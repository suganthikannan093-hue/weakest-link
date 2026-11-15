#!/usr/bin/env python3
"""Start Relate's MCP server (stdio) for the Weakest Link agent.

  mcp_server.py catalog            read-only: data/weakest-link.rl (tools: read_cypher, get_schema)
  mcp_server.py mybag              writable copy: data/work/my-bag.rl (adds write_cypher)
  mcp_server.py mybag --reset      start the writable copy again from the catalog
  mcp_server.py mybag --store X    use another writable store path
  mcp_server.py init [--store X] [--reset]   create the writable store and exit

The writable store starts as a copy of the committed catalog plus :Recipe nodes (the vetted query
and ingest statements), so any MCP host can discover them with read_cypher. The committed catalog
is never opened for writing. stdout carries only JSON-RPC; messages go to stderr.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "data" / "weakest-link.rl"
DEFAULT_STORE = ROOT / "data" / "work" / "my-bag.rl"
QUERIES = ROOT / "queries"
AGENT_CYPHER = ROOT / "agent" / "cypher"

RECIPES = [
    # name, kind, file, description, example params
    ("reach", "read", QUERIES / "reach.cypher",
     "Can the laptop drive the venue's display at a mode with the bag plus what the venue provides? "
     "Returns ok, the shortest working chain, its weakest link and every hop's source and confidence.",
     {"laptop": "mba-m2", "venue": "meetup-hall", "bag": ["adp-apple-av-a1621"], "mode": "4K60"}),
    ("chains", "read", QUERIES / "chains.cypher",
     "Every distinct chain from the laptop to the venue's display, widest first, with the weakest link, "
     "its standard, confidence and source, and the best mode the chain carries.",
     {"laptop": "mba-m2", "venue": "meetup-hall", "bag": ["adp-apple-av-a1621"]}),
    ("best_fix", "read", QUERIES / "best_fix.cypher",
     "The single purchasable item that makes the mode work at the most failing venues in $venues.",
     {"laptop": "mba-m2", "bag": ["adp-apple-av-a1621"], "venues": ["meetup-hall", "studio-tv"], "mode": "4K60"}),
    ("power", "read", QUERIES / "power.cypher",
     "For each charger in the bag, the best charger-cable-laptop chain in watts and a verdict "
     "(fast-charge, full-speed, below-recommended, unknown).",
     {"laptop": "mba-m2", "bag": ["chg-apple-70w", "cable-usbc-usb2-60w"]}),
    ("ingest_venue", "write", AGENT_CYPHER / "ingest_venue.cypher",
     "Write a venue (from an email or web page) as Venue + display Item + ports + cited VIDEO edges. "
     "Idempotent per venue id. Param $v follows agent/schemas/venue.schema.json.",
     {"v": {"id": "riverside-library-room-2", "name": "Riverside Library, Room 2", "confidence": "medium",
            "source": {"id": "email-riverside", "kind": "email", "supports": "Full HD projector, HDMI and VGA inputs"},
            "display": {"name": "Room 2 projector", "max_mode": "1080p60",
                        "inputs": [{"connector": "HDMI", "standard": "HDMI-1.4"}]},
            "provides": ["cable-hdmi-standard"]}}),
    ("ingest_item", "write", AGENT_CYPHER / "ingest_item.cypher",
     "Write an adapter, cable or charger (from its spec page) as Item + ports + cited VIDEO/POWER edges "
     "and MATES to every compatible port. Ids start with my-. Param $it follows agent/schemas/item.schema.json.",
     {"it": {"id": "my-adp-usbc-hdmi20", "name": "USB-C to HDMI 2.0 adapter", "kind": "adapter", "confidence": "medium",
             "source": {"id": "spec-x", "kind": "manufacturer", "url": "https://example.org"},
             "ports": [{"name": "in", "connector": "USB-C", "gender": "plug"},
                       {"name": "out", "connector": "HDMI", "gender": "receptacle"}],
             "video": [{"from": "in", "to": "out", "standard": "HDMI-2.0"}]}}),
]


def relate_bin():
    found = os.environ.get("RELATE_BIN") or shutil.which("relate")
    if not found:
        home = Path.home() / ".local" / "bin" / ("relate.exe" if os.name == "nt" else "relate")
        found = str(home) if home.exists() else None
    if not found:
        sys.exit("relate CLI not found. Install: curl -sSfL https://relatedb.ai/install.sh | bash "
                 "(or set RELATE_BIN to its full path)")
    return found


def recipes():
    return [{"name": n, "kind": k, "file": str(f.relative_to(ROOT)), "description": d,
             "example_params": json.dumps(ex), "cypher": f.read_text(encoding="utf-8")}
            for n, k, f, d, ex in RECIPES]


def init_store(store: Path, reset=False):
    store = Path(store)
    if store.exists() and not reset:
        return store
    if store.resolve() == CATALOG.resolve():
        sys.exit("refusing to use the committed catalog as the writable store")
    store.parent.mkdir(parents=True, exist_ok=True)
    for p in (store, Path(str(store) + ".lock")):
        if p.exists():
            p.unlink()
    shutil.copyfile(CATALOG, store)
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as fh:
        json.dump(recipes(), fh)
        tmp = fh.name
    try:
        res = subprocess.run(
            [relate_bin(), "--database", str(store), "--json", "--no-agent-mode", "--fetch-params", f"r={tmp}", "query"],
            input="UNWIND $r AS x CREATE (q:Recipe) SET q = x RETURN count(q) AS recipes",
            text=True, capture_output=True)
    finally:
        os.unlink(tmp)
    if res.returncode != 0 or json.loads(res.stdout).get("error"):
        sys.exit(f"could not seed recipes: {res.stderr or res.stdout}")
    print(f"weakest-link: created writable store {store} (catalog copy + {len(RECIPES)} recipes)", file=sys.stderr)
    return store



def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("which", choices=["catalog", "mybag", "init"])
    ap.add_argument("--store", default=os.environ.get("WEAKEST_LINK_STORE", str(DEFAULT_STORE)))
    ap.add_argument("--reset", action="store_true")
    a = ap.parse_args(argv)
    if a.which == "catalog":
        cmd = [relate_bin(), "serve", "--database", str(CATALOG), "--mcp", "stdio", "--read-only"]
    else:
        store = init_store(Path(a.store), a.reset)
        if a.which == "init":
            print(store)
            return 0
        cmd = [relate_bin(), "serve", "--database", str(store), "--mcp", "stdio"]
    if os.name == "posix":
        os.execv(cmd[0], cmd)
    return subprocess.call(cmd)


if __name__ == "__main__":
    sys.exit(main())
