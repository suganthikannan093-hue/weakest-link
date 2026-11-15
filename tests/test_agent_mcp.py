"""MCP flow tests: launcher, read-only catalog, writable my-bag store, recipes, ingest, planning,
offline demo and client configs. Needs the relate CLI (like test_queries.py)."""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import agent_lib as A  # noqa: E402

EX = ROOT / "agent" / "examples"
CATALOG = ROOT / "data" / "weakest-link.rl"
PROFILE = json.loads((EX / "my-profile.json").read_text())


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


class AgentMcpTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog_hash = sha(CATALOG)
        cls.tmp = tempfile.mkdtemp(prefix="wl-agent-test-")
        cls.store = os.path.join(cls.tmp, "my-bag.rl")
        cls.cat = A.McpClient(A.server_argv("catalog"))
        cls.mine = A.McpClient(A.server_argv("mybag", cls.store))
        cls.rec = {r["name"]: r["cypher"] for r in cls.mine.read("MATCH (r:Recipe) RETURN r.name AS name, r.cypher AS cypher")}
        cls.venue = A.extract_venue_email((EX / "venue-email-riverside.eml").read_text())
        cls.item = A.extract_spec_page((EX / "spec-page-examplelabs-usbc-hdmi.html").read_text())
        cls.venue_stats = cls.mine.write(cls.rec["ingest_venue"], {"v": cls.venue})["stats"]
        cls.item_stats = cls.mine.write(cls.rec["ingest_item"], {"it": cls.item})["stats"]

    @classmethod
    def tearDownClass(cls):
        cls.cat.close()
        cls.mine.close()
        shutil.rmtree(cls.tmp, ignore_errors=True)
        assert sha(CATALOG) == cls.catalog_hash, "the committed catalog store changed"

    # -- servers and tools
    def test_catalog_server_is_read_only(self):
        self.assertEqual(sorted(self.cat.tools()), ["get_schema", "read_cypher"])
        with self.assertRaises(A.McpError):
            self.cat.call("write_cypher", {"statement": "CREATE (:Probe)"})
        with self.assertRaises(A.McpError):
            self.cat.read("MATCH (n:Venue) DETACH DELETE n")

    def test_mybag_server_tools_and_recipes(self):
        self.assertEqual(sorted(self.mine.tools()), ["get_schema", "read_cypher", "write_cypher"])
        self.assertEqual(sorted(self.rec), ["best_fix", "chains", "charge_fix", "ingest_item", "ingest_venue", "power", "reach"])
        for name in ("reach", "chains", "best_fix", "power", "charge_fix"):
            self.assertEqual(self.rec[name], (ROOT / "queries" / f"{name}.cypher").read_text())

    def test_read_recipes_pass_mcp_read_cypher(self):
        # Relate's MCP read_cypher rejects CALL subqueries; every read recipe must be accepted
        p = {"laptop": "mba-m2", "bag": ["adp-apple-av-a1621"], "venue": "meetup-hall", "mode": "4K30",
             "venues": ["meetup-hall", "studio-tv"]}
        for name in ("reach", "chains", "best_fix", "power", "charge_fix"):
            for strict in (False, True):
                self.cat.read(self.rec[name], dict(p, strict=strict))

    def test_strict_recipe_parameter_drops_low_confidence_links(self):
        p = {"laptop": "iphone-15", "venue": "meetup-hall", "bag": ["adp-apple-av-a2119"], "mode": "1080p60"}
        self.assertTrue(self.cat.read(self.rec["reach"], dict(p, strict=False))[0]["ok"])
        self.assertFalse(self.cat.read(self.rec["reach"], dict(p, strict=True))[0]["ok"])

    def test_plan_suggests_a_charging_purchase(self):
        prof = {"laptop": "mba-m2", "bag": ["chg-apple-70w", "cable-usbc-usb2-60w"], "usual_venues": ["meetup-hall"]}
        plan = A.plan_trip(self.cat, prof, "meetup-hall", "4K60")
        self.assertEqual(plan["power"][0]["verdict"], "full-speed")
        self.assertEqual(plan["charge_fix"]["verdict"], "fast-charge")
        self.assertTrue(any(l.startswith("For charging, buy") for l in A.describe(self.cat, plan)))

    def test_get_schema_sees_ingested_labels(self):
        schema = self.mine.call("get_schema", {"sample_size": -1})
        self.assertIn("Recipe", schema)
        self.assertIn("Venue", schema)

    # -- extraction
    def test_extract_riverside_email(self):
        v = self.venue
        self.assertEqual(v["id"], "riverside-library-room-2")
        self.assertEqual(v["display"]["max_mode"], "1080p60")
        self.assertEqual([(i["connector"], i["standard"], i["confidence"]) for i in v["display"]["inputs"]],
                         [("HDMI", "HDMI-1.4", "low"), ("VGA", "VGA-1200p", "medium")])
        self.assertEqual(v["provides"], ["cable-hdmi-standard"])
        self.assertEqual(v["confidence"], "low")
        self.assertIn("older ones", v["source"]["supports"])

    def test_extract_hotel_email_ignores_negations(self):
        v = A.extract_venue_email((EX / "venue-email-harbour-hotel.eml").read_text())
        self.assertEqual(v["display"]["max_mode"], "4K60")
        self.assertEqual([i["standard"] for i in v["display"]["inputs"]], ["HDMI-2.0"])
        self.assertEqual(v["provides"], ["cable-hdmi-premium"])  # "we do not supply VGA cables" is ignored
        self.assertEqual(v["confidence"], "medium")
        self.assertNotIn("Dear", v["description"])

    def test_extract_spec_page(self):
        it = self.item
        self.assertTrue(it["id"].startswith("my-"))
        self.assertEqual([(p["connector"], p["gender"]) for p in it["ports"]],
                         [("USB-C", "plug"), ("HDMI", "receptacle"), ("USB-C", "receptacle")])
        self.assertEqual(it["video"][0]["standard"], "HDMI-2.0")
        self.assertEqual(it["power"][0]["watts"], 85)
        self.assertEqual(it["source"]["url"], "https://shop.examplelabs.example/usbc-hdmi20-pd")

    # -- writes
    def test_ingested_venue_in_graph_with_source(self):
        self.assertGreater(self.venue_stats["nodes_created"], 0)
        vc = A.check_venue(self.mine, self.venue["id"])
        self.assertEqual(sorted(vc["modes"]), ["1080p60", "720p60"])
        self.assertEqual(vc["provides"], ["cable-hdmi-standard"])
        self.assertEqual(vc["source"], self.venue["source"]["id"])
        self.assertGreater(vc["joints"], 0)
        gb = {i["connector"]: (i["gbps"], i["confidence"]) for i in vc["inputs"]}
        self.assertEqual(gb["HDMI"], (8.16, "low"))
        self.assertEqual(gb["VGA"], (3.7, "medium"))

    def test_ingested_item_in_graph(self):
        ic = A.check_item(self.mine, self.item["id"])
        self.assertEqual(len(ic["ports"]), 3)
        self.assertEqual(ic["video_gbps"], [14.4])
        self.assertEqual(ic["power_w"], [85])
        self.assertGreater(ic["joints"], 10)
        self.assertEqual(ic["source_url"], "https://shop.examplelabs.example/usbc-hdmi20-pd")

    def test_reingest_is_idempotent(self):
        count = "MATCH (n) RETURN count(n) AS n"
        before = self.mine.read(count)[0]["n"]
        rels = self.mine.read("MATCH ()-[r]->() RETURN count(r) AS n")[0]["n"]
        self.mine.write(self.rec["ingest_venue"], {"v": self.venue})
        self.mine.write(self.rec["ingest_item"], {"it": self.item})
        self.assertEqual(self.mine.read(count)[0]["n"], before)
        self.assertEqual(self.mine.read("MATCH ()-[r]->() RETURN count(r) AS n")[0]["n"], rels)

    def test_ingest_refuses_catalog_ids(self):
        v = dict(self.venue, id="meetup-hall")
        st = self.mine.write(self.rec["ingest_venue"], {"v": v})["stats"]
        self.assertEqual(st["nodes_created"], 0)
        self.assertEqual(st["nodes_deleted"], 0)
        it = dict(self.item, id="cable-vga")
        st = self.mine.write(self.rec["ingest_item"], {"it": it})["stats"]
        self.assertEqual((st["nodes_created"], st["nodes_deleted"]), (0, 0))
        self.assertEqual(self.mine.read("MATCH (v:Venue {id: 'meetup-hall'}) RETURN v.name AS n")[0]["n"], "Community meetup hall")

    def test_catalog_not_changed_by_writes(self):
        self.assertEqual(self.cat.read("MATCH (v:Venue) WHERE v.ingested RETURN count(v) AS n")[0]["n"], 0)
        self.assertEqual(self.cat.read("MATCH (r:Recipe) RETURN count(r) AS n")[0]["n"], 0)

    # -- queries over the ingested data
    def test_weakest_link_is_the_venue_cable(self):
        r = self.mine.query("reach", {"laptop": "mba-m2", "venue": self.venue["id"],
                                      "bag": ["adp-apple-av-a1621"], "mode": "1080p60"})[0]
        self.assertFalse(r["ok"])
        self.assertTrue(r["panel_ok"])
        r = self.mine.query("reach", {"laptop": "mba-m2", "venue": self.venue["id"],
                                      "bag": ["adp-apple-av-a1621"], "mode": "720p60"})[0]
        self.assertTrue(r["ok"])
        self.assertEqual(r["weakest_item"], "cable-hdmi-standard")
        ch = self.mine.query("chains", {"laptop": "mba-m2", "venue": self.venue["id"], "bag": ["adp-apple-av-a1621"]})
        self.assertEqual(ch[0]["weakest_item"], "cable-hdmi-standard")
        self.assertEqual(ch[0]["weakest_source"], "https://www.hdmi.org/resource/cables")

    def test_ingested_adapter_is_used_at_catalog_venue(self):
        r = self.mine.query("reach", {"laptop": "mba-m2", "venue": "meetup-hall", "bag": [self.item["id"]], "mode": "4K60"})[0]
        self.assertTrue(r["ok"])
        self.assertIn(self.item["id"], r["chain"])

    def test_plan(self):
        plan = A.plan_trip(self.mine, PROFILE, self.venue["id"], "1080p60", considering=self.item["id"])
        self.assertFalse(plan["reach_target"]["ok"])
        self.assertFalse(plan["considering"]["fixes_venue"])
        self.assertEqual(plan["considering"]["weakest_with_it"], "cable-hdmi-standard")
        self.assertEqual(plan["buy"]["buy"], "cable-usbc-hdmi-4k60")
        self.assertEqual(sorted(plan["buy"]["fixed_venues"]), ["riverside-library-room-2", "studio-tv"])
        self.assertTrue(all(r["ok"] for r in plan["after"].values()))
        self.assertIn("cable-usbc-hdmi-4k60", plan["pack"])
        self.assertIn("hub-usbc-4k30", plan["leave"])
        self.assertEqual(plan["power"][0]["verdict"], "full-speed")
        text = " ".join(A.describe(self.mine, plan))
        for phrase in ("only reaches 720p", "Standard HDMI cable", "Buy one thing: USB-C to HDMI cable, 4K60",
                       "would not help", "Pack:", "charges at full speed"):
            self.assertIn(phrase, text)


class DemoAndConfigTest(unittest.TestCase):
    def test_offline_demo_end_to_end(self):
        res = subprocess.run([sys.executable, str(ROOT / "scripts" / "agent_demo.py"), "--json"],
                             capture_output=True, text=True, timeout=120, cwd=ROOT)
        self.assertEqual(res.returncode, 0, res.stderr)
        d = json.loads(res.stdout)
        self.assertTrue(d["catalog_untouched"])
        self.assertEqual(d["plan"]["buy"], "cable-usbc-hdmi-4k60")
        self.assertEqual(d["plan"]["weakest_now"], "cable-hdmi-standard")
        self.assertEqual(d["plan"]["best_mode_now"], "720p60")
        self.assertFalse(d["plan"]["considering_fixes_venue"])
        self.assertTrue(all(d["plan"]["after_ok"].values()))

    def test_demo_is_deterministic(self):
        runs = [json.loads(subprocess.run([sys.executable, str(ROOT / "scripts" / "agent_demo.py"), "--json"],
                                          capture_output=True, text=True, timeout=120, cwd=ROOT).stdout)
                for _ in range(2)]
        for r in runs:
            r.pop("seconds")
        self.assertEqual(runs[0], runs[1])

    def test_demo_with_preextracted_venue(self):
        with tempfile.TemporaryDirectory() as d:
            v = A.extract_venue_email((EX / "venue-email-harbour-hotel.eml").read_text())
            p = Path(d) / "v.json"
            p.write_text(json.dumps(v))
            res = subprocess.run([sys.executable, str(ROOT / "scripts" / "agent_demo.py"), "--json", "--venue-json", str(p)],
                                 capture_output=True, text=True, timeout=120, cwd=ROOT)
            self.assertEqual(res.returncode, 0, res.stderr)
            out = json.loads(res.stdout)
            self.assertEqual(out["venue"]["id"], "harbour-suite-harbour-hotel")
            self.assertEqual(out["venue"]["check"]["provides"], ["cable-hdmi-premium"])

    def test_client_configs_launch_the_servers(self):
        cfgs = {
            ".cursor/mcp.json": ("mcpServers", lambda a: a.replace("${workspaceFolder}", str(ROOT))),
            ".vscode/mcp.json": ("servers", lambda a: a.replace("${workspaceFolder}", str(ROOT))),
            ".mcp.json": ("mcpServers", lambda a: a),
            "agent/clients/cursor.mcp.json": ("mcpServers", lambda a: a.replace("${workspaceFolder}", str(ROOT))),
            "agent/clients/vscode.mcp.json": ("servers", lambda a: a.replace("${workspaceFolder}", str(ROOT))),
            "agent/clients/claude_desktop_config.json": ("mcpServers", lambda a: a.replace("/ABSOLUTE/PATH/TO/weakest-link", str(ROOT))),
        }
        for path, (key, fix) in cfgs.items():
            servers = json.loads((ROOT / path).read_text())[key]
            self.assertEqual(sorted(servers), ["weakest-link-catalog", "weakest-link-mybag"], path)
            s = servers["weakest-link-catalog"]  # launch the read-only one (no store side effects)
            argv = [sys.executable if s["command"] in ("python3", "python") else s["command"]] + [fix(a) for a in s["args"]]
            with A.McpClient(argv) as c:
                self.assertIn("read_cypher", c.tools(), path)
            self.assertTrue(servers["weakest-link-mybag"]["args"][-1] == "mybag", path)
        direct = json.loads((ROOT / "agent/clients/relate-direct.mcp.json").read_text())["mcpServers"]
        self.assertIn("--read-only", direct["weakest-link-catalog"]["args"])

    def test_skill_folder_is_up_to_date(self):
        res = subprocess.run([sys.executable, str(ROOT / "scripts" / "build_agent_docs.py"), "--check"],
                             capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, res.stdout)

    def test_schemas_are_valid_json_and_match_examples(self):
        for p in (ROOT / "agent" / "schemas").glob("*.json"):
            json.loads(p.read_text())
        v = A.extract_venue_email((EX / "venue-email-riverside.eml").read_text())
        schema = json.loads((ROOT / "agent/schemas/venue.schema.json").read_text())
        self.assertTrue(set(schema["required"]) <= set(v))
        allowed = set(schema["properties"]["display"]["properties"]["inputs"]["items"]["properties"]["standard"]["enum"])
        self.assertTrue({i["standard"] for i in v["display"]["inputs"]} <= allowed)


if __name__ == "__main__":
    unittest.main()
