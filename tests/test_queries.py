"""Runs every core query against the committed Relate store (data/weakest-link.rl).

    python3 -m unittest -v
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from wl import run_cypher, run_query  # noqa: E402

ALL_VENUES = ["meetup-hall", "college-seminar", "hotel-ballroom", "coworking-room", "conference-booth", "studio-tv"]


def reach(laptop, venue, bag, mode):
    rows = run_query("reach", {"laptop": laptop, "venue": venue, "bag": bag, "mode": mode})
    assert len(rows) == 1, rows
    return rows[0]


class DatasetIntegrity(unittest.TestCase):
    def test_size(self):
        n = run_cypher("MATCH (i:Item) RETURN count(i) AS n")[0]["n"]
        self.assertGreaterEqual(n, 40)

    def test_every_capability_edge_is_cited(self):
        rows = run_cypher("MATCH ()-[r:VIDEO|POWER]->() "
                          "RETURN count(r) AS total, "
                          "count(CASE WHEN r.source_url IS NULL OR NOT r.confidence IN ['high','medium','low'] THEN 1 END) AS uncited")
        self.assertGreater(rows[0]["total"], 50)
        self.assertEqual(rows[0]["uncited"], 0)

    def test_video_edges_have_bandwidth(self):
        rows = run_cypher("MATCH ()-[r:VIDEO]->() WHERE r.gbps IS NULL RETURN count(r) AS n")
        self.assertEqual(rows[0]["n"], 0)

    def test_mates_only_join_same_connector(self):
        rows = run_cypher("MATCH (a:Port)-[:MATES]->(b:Port) WHERE a.connector <> b.connector OR a.gender = b.gender RETURN count(*) AS n")
        self.assertEqual(rows[0]["n"], 0)

    def test_mode_rates(self):
        rows = {r["id"]: r["gbps"] for r in run_cypher("MATCH (m:Mode) RETURN m.id AS id, m.gbps AS gbps")}
        self.assertAlmostEqual(rows["4K60"], 14.256)   # 594 MHz x 24 bit
        self.assertAlmostEqual(rows["1080p60"], 3.564)  # 148.5 MHz x 24 bit


class Reachability(unittest.TestCase):
    def test_old_apple_adapter_blocks_4k60(self):
        r = reach("mba-m2", "meetup-hall", ["adp-apple-av-a1621"], "4K60")
        self.assertFalse(r["ok"])
        self.assertTrue(r["panel_ok"])

    def test_old_apple_adapter_fine_for_1080p(self):
        r = reach("mba-m2", "meetup-hall", ["adp-apple-av-a1621"], "1080p60")
        self.assertTrue(r["ok"])
        self.assertEqual(r["chain"], ["mba-m2", "adp-apple-av-a1621", "cable-hdmi-premium", "tv-4k-hdmi20"])
        self.assertEqual(r["weakest_item"], "adp-apple-av-a1621")
        self.assertAlmostEqual(r["bottleneck_gbps"], 8.16)

    def test_new_apple_adapter_does_4k60(self):
        r = reach("mba-m2", "meetup-hall", ["adp-apple-av-a2119"], "4K60")
        self.assertTrue(r["ok"])
        self.assertAlmostEqual(r["bottleneck_gbps"], 14.4)

    def test_usb2_charge_cable_carries_no_video(self):
        self.assertFalse(reach("mba-m2", "conference-booth", ["cable-usbc-usb2-240w"], "1080p60")["ok"])
        r = reach("mba-m2", "conference-booth", ["cable-tb4"], "4K60")
        self.assertTrue(r["ok"])
        self.assertEqual(r["chain"], ["mba-m2", "cable-tb4", "mon-4k-multi"])

    def test_passive_dp_hdmi_needs_dual_mode_source(self):
        bag = ["adp-usbc-dp", "adp-dp-hdmi-passive"]
        self.assertFalse(reach("mba-m2", "meetup-hall", bag, "1080p60")["ok"])
        r = reach("mba-m2", "meetup-hall", ["adp-usbc-dp", "adp-dp-hdmi-active"], "4K60")
        self.assertTrue(r["ok"])
        self.assertEqual(r["chain"], ["mba-m2", "adp-usbc-dp", "adp-dp-hdmi-active", "cable-hdmi-premium", "tv-4k-hdmi20"])

    def test_panel_limit_is_reported(self):
        r = reach("x1c-g11", "college-seminar", ["adp-usbc-vga"], "1080p60")
        self.assertFalse(r["ok"])
        self.assertFalse(r["panel_ok"])
        self.assertTrue(reach("x1c-g11", "college-seminar", ["adp-usbc-vga"], "720p60")["ok"])

    def test_budget_laptop_usbc_has_no_video(self):
        self.assertFalse(reach("gen-laptop-budget", "conference-booth", ["cable-tb4"], "1080p60")["ok"])
        self.assertTrue(reach("gen-laptop-budget", "hotel-ballroom", [], "1080p60")["ok"])


class Bottleneck(unittest.TestCase):
    def test_widest_chain_first_and_weakest_link_cited(self):
        rows = run_query("chains", {"laptop": "mba-m2", "venue": "meetup-hall",
                                    "bag": ["adp-apple-av-a1621", "hub-usbc-4k30", "cable-usbc-hdmi-4k60"]})
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0]["chain"], ["mba-m2", "cable-usbc-hdmi-4k60", "tv-4k-hdmi20"])
        self.assertEqual(rows[0]["best_mode"], "4K60")
        apple = next(r for r in rows if "adp-apple-av-a1621" in r["chain"])
        self.assertEqual(apple["weakest_item"], "adp-apple-av-a1621")
        self.assertEqual(apple["best_mode"], "4K30")
        self.assertEqual(apple["weakest_source"], "https://support.apple.com/en-us/119850")

    def test_venue_cable_is_the_weakest_link(self):
        rows = run_query("chains", {"laptop": "mbp14-m3", "venue": "studio-tv", "bag": []})
        self.assertEqual(rows[0]["weakest_item"], "cable-hdmi-standard")
        self.assertEqual(rows[0]["best_mode"], "720p60")
        self.assertTrue(reach("mbp14-m3", "studio-tv", ["cable-hdmi-premium"], "4K60")["ok"])

    def test_venue_input_caps_mode(self):
        rows = run_query("chains", {"laptop": "mbp14-m3", "venue": "coworking-room", "bag": ["cable-hdmi-ultra"]})
        self.assertTrue(all(r["best_mode"] == "4K30" for r in rows))
        self.assertTrue(any(r["weakest_item"] == "disp-4k-hdmi14" for r in rows))


class BestFix(unittest.TestCase):
    def test_one_purchase_fixes_most_venues(self):
        rows = run_query("best_fix", {"laptop": "mba-m2", "bag": ["adp-apple-av-a1621"],
                                      "venues": ALL_VENUES, "mode": "1080p60"})
        top = rows[0]
        self.assertEqual(top["venues_fixed"], 2)
        self.assertEqual(sorted(top["fixed_venues"]), ["conference-booth", "studio-tv"])
        self.assertEqual(top["still_failing"], ["college-seminar"])
        self.assertIn("cable-hdmi-premium", [r["buy"] for r in rows if r["venues_fixed"] == 2])

    def test_no_purchase_fixes_a_venue_input_limit(self):
        rows = run_query("best_fix", {"laptop": "mbp14-m3", "bag": [], "venues": ["coworking-room"], "mode": "4K60"})
        self.assertEqual(rows, [])

    def test_4k60_fix_for_old_adapter_owner(self):
        rows = run_query("best_fix", {"laptop": "mba-m2", "bag": ["adp-apple-av-a1621"],
                                      "venues": ["meetup-hall", "conference-booth", "studio-tv"], "mode": "4K60"})
        best = [r["buy"] for r in rows if r["venues_fixed"] == rows[0]["venues_fixed"]]
        self.assertIn("cable-usbc-hdmi-4k60", best)
        self.assertEqual(rows[0]["venues_fixed"], 3)


class Power(unittest.TestCase):
    def test_fast_charge_and_weak_cable(self):
        rows = run_query("power", {"laptop": "mbp14-m3", "bag": ["chg-apple-96w", "cable-usbc-magsafe3"]})
        self.assertEqual(rows[0]["verdict"], "fast-charge")
        rows = run_query("power", {"laptop": "mbp14-m3", "bag": ["chg-apple-140w", "cable-usbc-usb2-60w"]})
        self.assertEqual(rows[0]["capacity_w"], 60)
        self.assertEqual(rows[0]["weakest_item"], "cable-usbc-usb2-60w")
        self.assertEqual(rows[0]["verdict"], "below-recommended")

    def test_phone_charger_is_below_recommended(self):
        rows = run_query("power", {"laptop": "mba-m2", "bag": ["chg-gen-20w", "cable-usbc-usb2-60w"]})
        self.assertEqual(rows[0]["capacity_w"], 20)
        self.assertEqual(rows[0]["verdict"], "below-recommended")

    def test_epr_cable_unlocks_140w(self):
        rows = run_query("power", {"laptop": "mba-m2", "bag": ["chg-apple-140w", "cable-usbc-usb2-240w"]})
        self.assertEqual(rows[0]["capacity_w"], 140)
        self.assertEqual(rows[0]["verdict"], "fast-charge")

    def test_data_only_usbc_cannot_charge(self):
        self.assertEqual(run_query("power", {"laptop": "gen-laptop-budget", "bag": ["chg-gen-65w", "cable-usbc-10g-100w"]}), [])



class ChargeFix(unittest.TestCase):
    def test_thin_cable_owner_is_told_to_buy_a_cable(self):
        rows = run_query("charge_fix", {"laptop": "mbp14-m3", "bag": ["chg-apple-140w", "cable-usbc-usb2-60w"]})
        top = rows[0]
        self.assertEqual(len(top["buy"]), 1)
        self.assertTrue(top["buy"][0].startswith("cable-"))
        self.assertEqual((top["verdict"], top["verdict_now"], top["capacity_now_w"]), ("fast-charge", "below-recommended", 60))

    def test_empty_bag_gets_a_charger_and_cable_pair(self):
        top = run_query("charge_fix", {"laptop": "iphone-15", "bag": []})[0]
        self.assertEqual(len(top["buy"]), 2)
        self.assertEqual(top["verdict"], "fast-charge")
        self.assertIsNone(top["capacity_now_w"])

    def test_nothing_to_buy_when_already_fast(self):
        self.assertEqual(run_query("charge_fix", {"laptop": "mbp14-m3", "bag": ["chg-apple-96w", "cable-usbc-magsafe3"]}), [])

    def test_barrel_jack_laptop_gets_no_suggestion(self):
        self.assertEqual(run_query("charge_fix", {"laptop": "ideapad1-15amn7", "bag": []}), [])


class StrictMode(unittest.TestCase):
    def test_strict_ignores_low_confidence_phone_video(self):
        p = {"laptop": "iphone-15", "venue": "meetup-hall", "bag": ["adp-apple-av-a2119"], "mode": "1080p60"}
        self.assertTrue(reach(**{k: p[k] for k in ("venue", "bag", "mode")}, laptop="iphone-15")["ok"])
        self.assertFalse(run_query("reach", dict(p, strict=True))[0]["ok"])

    def test_strict_keeps_medium_and_high_links(self):
        r = run_query("reach", {"laptop": "mba-m2", "venue": "meetup-hall", "bag": ["adp-apple-av-a2119"], "mode": "4K60", "strict": True})[0]
        self.assertTrue(r["ok"])
        self.assertTrue(all(h["confidence"] != "low" for h in r["hops"]))

    def test_strict_drops_the_low_confidence_venue_cable(self):
        # the VGA cable is low confidence, so strict mode cannot use the college seminar room's only input
        self.assertTrue(reach("gen-laptop-budget", "college-seminar", ["adp-hdmi-vga"], "720p60")["ok"])
        self.assertFalse(run_query("reach", {"laptop": "gen-laptop-budget", "venue": "college-seminar", "bag": ["adp-hdmi-vga"], "mode": "720p60", "strict": True})[0]["ok"])

    def test_every_query_accepts_strict(self):
        base = {"laptop": "mba-m2", "bag": ["chg-apple-70w"], "venue": "meetup-hall", "mode": "1080p60", "venues": ["meetup-hall"]}
        need = {"reach": ("laptop", "venue", "bag", "mode"), "chains": ("laptop", "venue", "bag"),
                "best_fix": ("laptop", "bag", "venues", "mode"), "power": ("laptop", "bag"), "charge_fix": ("laptop", "bag")}
        for q, keys in need.items():
            run_query(q, dict({k: base[k] for k in keys}, strict=True))


if __name__ == "__main__":
    unittest.main()
