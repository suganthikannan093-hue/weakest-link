#!/usr/bin/env python3
"""Build the Weakest Link graph.

data/src/*.json (hand-written, cited)
  -> validate
  -> data/build/graph.json   (flat node/relationship lists, also used by the browser build)
  -> data/csv/*.csv          (the same graph as plain CSV, for inspection and reuse)
  -> data/weakest-link.rl    (single-file Relate store, written by the `relate` CLI
                               running scripts/import.cypher with graph.json as $g)

Usage: python3 scripts/build_store.py [--no-store]
"""
import csv
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "src"
BUILD = ROOT / "data" / "build"
CSV_DIR = ROOT / "data" / "csv"
STORE = ROOT / "data" / "weakest-link.rl"
CONFIDENCE = {"high", "medium", "low"}
KINDS = {"laptop", "phone", "tablet", "adapter", "cable", "charger", "display"}
DEVICES = {"laptop", "phone", "tablet"}  # things you carry that render video and charge
DATA_LICENSE = "CC-BY-4.0"


def load(name):
    with open(SRC / name, encoding="utf-8") as f:
        return json.load(f)


class Invalid(Exception):
    pass


def build_graph():
    sources = {s["id"]: s for s in load("sources.json")}
    standards = {s["id"]: s for s in load("standards.json")}
    modes = {m["id"]: m for m in load("modes.json")}
    items = load("items.json")["items"]
    venues = load("venues.json")
    errors = []

    def need(cond, msg):
        if not cond:
            errors.append(msg)

    for st in standards.values():
        need(st["source"] in sources, f"standard {st['id']}: unknown source {st['source']}")
    for m in modes.values():
        # 8-bit RGB (24 bit/pixel) uncompressed data rate
        m["gbps"] = round(m["pixel_clock_mhz"] * 24 / 1000, 3)
        m["source_url"] = sources[m["source"]]["url"]

    g = {k: [] for k in ("sources", "standards", "modes", "items", "ports", "endpoints", "venues",
                         "has_port", "has_endpoint", "video", "power", "mates", "supports_mode",
                         "provides", "conforms_to", "cites")}
    g["sources"] = list(sources.values())
    g["standards"] = list(standards.values())
    g["modes"] = list(modes.values())

    item_ids = set()
    port_index = {}
    for it in items:
        iid = it["id"]
        need(iid not in item_ids, f"duplicate item {iid}")
        item_ids.add(iid)
        need(it["kind"] in KINDS, f"{iid}: bad kind")
        node = {k: v for k, v in it.items() if k not in ("ports", "video", "power", "modes", "bidirectional")}
        node.setdefault("purchasable", False)
        node["license"] = DATA_LICENSE
        g["items"].append(node)

        local = {}
        for p in it.get("ports", []):
            pid = f"{iid}:{p['id']}"
            need(p["gender"] in {"plug", "receptacle"}, f"{pid}: bad gender")
            port = {"id": pid, "item": iid, "name": p["id"], "connector": p["connector"], "gender": p["gender"],
                    "dual_mode": p.get("dual_mode", False), "requires_dual_mode": p.get("requires_dual_mode", False)}
            if p.get("note"):
                port["note"] = p["note"]
            g["ports"].append(port)
            g["has_port"].append({"item": iid, "port": pid})
            port_index[pid] = port
            local[p["id"]] = pid

        # Internal endpoints: where a signal starts or ends inside an item.
        roles = [("gpu", "video-source"), ("battery", "power-sink")] if it["kind"] in DEVICES else \
            {"display": [("panel", "video-sink")], "charger": [("psu", "power-source")]}.get(it["kind"], [])
        # Docks and USB-C monitors with their own power supply can charge a laptop too.
        if it["kind"] != "charger" and any(e.get("from") == "psu" for e in it.get("power", [])):
            roles = roles + [("psu", "power-source")]
        for name, role in roles:
            eid = f"{iid}:{name}"
            g["endpoints"].append({"id": eid, "item": iid, "name": name, "role": role})
            g["has_endpoint"].append({"item": iid, "endpoint": eid})
            local[name] = eid

        cited = set()
        for domain in ("video", "power"):
            for e in it.get(domain, []):
                where = f"{iid} {domain} {e.get('from')}->{e.get('to')}"
                need(e.get("from") in local and e.get("to") in local, f"{where}: unknown port/endpoint")
                need(e.get("source") in sources, f"{where}: unknown source {e.get('source')}")
                need(e.get("confidence") in CONFIDENCE, f"{where}: confidence must be high/medium/low")
                props = {"item": iid, "from_item": iid, "to_item": iid, "source": e.get("source"),
                         "source_url": sources.get(e.get("source"), {}).get("url"),
                         "confidence": e.get("confidence"), "note": e.get("note")}
                if e.get("standard"):
                    st = standards.get(e["standard"])
                    need(st is not None, f"{where}: unknown standard {e['standard']}")
                    if st is None:
                        continue
                    props["standard"] = st["id"]
                    if domain == "video":
                        props["gbps"] = st["data_gbps"]
                    else:
                        props["watts"] = st["watts"]
                    g["conforms_to"].append({"item": iid, "standard": st["id"]})
                if domain == "video":
                    need(props.get("gbps") is not None, f"{where}: video edge needs a standard with data_gbps")
                if domain == "power" and "watts" in e:
                    props["watts"] = e["watts"]
                cited.add(e.get("source"))
                pairs = [(e.get("from"), e.get("to"))]
                if it.get("bidirectional"):
                    pairs.append((e.get("to"), e.get("from")))
                for a, b in pairs:
                    if a in local and b in local:
                        g[domain].append({"from": local[a], "to": local[b], "props": props})
        for s in sorted(c for c in cited if c in sources):
            g["cites"].append({"item": iid, "source": s})
        for m in it.get("modes", []):
            need(m in modes, f"{iid}: unknown mode {m}")
            g["supports_mode"].append({"endpoint": f"{iid}:panel", "mode": m})
        if it["kind"] == "display":
            need(bool(it.get("modes")), f"{iid}: display needs modes")
        if it["kind"] in DEVICES:
            for m in modes:  # every modelled device GPU can render every mode here; ports set the limit
                g["supports_mode"].append({"endpoint": f"{iid}:gpu", "mode": m})

    # Physical mating: a plug fits a receptacle of the same connector on a different item.
    # MATES is created in both directions because video and power flow opposite ways
    # through the same physical connection; queries alternate MATES with an internal hop.
    plugs = [p for p in g["ports"] if p["gender"] == "plug"]
    recs = [p for p in g["ports"] if p["gender"] == "receptacle"]
    for p in plugs:
        for r in recs:
            if p["connector"] != r["connector"] or p["item"] == r["item"]:
                continue
            if p["requires_dual_mode"] and not r["dual_mode"]:
                continue
            g["mates"].append({"from": p["id"], "to": r["id"], "props": {"from_item": p["item"], "to_item": r["item"], "connector": p["connector"]}})
            g["mates"].append({"from": r["id"], "to": p["id"], "props": {"from_item": r["item"], "to_item": p["item"], "connector": p["connector"]}})

    for v in venues:
        g["venues"].append({k: v[k] for k in ("id", "name", "description")})
        for iid in v["provides"]:
            need(iid in item_ids, f"venue {v['id']}: unknown item {iid}")
            g["provides"].append({"venue": v["id"], "item": iid})

    # de-duplicate CONFORMS_TO
    g["conforms_to"] = [dict(t) for t in sorted({tuple(sorted(d.items())) for d in g["conforms_to"]})]
    if errors:
        raise Invalid("\n".join(errors))
    return g


def write_csv(g):
    if CSV_DIR.exists():
        shutil.rmtree(CSV_DIR)
    CSV_DIR.mkdir(parents=True)
    for key, rows in g.items():
        if not rows:
            continue
        flat = []
        for r in rows:
            row = dict(r)
            props = row.pop("props", None) or {}
            row.update(props)
            flat.append({k: (json.dumps(v) if isinstance(v, (list, dict)) else v) for k, v in row.items()})
        cols = []
        for r in flat:
            for k in r:
                if k not in cols:
                    cols.append(k)
        prefix = "nodes" if key in ("sources", "standards", "modes", "items", "ports", "endpoints", "venues") else "rels"
        with open(CSV_DIR / f"{prefix}_{key}.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=cols)
            w.writeheader()
            w.writerows(flat)


def build_store(graph_json):
    relate = shutil.which("relate")
    if not relate:
        sys.exit("relate CLI not found. Install: curl -sSfL https://relatedb.ai/install.sh | bash")
    for p in (STORE, STORE.with_suffix(".rl.lock")):
        if p.exists():
            p.unlink()
    script = (ROOT / "scripts" / "import.cypher").read_text(encoding="utf-8")
    res = subprocess.run([relate, "--database", str(STORE), "--fetch-params", f"g={graph_json}",
                          "--mode", "jsonl", "query"], input=script, text=True, capture_output=True)
    if res.returncode != 0:
        sys.exit(f"relate import failed ({res.returncode}):\n{res.stderr}\n{res.stdout}")
    res = subprocess.run([relate, "--database", str(STORE), "--read-only", "--json", "-c",
                          "MATCH (n) RETURN labels(n)[0] AS label, count(*) AS n ORDER BY label"],
                         text=True, capture_output=True, check=True)
    return json.loads(res.stdout)["data"]


def main():
    try:
        g = build_graph()
    except Invalid as e:
        sys.exit(f"dataset validation failed:\n{e}")
    BUILD.mkdir(parents=True, exist_ok=True)
    graph_json = BUILD / "graph.json"
    graph_json.write_text(json.dumps(g, indent=1, ensure_ascii=False), encoding="utf-8")
    write_csv(g)
    counts = {k: len(v) for k, v in g.items()}
    print("graph:", json.dumps(counts))
    if "--no-store" not in sys.argv:
        print("store:", STORE.relative_to(ROOT), json.dumps(build_store(graph_json)))


if __name__ == "__main__":
    main()
