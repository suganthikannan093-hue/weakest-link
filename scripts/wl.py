#!/usr/bin/env python3
"""Run the Weakest Link queries against the committed Relate store with the relate CLI.

  python3 scripts/wl.py reach    --laptop mba-m2 --venue meetup-hall --bag adp-apple-av-a1621 --mode 4K60
  python3 scripts/wl.py chains   --laptop mba-m2 --venue meetup-hall --bag adp-apple-av-a1621,hub-usbc-4k30
  python3 scripts/wl.py best_fix --laptop mba-m2 --bag adp-apple-av-a1621 --venues all --mode 1080p60
  python3 scripts/wl.py power    --laptop mbp14-m3 --bag chg-apple-140w,cable-usbc-usb2-60w
  python3 scripts/wl.py list     # laptops, venues, items
"""
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STORE = ROOT / "data" / "weakest-link.rl"
QUERIES = ROOT / "queries"


def run_cypher(cypher, params=None, store=STORE):
    relate = shutil.which("relate")
    if not relate:
        raise RuntimeError("relate CLI not found. Install: curl -sSfL https://relatedb.ai/install.sh | bash")
    cmd = [relate, "--database", str(store), "--read-only", "--json", "--no-agent-mode", "--max-rows", "0"]
    for k, v in (params or {}).items():
        cmd += ["--param", f"{k}={json.dumps(v)}"]
    cmd.append("query")
    res = subprocess.run(cmd, input=cypher, text=True, capture_output=True)
    if res.returncode != 0:
        raise RuntimeError(f"relate exited {res.returncode}: {res.stderr.strip() or res.stdout.strip()}")
    out = json.loads(res.stdout)
    if out.get("error"):
        raise RuntimeError(out["error"])
    return out["data"]


def run_query(name, params=None, store=STORE):
    return run_cypher((QUERIES / f"{name}.cypher").read_text(encoding="utf-8"), params, store)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("query", choices=["reach", "chains", "best_fix", "power", "list"])
    ap.add_argument("--laptop")
    ap.add_argument("--venue")
    ap.add_argument("--venues", help="comma-separated venue ids, or 'all'")
    ap.add_argument("--bag", default="", help="comma-separated item ids")
    ap.add_argument("--mode", default="4K60")
    a = ap.parse_args()
    bag = [b for b in a.bag.split(",") if b]
    if a.query == "list":
        rows = run_cypher("MATCH (i:Item) RETURN i.kind AS kind, i.id AS id, i.name AS name ORDER BY kind, id")
        rows += run_cypher("MATCH (v:Venue) RETURN 'venue' AS kind, v.id AS id, v.name AS name ORDER BY id")
    else:
        params = {"laptop": a.laptop, "bag": bag}
        if a.query in ("reach", "chains"):
            params["venue"] = a.venue
        if a.query in ("reach", "best_fix"):
            params["mode"] = a.mode
        if a.query == "best_fix":
            if not a.venues or a.venues == "all":
                params["venues"] = [r["id"] for r in run_cypher("MATCH (v:Venue) RETURN v.id AS id ORDER BY id")]
            else:
                params["venues"] = a.venues.split(",")
        rows = run_query(a.query, params)
    for r in rows:
        print(json.dumps(r, ensure_ascii=False))
    if not rows:
        print("(no rows)", file=sys.stderr)


if __name__ == "__main__":
    main()
