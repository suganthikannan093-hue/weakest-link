"""Traps found while auditing the milestone 4 catalog. Each test pins one documented limit
to the maker's or spec body's own page (see docs/DATA.md, audit table).

    python3 -m unittest tests.test_catalog_traps -v
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from wl import run_cypher, run_query  # noqa: E402


def reach(device, venue, bag, mode):
    rows = run_query("reach", {"laptop": device, "venue": venue, "bag": bag, "mode": mode})
    assert len(rows) == 1, rows
    return rows[0]


def power(device, bag):
    return run_query("power", {"laptop": device, "bag": bag})


class AuditFixes(unittest.TestCase):
    def test_dp8k_cable_is_hbr3_not_uhbr10(self):
        rows = run_cypher("MATCH (:Item {id: 'cable-dp8k'})-[:HAS_PORT]->()-[v:VIDEO]->() RETURN DISTINCT v.standard AS s, v.gbps AS g, v.source AS src")
        self.assertEqual(rows, [{"s": "DP-1.4-HBR3", "g": 25.92, "src": "vesa-dp8k-pr"}])

    def test_high_speed_hdmi_is_medium_confidence(self):
        rows = run_cypher("MATCH (:Item {id: 'cable-hdmi-high-speed'})-[:HAS_PORT]->()-[v:VIDEO]->() RETURN DISTINCT v.confidence AS c, v.gbps AS g")
        self.assertEqual(rows, [{"c": "medium", "g": 8.16}])

    def test_no_source_points_at_a_private_repo(self):
        rows = run_cypher("MATCH (s:Source) WHERE s.url CONTAINS 'github.com' OR NOT s.url STARTS WITH 'https://' RETURN s.id AS id")
        self.assertEqual(rows, [])
        rows = run_cypher("MATCH ()-[r:VIDEO|POWER]->() WHERE r.source_url CONTAINS 'github.com' RETURN count(r) AS n")
        self.assertEqual(rows[0]["n"], 0)

    def test_every_product_edge_cites_a_maker_or_spec_body(self):
        rows = run_cypher("MATCH (i:Item {class: 'product'})-[:CITES]->(s:Source) WHERE NOT s.kind IN ['manufacturer', 'spec-body'] RETURN i.id AS id, s.id AS s")
        self.assertEqual(rows, [])


class LaptopTraps(unittest.TestCase):
    def test_ideapad1_usbc_is_data_only(self):
        self.assertFalse(reach("ideapad1-15amn7", "hot-desk", ["cable-usbc-dp14", "cable-usbc-hdmi-4k60"], "720p60")["ok"])
        self.assertTrue(reach("ideapad1-15amn7", "hot-desk", ["cable-hdmi-premium"], "1440p60")["ok"])

    def test_ideapad1_hdmi_14b_caps_at_4k30(self):
        self.assertFalse(reach("ideapad1-15amn7", "meetup-hall", [], "4K60")["ok"])
        r = reach("ideapad1-15amn7", "meetup-hall", [], "4K30")
        self.assertTrue(r["ok"])

    def test_slim3_hdmi_is_4k30_but_usbc_reaches_4k60(self):
        r = reach("ideapad-slim3-15iru8", "meetup-hall", [], "4K60")
        self.assertFalse(r["ok"])
        self.assertTrue(r["panel_ok"])
        r = reach("ideapad-slim3-15iru8", "meetup-hall", ["adp-usbc-hdmi-4k60"], "4K60")
        self.assertTrue(r["ok"])
        self.assertEqual(r["chain"][:2], ["ideapad-slim3-15iru8", "adp-usbc-hdmi-4k60"])

    def test_xps13_has_no_hdmi_port(self):
        self.assertFalse(reach("xps13-9340", "meetup-hall", [], "720p60")["ok"])
        self.assertTrue(reach("xps13-9340", "meetup-hall", ["adp-usbc-hdmi-4k60"], "4K60")["ok"])

    def test_mbp14_m4_hdmi_is_frl(self):
        self.assertTrue(reach("mbp14-m4", "studio-tv", ["cable-hdmi-ultra"], "4K60")["ok"])


class PhoneAndTabletTraps(unittest.TestCase):
    def test_pixel_7a_has_no_video_but_pixel_8_does(self):
        self.assertFalse(reach("pixel-7a", "conference-booth", ["cable-usbc-dp14"], "720p60")["ok"])
        self.assertTrue(reach("pixel-8", "conference-booth", ["cable-usbc-dp14"], "1080p60")["ok"])

    def test_galaxy_z_flip6_has_no_video(self):
        self.assertFalse(reach("galaxy-z-flip6", "meetup-hall", ["adp-usbc-hdmi-4k60"], "720p60")["ok"])
        self.assertTrue(reach("galaxy-s24", "meetup-hall", ["adp-usbc-hdmi-4k60"], "1080p60")["ok"])

    def test_galaxy_tab_s9_fe_has_no_hdmi_output(self):
        self.assertFalse(reach("galaxy-tab-s9-fe", "meetup-hall", ["adp-usbc-hdmi-4k60"], "720p60")["ok"])
        self.assertTrue(reach("galaxy-tab-s9", "meetup-hall", ["adp-usbc-hdmi-4k60"], "1080p60")["ok"])

    def test_ipad_10_is_4k30_only(self):
        self.assertTrue(reach("ipad-10", "conference-booth", ["cable-usbc-dp14"], "4K30")["ok"])
        self.assertFalse(reach("ipad-10", "conference-booth", ["cable-usbc-dp14"], "4K60")["ok"])
        best = run_query("chains", {"laptop": "ipad-10", "venue": "conference-booth", "bag": ["cable-usbc-dp14"]})[0]
        self.assertEqual((best["best_mode"], best["weakest_item"]), ("4K30", "ipad-10"))

    def test_iphone_needs_a_video_capable_cable(self):
        self.assertFalse(reach("iphone-15", "hot-desk", ["cable-usbc-usb2-60w"], "720p60")["ok"])
        self.assertTrue(reach("iphone-15", "meetup-hall", ["adp-apple-av-a2119"], "1080p60")["ok"])

    def test_iphone_fast_charges_on_20w(self):
        rows = power("iphone-15", ["chg-apple-20w", "cable-usbc-usb2-60w"])
        self.assertEqual(rows[0]["verdict"], "fast-charge")

    def test_phone_without_documented_wattage_is_unknown(self):
        rows = power("pixel-8", ["chg-anker-735", "cable-usbc-usb2-60w"])
        self.assertEqual(rows[0]["verdict"], "unknown")


class HubAndDockTraps(unittest.TestCase):
    def test_anker_341_usbc_data_port_carries_no_video(self):
        rows = run_query("chains", {"laptop": "mba-m2", "venue": "conference-booth",
                                    "bag": ["hub-anker-341", "cable-usbc-dp14", "cable-hdmi-premium"]})
        self.assertTrue(rows)
        for r in rows:
            self.assertFalse("hub-anker-341" in r["chain"] and "cable-usbc-dp14" in r["chain"], r["chain"])

    def test_anker_341_hdmi_is_4k30(self):
        r = reach("mba-m2", "meetup-hall", ["hub-anker-341"], "4K60")
        self.assertFalse(r["ok"])
        self.assertTrue(reach("mba-m2", "meetup-hall", ["hub-anker-341"], "4K30")["ok"])

    def test_apple_vga_adapter_reaches_meeting_room_over_vga(self):
        r = reach("mba-m2", "meeting-room", ["adp-apple-vga"], "1080p60")
        self.assertTrue(r["ok"])
        self.assertIn("cable-vga", r["chain"])

    def test_docks_charge_the_laptop(self):
        self.assertEqual(power("t14-g4", ["dock-lenovo-universal"])[0]["capacity_w"], 65)
        rows = power("mbp14-m4", ["dock-caldigit-ts4"])
        self.assertEqual((rows[0]["capacity_w"], rows[0]["verdict"]), (98, "fast-charge"))

    def test_travel_hub_cannot_charge_a_laptop(self):
        self.assertEqual(power("mba-m2", ["hub-ms-travel", "chg-apple-70w"]), [])


class MonitorAndProjectorTraps(unittest.TestCase):
    def test_usbc_monitor_charges_over_the_video_cable(self):
        rows = power("mba-m2", ["mon-lg-27up850", "cable-usbc-10g-100w"])
        self.assertEqual((rows[0]["capacity_w"], rows[0]["verdict"]), (96, "fast-charge"))

    def test_usb2_cable_charges_but_shows_nothing_at_hot_desk(self):
        self.assertFalse(reach("mba-m2", "hot-desk", ["cable-usbc-usb2-240w"], "720p60")["ok"])
        self.assertTrue(reach("mba-m2", "hot-desk", ["cable-usbc-10g-100w"], "1440p60")["ok"])

    def test_hot_desk_monitor_is_1440p(self):
        r = reach("mba-m2", "hot-desk", ["cable-usbc-10g-100w"], "4K30")
        self.assertFalse(r["ok"])
        self.assertFalse(r["panel_ok"])

    def test_xga_classroom_projector_takes_1080p_but_not_4k(self):
        self.assertTrue(reach("mba-m2", "school-classroom", ["adp-usbc-hdmi-4k60"], "1080p60")["ok"])
        self.assertFalse(reach("mba-m2", "school-classroom", ["adp-usbc-hdmi-4k60"], "4K30")["panel_ok"])


if __name__ == "__main__":
    unittest.main()
