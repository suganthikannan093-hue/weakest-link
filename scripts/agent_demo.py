#!/usr/bin/env python3
"""Offline, deterministic 'pack my bag' agent demo over Relate's MCP server.

It drives two MCP servers over stdio, exactly as an MCP host would:
  catalog  read-only `relate serve --mcp stdio --read-only` on data/weakest-link.rl
  my-bag   writable `relate serve --mcp stdio` on a copy (default: a fresh temp store)
and runs: discover -> ingest a venue email -> ingest an adapter spec page -> query -> recommend.
No LLM, no API key and no network. Every step prints the MCP tool call it makes.

  python3 scripts/agent_demo.py                 # the full story, about 1 second
  python3 scripts/agent_demo.py --pace 2        # pause between steps (for filming)
  python3 scripts/agent_demo.py --json          # machine-readable summary (CI)
  python3 scripts/agent_demo.py --email my.eml --spec page.html --profile me.json
  python3 scripts/agent_demo.py --venue-json v.json   # use a venue an LLM extracted instead
"""
import argparse
import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import agent_lib as A  # noqa: E402

EX = A.ROOT / "agent" / "examples"


class Out:
    def __init__(self, quiet, pace, color):
        self.quiet, self.pace, self.color = quiet, pace, color

    def c(self, code, s):
        return f"\033[{code}m{s}\033[0m" if self.color else s

    def step(self, n, title):
        if self.quiet:
            return
        if self.pace and n > 1:
            time.sleep(self.pace)
        print("\n" + self.c("1;36", f"[{n}] {title}"))

    def tool(self, server, name, summary):
        if not self.quiet:
            print(self.c("2", f"    -> {server}.{name}  {summary}"))

    def say(self, s="", code=None):
        if not self.quiet:
            print("    " + (self.c(code, s) if code else s))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--email", default=str(EX / "venue-email-riverside.eml"))
    ap.add_argument("--venue-json", help="a venue already extracted (for example by an LLM) instead of --email")
    ap.add_argument("--spec", default=str(EX / "spec-page-examplelabs-usbc-hdmi.html"))
    ap.add_argument("--profile", default=str(EX / "my-profile.json"))
    ap.add_argument("--store", help="writable store path (default: a fresh temp copy, deleted afterwards)")
    ap.add_argument("--pace", type=float, default=0.0, help="seconds to pause between steps")
    ap.add_argument("--json", action="store_true", help="print only a JSON summary")
    ap.add_argument("--no-color", action="store_true")
    a = ap.parse_args(argv)
    out = Out(a.json, a.pace, sys.stdout.isatty() and not a.no_color and not os.environ.get("NO_COLOR"))

    tmpdir = None
    store = a.store
    if not store:
        tmpdir = tempfile.mkdtemp(prefix="weakest-link-demo-")
        store = os.path.join(tmpdir, "my-bag.rl")
    profile = json.loads(Path(a.profile).read_text(encoding="utf-8"))
    summary = {"profile": profile}
    t0 = time.perf_counter()
    try:
        out.step(1, "Connect to Relate over MCP")
        with A.McpClient(A.server_argv("catalog")) as cat, A.McpClient(A.server_argv("mybag", store)) as mine:
            ct, mt = cat.tools(), mine.tools()
            out.say(f"catalog (read-only): {', '.join(ct)}   [{cat.server_info.get('name')} {cat.server_info.get('version')}]")
            out.say(f"my-bag  (writable) : {', '.join(mt)}")
            summary["tools"] = {"catalog": ct, "mybag": mt}
            out.tool("my-bag", "read_cypher", "MATCH (r:Recipe) RETURN r.name, r.kind, r.description")
            recipes = mine.read("MATCH (r:Recipe) RETURN r.name AS name, r.kind AS kind, r.description AS d ORDER BY kind, name")
            for r in recipes:
                out.say(f"recipe {r['name']:<13} ({r['kind']}) {r['d'][:88]}…")
            rec = {r["name"]: r for r in mine.read("MATCH (r:Recipe) RETURN r.name AS name, r.cypher AS cypher")}
            summary["recipes"] = [r["name"] for r in recipes]

            out.step(2, "Read the venue's email and write it into the graph")
            if a.venue_json:
                venue = json.loads(Path(a.venue_json).read_text(encoding="utf-8"))
                out.say(f"using pre-extracted venue {a.venue_json}")
            else:
                raw = Path(a.email).read_text(encoding="utf-8")
                for line in raw.splitlines()[:4]:
                    out.say(line, "2")
                venue = A.extract_venue_email(raw)
            d = venue["display"]
            out.say(f"extracted: {venue['name']} | {d['name']} | best picture {d['max_mode']} | inputs "
                    + ", ".join(f"{i['connector']} ({i['standard']}, {i.get('confidence', venue['confidence'])})" for i in d["inputs"])
                    + f" | leaves out: {', '.join(venue.get('provides') or ['nothing'])}")
            out.tool("my-bag", "write_cypher", f"recipe ingest_venue, $v = {{id: '{venue['id']}', …}}")
            st = mine.write(rec["ingest_venue"]["cypher"], {"v": venue})["stats"]
            if not st["nodes_created"]:
                raise SystemExit(f"ingest_venue wrote nothing: '{venue['id']}' is a catalog venue id")
            out.say(f"wrote {st['nodes_created']} nodes and {st['relationships_created']} relationships")
            out.tool("my-bag", "read_cypher", "verify: the venue, its display's inputs, modes and cables")
            vc = A.check_venue(mine, venue["id"])
            out.say(f"in the graph: {vc['display']} supports {', '.join(vc['modes'])}; inputs "
                    + ", ".join(f"{i['connector']} {i['gbps']} Gbps" for i in vc["inputs"])
                    + f"; {vc['joints']} plug/socket joints; cites {vc['source']}")
            summary["venue"] = {"id": venue["id"], "max_mode": d["max_mode"], "stats": st, "check": vc, "extracted": venue}

            out.step(3, "Read an adapter's spec page and write it into the graph")
            page = Path(a.spec).read_text(encoding="utf-8")
            item = A.extract_spec_page(page)
            out.say(f"extracted: {item['name']} | {item['ports'][0]['connector']} -> {item['ports'][1]['connector']} "
                    f"| {item['video'][0]['standard']} | confidence {item['confidence']}"
                    + (f" | PD pass-through {item['power'][0]['watts']} W" if item.get("power") else ""))
            out.tool("my-bag", "write_cypher", f"recipe ingest_item, $it = {{id: '{item['id']}', …}}")
            st = mine.write(rec["ingest_item"]["cypher"], {"it": item})["stats"]
            if not st["nodes_created"]:
                raise SystemExit(f"ingest_item wrote nothing: '{item['id']}' is a catalog item id")
            out.say(f"wrote {st['nodes_created']} nodes and {st['relationships_created']} relationships")
            ic = A.check_item(mine, item["id"])
            out.tool("my-bag", "read_cypher", "verify: the item's ports, links and joints")
            out.say(f"in the graph: {len(ic['ports'])} ports, video {ic['video_gbps']} Gbps, power {ic['power_w']} W, "
                    f"{ic['joints']} plug/socket joints with the rest of the catalog")
            summary["item"] = {"id": item["id"], "stats": st, "check": ic, "extracted": item}

            out.step(4, "Check that the read-only catalog was not touched")
            out.tool("catalog", "read_cypher", "MATCH (v:Venue {id: $id}) RETURN count(v)")
            n_cat = cat.read("MATCH (v:Venue {id: $id}) RETURN count(v) AS n", {"id": venue["id"]})[0]["n"]
            try:
                cat.call("write_cypher", {"statement": "CREATE (:Probe)"})
                refused = False
            except A.McpError as e:
                refused = True
                out.say(f"catalog refuses writes: {str(e)[:60]}")
            out.say(f"venue in catalog: {n_cat} (only in the writable my-bag store)")
            summary["catalog_untouched"] = n_cat == 0 and refused

            out.step(5, f"Ask: what do I pack for {venue['name']}, and what one thing should I buy?")
            for q in ("reach", "chains", "best_fix", "power"):
                out.tool("my-bag", "read_cypher", f"recipe {q}")
            plan = A.plan_trip(mine, profile, venue["id"], d["max_mode"], considering=item["id"])
            lines = A.describe(mine, plan)
            out.step(6, "Answer")
            for ln in lines:
                out.say(ln, "1" if ln.startswith(("Buy", "Pack")) else None)
            summary["plan"] = {
                "reach_best_ok": plan["reach_best"]["ok"],
                "reach_target_ok": plan["reach_target"]["ok"],
                "weakest_now": plan["chains"][0]["weakest_item"] if plan["chains"] else None,
                "best_mode_now": plan["chains"][0]["best_mode"] if plan["chains"] else None,
                "considering_fixes_venue": plan.get("considering", {}).get("fixes_venue"),
                "buy": plan["buy"]["buy"] if plan["buy"] else None,
                "buy_fixed_venues": plan["buy"]["fixed_venues"] if plan["buy"] else [],
                "buy_ties": plan["buy_ties"],
                "after_ok": {v: r["ok"] for v, r in plan["after"].items()},
                "pack": plan["pack"], "leave": plan["leave"],
                "charging": plan["power"][0]["verdict"] if plan["power"] else None,
            }
            summary["answer"] = lines
        summary["seconds"] = round(time.perf_counter() - t0, 2)
        if a.json:
            print(json.dumps(summary, indent=2))
        else:
            out.say("")
            out.say(f"done in {summary['seconds']} s, offline, no LLM. Store: {store if a.store else '(temporary)'}", "2")
    finally:
        if tmpdir:
            shutil.rmtree(tmpdir, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
