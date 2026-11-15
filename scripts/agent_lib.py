"""Weakest Link agent toolkit: a dependency-free MCP stdio client for Relate, deterministic
extractors for venue emails and adapter spec pages, and a planner that turns query results into a
packing list. No LLM and no network access is needed.

In a real MCP host (Claude Desktop, Cursor, VS Code ...) the host's model does the extraction step
by following agent/prompts/. The extractors here cover the sample formats so the demo and CI run
offline and give the same answer every time.
"""
import email
import email.utils
import html
import json
import queue
import re
import subprocess
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
QUERIES = ROOT / "queries"
AGENT_CYPHER = ROOT / "agent" / "cypher"
MODE_RANK = {"720p60": 1, "1080p60": 2, "1440p60": 3, "4K30": 4, "4K60": 5}
MODE_LABEL = {"720p60": "720p at 60 Hz", "1080p60": "1080p (Full HD) at 60 Hz", "1440p60": "1440p at 60 Hz",
              "4K30": "4K at 30 Hz", "4K60": "4K at 60 Hz"}


# ---------------------------------------------------------------- MCP client
class McpError(RuntimeError):
    pass


class McpClient:
    """Minimal MCP client over stdio (newline-delimited JSON-RPC 2.0)."""

    def __init__(self, argv, timeout=60, name="weakest-link-agent"):
        self.timeout = timeout
        self.proc = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE, text=True, encoding="utf-8", cwd=ROOT)
        self._q = queue.Queue()
        self._stderr = []
        threading.Thread(target=self._pump, daemon=True).start()
        threading.Thread(target=lambda: self._stderr.extend(self.proc.stderr), daemon=True).start()
        self._id = 0
        init = self.request("initialize", {"protocolVersion": "2025-06-18", "capabilities": {},
                                           "clientInfo": {"name": name, "version": "1.0"}})
        self.server_info = init.get("serverInfo", {})
        self._send({"jsonrpc": "2.0", "method": "notifications/initialized"})

    def _pump(self):
        for line in self.proc.stdout:
            if line.strip():
                self._q.put(json.loads(line))
        self._q.put(None)

    def _send(self, msg):
        self.proc.stdin.write(json.dumps(msg) + "\n")
        self.proc.stdin.flush()

    def request(self, method, params=None):
        self._id += 1
        self._send({"jsonrpc": "2.0", "id": self._id, "method": method, "params": params or {}})
        while True:
            try:
                msg = self._q.get(timeout=self.timeout)
            except queue.Empty:
                raise McpError(f"timeout waiting for {method}")
            if msg is None:
                raise McpError("MCP server exited: " + "".join(self._stderr)[-500:])
            if msg.get("id") == self._id:
                if "error" in msg:
                    raise McpError(msg["error"].get("message", str(msg["error"])))
                return msg["result"]

    def tools(self):
        return [t["name"] for t in self.request("tools/list")["tools"]]

    def call(self, tool, arguments):
        res = self.request("tools/call", {"name": tool, "arguments": arguments})
        text = "".join(c.get("text", "") for c in res.get("content", []))
        if res.get("isError"):
            raise McpError(text)
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return text
        if isinstance(data, dict) and data.get("error"):
            raise McpError(str(data["error"]))
        return data

    def read(self, statement, params=None):
        return self.call("read_cypher", {"statement": statement, "parameters": params or {}})["rows"]

    def write(self, statement, params=None):
        return self.call("write_cypher", {"statement": statement, "parameters": params or {}})

    def query(self, name, params):
        return self.read((QUERIES / f"{name}.cypher").read_text(encoding="utf-8"), params)

    def close(self):
        try:
            self.proc.stdin.close()
            self.proc.wait(timeout=10)
        except Exception:
            self.proc.kill()
            self.proc.wait()
        for f in (self.proc.stdout, self.proc.stderr):
            try:
                f.close()
            except Exception:
                pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def server_argv(which, store=None):
    argv = [sys.executable, str(ROOT / "scripts" / "mcp_server.py"), which]
    if store:
        argv += ["--store", str(store)]
    return argv


# ---------------------------------------------------------------- extraction helpers
def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def sentences(text):
    text = re.sub(r"\s+", " ", text)
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]


NEGATION = re.compile(r"\b(no|not|don't|do not|doesn't|does not|never|without|isn't|aren't|unavailable)\b", re.I)


def _max_mode(text):
    """Best mode the display can show, read conservatively. Returns (mode, confidence, evidence)."""
    t = text
    m4k = re.search(r"\b(4K|UHD|2160p?|3840\s*[x×]\s*2160)\b", t, re.I)
    if m4k:
        if re.search(r"\b60\s*Hz\b|4K\s*@?\s*60|2160p60", t, re.I):
            return "4K60", "medium", m4k.group(0)
        return "4K30", "low", m4k.group(0) + " (refresh rate not stated, assumed 30 Hz)"
    for pat, mode in [(r"\b(1440p|2560\s*[x×]\s*1440|QHD)\b", "1440p60"),
                      (r"\b(1080p?|Full HD|FHD|1920\s*[x×]\s*10[48]0|WUXGA|1920\s*[x×]\s*1200)\b", "1080p60"),
                      (r"\b(720p|1280\s*[x×]\s*720|HD ready)\b", "720p60")]:
        m = re.search(pat, t, re.I)
        if m:
            return mode, "medium", m.group(0)
    return "720p60", "low", "resolution not stated, assumed 720p"


def _strip_salutations(body):
    keep = []
    for line in body.splitlines():
        if re.match(r"\s*(best|kind regards|regards|thanks|cheers|sincerely|many thanks)\b[^.]*,?\s*$", line, re.I):
            break
        if re.match(r"\s*(hi|hello|dear)\b[^.]*[,!]\s*$", line, re.I):
            continue
        keep.append(line)
    return "\n".join(keep)


def extract_venue_email(raw, display_kind=None):
    """Deterministic extractor for a venue's AV email -> param $v of ingest_venue."""
    msg = email.message_from_string(raw)
    body = msg.get_payload() if not msg.is_multipart() else msg.get_payload(0).get_payload()
    name_from, addr = email.utils.parseaddr(msg.get("From", ""))
    subject = msg.get("Subject", "")
    date = email.utils.parsedate_to_datetime(msg["Date"]).date().isoformat() if msg.get("Date") else ""
    body = _strip_salutations(body)
    org = " ".join(w.capitalize() for w in addr.split("@")[-1].split(".")[0].split("-")) if addr else "Venue"
    sents = sentences(body)
    room = None
    for s in sents:
        m = re.search(r"\b((?:Room|Hall|Suite|Studio|Ballroom|Theatre|Auditorium)\s+[A-Z0-9][\w-]*"
                      r"|(?:the\s+)?[A-Z][a-z]+\s+(?:Room|Hall|Suite|Studio|Ballroom|Theatre|Auditorium))\b", s)
        if m:
            room = re.sub(r"^the\s+", "", m.group(1), flags=re.I)
            break
    venue_name = f"{org}, {room}" if room and org.split()[0].lower() not in room.lower() else (room or org)
    if room and org.split()[0].lower() in room.lower():
        venue_name = f"{room}, {org}"
    evidence = []

    display_s = [s for s in sents if re.search(r"projector|\bTV\b|display|screen|monitor", s, re.I)]
    kind = display_kind or next((k for k, p in [("projector", r"projector"), ("TV", r"\bTV\b"),
                                                ("display", r"display|monitor|screen")]
                                 if any(re.search(p, s, re.I) for s in display_s)), "display")
    mode, mode_conf, mode_ev = _max_mode(" ".join(display_s) or body)
    evidence += display_s[:1]

    inputs, seen = [], set()
    input_s = [s for s in sents if re.search(r"\binputs?\b|\bports?\b|lectern|plug", s, re.I)
               and re.search(r"HDMI|VGA|DisplayPort|\bDP\b|USB-?C", s, re.I) and not re.search(r"\bcables?\b", s, re.I)]
    for s in input_s:
        for m in re.finditer(r"HDMI(?:\s*(1\.4|2\.0|2\.1))?|VGA|DisplayPort(?:\s*(1\.2|1\.4))?|\bDP\b|USB-?C", s, re.I):
            tok = m.group(0).upper()
            if tok.startswith("HDMI"):
                ver = m.group(1)
                if ver:
                    std, conf, note = {"1.4": "HDMI-1.4", "2.0": "HDMI-2.0", "2.1": "HDMI-2.1-FRL"}[ver], "medium", f"HDMI {ver} stated"
                elif MODE_RANK[mode] >= MODE_RANK["4K60"]:
                    std, conf, note = "HDMI-2.0", "low", "HDMI version not stated; a 4K60 display implies at least HDMI 2.0"
                else:
                    std, conf, note = "HDMI-1.4", "low", "HDMI version not stated; assumed HDMI 1.4"
                inp = ("HDMI", std, conf, note)
            elif tok == "VGA":
                inp = ("VGA", "VGA-1200p", "medium", "VGA input")
            elif tok.startswith("USB"):
                inp = ("USB-C", "DP-Alt-4L-HBR3", "low", "USB-C input assumed to take DisplayPort Alt Mode")
            else:
                ver = m.group(2)
                inp = ("DP", "DP-1.4-HBR3" if ver == "1.4" else "DP-1.2-HBR2", "medium" if ver else "low",
                       f"DisplayPort {ver} stated" if ver else "DisplayPort version not stated; assumed 1.2")
            if (inp[0], inp[1]) not in seen:
                seen.add((inp[0], inp[1]))
                inputs.append({"connector": inp[0], "standard": inp[1], "confidence": inp[2], "note": inp[3]})
        evidence.append(s)

    provides = []
    for s in sents:
        if not re.search(r"\bcables?\b", s, re.I) or NEGATION.search(s):
            continue
        if re.search(r"HDMI", s, re.I):
            if re.search(r"ultra", s, re.I) or re.search(r"48\s*Gbps", s, re.I):
                provides.append("cable-hdmi-ultra")
            elif re.search(r"premium", s, re.I) or re.search(r"18\s*Gbps", s, re.I):
                provides.append("cable-hdmi-premium")
            elif re.search(r"high[\s-]speed", s, re.I) or re.search(r"10\.2\s*Gbps", s, re.I):
                provides.append("cable-hdmi-high-speed")
            else:  # "older", "standard" or unknown grade: assume the slowest HDMI cable
                provides.append("cable-hdmi-standard")
        if re.search(r"\bVGA\b", s, re.I):
            provides.append("cable-vga")
        evidence.append(s)

    explicit = mode_conf == "medium" and all(i["confidence"] == "medium" for i in inputs)
    vid = slug(venue_name)
    return {
        "id": vid,
        "name": venue_name,
        "description": " ".join(dict.fromkeys(evidence))[:400],
        "confidence": "medium" if explicit else "low",
        "source": {"id": f"email-{vid}-{date}".strip("-"), "kind": "email",
                   "publisher": f"{name_from} <{addr}>" if name_from else addr,
                   "title": subject, "url": None,
                   "supports": " ".join(dict.fromkeys(evidence))[:600]},
        "display": {"name": f"{venue_name} {kind}", "max_mode": mode,
                    "mode_evidence": mode_ev,
                    "inputs": inputs or [{"connector": "HDMI", "standard": "HDMI-1.4", "confidence": "low",
                                          "note": "No inputs listed; assumed one HDMI 1.4 input"}]},
        "provides": list(dict.fromkeys(provides)),
    }


def _spec_rows(page):
    rows = {}
    for th, td in re.findall(r"<tr>\s*<th[^>]*>(.*?)</th>\s*<td[^>]*>(.*?)</td>", page, re.I | re.S):
        rows[html.unescape(re.sub(r"<[^>]+>", "", th)).strip().lower()] = html.unescape(re.sub(r"<[^>]+>", "", td)).strip()
    return rows


def extract_spec_page(page, url=None):
    """Deterministic extractor for an adapter spec page (HTML) -> param $it of ingest_item."""
    title = re.search(r"<h1[^>]*>(.*?)</h1>", page, re.I | re.S) or re.search(r"<title>(.*?)</title>", page, re.I | re.S)
    name = html.unescape(re.sub(r"<[^>]+>", "", title.group(1))).split("|")[0].strip()
    maker_m = re.search(r'<meta\s+name="brand"\s+content="([^"]+)"', page, re.I)
    maker = maker_m.group(1) if maker_m else name.split()[0]
    canon = re.search(r'<link\s+rel="canonical"\s+href="([^"]+)"', page, re.I)
    url = url or (canon.group(1) if canon else None)
    rows = _spec_rows(page)
    inp, out = rows.get("input", ""), rows.get("output", "")
    res = rows.get("max resolution", rows.get("resolution", ""))
    pd = rows.get("power delivery", "")

    def conn(s):
        for pat, c in [(r"USB-?C|Thunderbolt", "USB-C"), (r"HDMI", "HDMI"), (r"DisplayPort|\bDP\b", "DP"), (r"VGA", "VGA")]:
            if re.search(pat, s, re.I):
                return c
        return None

    def gender(s, default):
        return "plug" if re.search(r"\bplug|male\b", s, re.I) else "receptacle" if re.search(r"port|socket|female", s, re.I) else default

    in_c, out_c = conn(inp), conn(out)
    ports = [{"name": "in", "connector": in_c, "gender": gender(inp, "plug")},
             {"name": "out", "connector": out_c, "gender": gender(out, "receptacle")}]
    supports = []
    if out_c == "HDMI":
        ver = re.search(r"HDMI\s*(1\.4|2\.0|2\.1)", out, re.I)
        if ver:
            std = {"1.4": "HDMI-1.4", "2.0": "HDMI-2.0", "2.1": "HDMI-2.1-FRL"}[ver.group(1)]
            conf = "high" if re.search(r"4K\s*@?\s*60", res, re.I) or ver.group(1) != "2.0" else "medium"
        else:
            std, conf = ("HDMI-2.0", "medium") if re.search(r"4K\s*@?\s*60", res, re.I) else ("HDMI-1.4", "low")
    elif out_c == "DP":
        std, conf = ("DP-1.4-HBR3", "medium") if re.search(r"1\.4|8K|4K\s*@?\s*1[24]", out + res, re.I) else ("DP-1.2-HBR2", "low")
    else:
        std, conf = "VGA-1200p", "medium"
    supports.append(f"Input: {inp}. Output: {out}. Max resolution: {res}.")
    item = {
        "id": "my-" + slug(name if name.lower().startswith(maker.lower()) else f"{maker} {name}"),
        "name": name, "kind": "adapter", "maker": maker, "purchasable": True, "confidence": conf,
        "source": {"id": "spec-" + slug(name), "kind": "manufacturer", "publisher": maker,
                   "title": name, "url": url, "supports": ""},
        "ports": ports,
        "video": [{"from": "in", "to": "out", "standard": std, "note": f"Spec page: {out}; {res}".strip("; ")}],
    }
    w = re.search(r"up to\s*(\d+)\s*W", pd, re.I) or re.search(r"(\d+)\s*W", pd, re.I)
    if pd and w and in_c == "USB-C":
        watts = int(w.group(1))
        item["ports"].append({"name": "pd", "connector": "USB-C", "gender": "receptacle"})
        item["power"] = [{"from": "pd", "to": "in", "standard": "USB-PD-5A" if watts > 60 else "USB-PD-3A",
                          "watts": watts, "note": f"PD pass-through: {pd}"}]
        supports.append(f"Power Delivery: {pd}.")
    item["source"]["supports"] = " ".join(supports)
    return item


# ---------------------------------------------------------------- verification reads after a write
VENUE_CHECK = """
MATCH (v:Venue {id: $id})-[:PROVIDES]->(d:Item {kind: 'display'})-[:HAS_ENDPOINT]->(e:Endpoint)
RETURN v.name AS venue, v.confidence AS confidence, d.id AS display,
       [(e)-[:SUPPORTS_MODE]->(m:Mode) | m.id] AS modes,
       [(d)-[:HAS_PORT]->(p:Port)-[x:VIDEO]->(e) | {connector: p.connector, gbps: x.gbps, standard: x.standard, confidence: x.confidence}] AS inputs,
       [(v)-[:PROVIDES]->(c:Item) WHERE c.kind <> 'display' | c.id] AS provides,
       COUNT { (d)-[:HAS_PORT]->(:Port)-[:MATES]->(:Port) } AS joints,
       [(d)-[:CITES]->(s:Source) | s.id][0] AS source
"""
ITEM_CHECK = """
MATCH (i:Item {id: $id})
RETURN i.name AS name, i.confidence AS confidence,
       [(i)-[:HAS_PORT]->(p:Port) | p.name + ':' + p.connector + ':' + p.gender] AS ports,
       COUNT { (i)-[:HAS_PORT]->(:Port)-[:MATES]->(:Port) } AS joints,
       [(i)-[:HAS_PORT]->(:Port)-[x:VIDEO]->() | x.gbps] AS video_gbps,
       [(i)-[:HAS_PORT]->(:Port)-[x:POWER]->() | x.watts] AS power_w,
       [(i)-[:CITES]->(s:Source) | s.url][0] AS source_url
"""


def check_venue(client, vid):
    rows = client.read(VENUE_CHECK, {"id": vid})
    return rows[0] if rows else None


def check_item(client, iid):
    rows = client.read(ITEM_CHECK, {"id": iid})
    return rows[0] if rows else None


# ---------------------------------------------------------------- planning (what to pack, what to buy)
def names(client, ids):
    if not ids:
        return {}
    rows = client.read("MATCH (i:Item) WHERE i.id IN $ids RETURN i.id AS id, i.name AS name", {"ids": list(ids)})
    return {r["id"]: r["name"] for r in rows}


def venue_names(client, ids):
    rows = client.read("MATCH (v:Venue) WHERE v.id IN $ids RETURN v.id AS id, v.name AS name", {"ids": list(ids)})
    return {r["id"]: r["name"] for r in rows}


def plan_trip(client, profile, venue_id, venue_mode, considering=None):
    """Answer 'what do I pack and what single item should I buy?' using only the four queries."""
    laptop, bag = profile["laptop"], list(profile["bag"])
    target = profile.get("target_mode", "1080p60")
    venues = [venue_id] + [v for v in profile.get("usual_venues", []) if v != venue_id]
    out = {"laptop": laptop, "venue": venue_id, "venue_mode": venue_mode, "target_mode": target}

    # 1. the new venue, at the best mode its display can show and at the target mode
    out["reach_best"] = client.query("reach", {"laptop": laptop, "venue": venue_id, "bag": bag, "mode": venue_mode})[0]
    out["reach_target"] = client.query("reach", {"laptop": laptop, "venue": venue_id, "bag": bag, "mode": target})[0]
    out["chains"] = client.query("chains", {"laptop": laptop, "venue": venue_id, "bag": bag})

    # 2. is the item the user is considering any help here?
    if considering:
        r = client.query("reach", {"laptop": laptop, "venue": venue_id, "bag": bag + [considering], "mode": target})[0]
        ch = client.query("chains", {"laptop": laptop, "venue": venue_id, "bag": bag + [considering]})
        rb = client.query("reach", {"laptop": laptop, "venue": venue_id, "bag": bag + [considering], "mode": venue_mode})[0]
        out["considering"] = {"item": considering, "fixes_venue": bool(r["ok"]) and not out["reach_target"]["ok"],
                              "upgrades_venue": bool(rb["ok"]) and not out["reach_best"]["ok"],
                              "reach": r, "weakest_with_it": ch[0]["weakest_item"] if ch else None}

    # 3. one purchase across this venue and the usual ones (tie-break: what also works at 4K60)
    fixes = client.query("best_fix", {"laptop": laptop, "bag": bag, "venues": venues, "mode": target})
    out["best_fix"] = fixes
    if fixes:
        top = [f for f in fixes if f["venues_fixed"] == fixes[0]["venues_fixed"]]
        hi = {f["buy"]: f["venues_fixed"] for f in
              client.query("best_fix", {"laptop": laptop, "bag": bag, "venues": venues, "mode": "4K60"})}
        top.sort(key=lambda f: (-hi.get(f["buy"], 0), f["buy"]))
        out["buy"] = dict(top[0], also_4k60=hi.get(top[0]["buy"], 0))
        out["buy_ties"] = [f["buy"] for f in top[1:]]
    else:
        out["buy"] = None
        out["buy_ties"] = []

    # 4. the packing list after the purchase: the items each venue's working chain uses
    final_bag = bag + ([out["buy"]["buy"]] if out["buy"] else [])
    per_venue = {}
    for v in venues:
        r = client.query("reach", {"laptop": laptop, "venue": v, "bag": final_bag, "mode": target})[0]
        per_venue[v] = r
    out["after"] = per_venue
    power = client.query("power", {"laptop": laptop, "bag": final_bag})
    out["power"] = power
    used = set()
    for r in per_venue.values():
        used.update(i for i in (r["chain"] or []) if i in final_bag)
    if power:
        used.update(i for i in (power[0]["chain"] or []) if i in final_bag)
    out["pack"] = [i for i in final_bag if i in used]
    out["leave"] = [i for i in final_bag if i not in used]
    return out


def describe(client, plan):
    """Plain-English answer for a plan from plan_trip()."""
    ids = set(plan["pack"]) | set(plan["leave"]) | {plan["laptop"]}
    for r in [plan["reach_best"], plan["reach_target"]] + list(plan["after"].values()):
        ids.update(r["chain"] or [])
    ids.update(h["weakest_item"] for h in plan["chains"] if h.get("weakest_item"))
    if plan.get("considering"):
        ids.update(x for x in (plan["considering"]["item"], plan["considering"]["weakest_with_it"]) if x)
    if plan["buy"]:
        ids.add(plan["buy"]["buy"])
        ids.update(plan["buy_ties"])
    nm = names(client, ids)
    vn = venue_names(client, list(plan["after"]))
    n = lambda i: nm.get(i, i)
    lines = []
    v = vn.get(plan["venue"], plan["venue"])
    rb, rt = plan["reach_best"], plan["reach_target"]
    if rb["ok"]:
        lines.append(f"At {v} your current bag already reaches {MODE_LABEL[plan['venue_mode']]}: "
                     + " -> ".join(n(i) for i in rb["chain"]) + ".")
    else:
        best = plan["chains"][0] if plan["chains"] else None
        if best:
            weak = next((h for h in best["hops"] if h["item"] == best["weakest_item"]), {})
            lines.append(f"At {v} your current bag only reaches {MODE_LABEL.get(best['best_mode'], 'no picture')} "
                         f"(the display can do {MODE_LABEL[plan['venue_mode']]}). The weakest link is "
                         f"{n(best['weakest_item'])} at {best['bottleneck_gbps']} Gbps ({weak.get('standard')}, "
                         f"{weak.get('confidence')} confidence, source: {weak.get('source_url') or 'the venue email'}).")
        else:
            lines.append(f"At {v} nothing in your bag connects your laptop to the display.")
    c = plan.get("considering")
    if c:
        if c["fixes_venue"]:
            lines.append(f"The {n(c['item'])} you asked about would fix {v}.")
        elif rt["ok"] and c.get("upgrades_venue"):
            lines.append(f"Your bag already works at {v} at {MODE_LABEL[plan['target_mode']]}; the {n(c['item'])} you asked "
                         f"about would take it to {MODE_LABEL[plan['venue_mode']]}.")
        elif rt["ok"]:
            lines.append(f"You don't need the {n(c['item'])} for {v}; your bag already works at {MODE_LABEL[plan['target_mode']]}.")
        else:
            w = c.get("weakest_with_it")
            lines.append(f"The {n(c['item'])} you asked about would not help at {v}: even with it, the weakest link "
                         f"is still {n(w) if w else 'missing'}." if w != c["item"] else
                         f"The {n(c['item'])} you asked about would itself be the weakest link at {v}.")
    b = plan["buy"]
    if b:
        fixed = ", ".join(vn.get(x, x) for x in b["fixed_venues"])
        line = (f"Buy one thing: {n(b['buy'])}. It makes {MODE_LABEL[plan['target_mode']]} work at {b['venues_fixed']} "
                f"more venue{'s' if b['venues_fixed'] != 1 else ''} ({fixed})")
        if b["also_4k60"]:
            line += f". It also makes 4K60 work at {b['also_4k60']} of these venues"
        lines.append(line + ".")
        if plan["buy_ties"]:
            lines.append("Equally good at that mode: " + ", ".join(n(t) for t in plan["buy_ties"]) + ".")
        if b["still_failing"]:
            lines.append("Still failing (limited by the venue's own equipment): "
                         + ", ".join(vn.get(x, x) for x in b["still_failing"]) + ".")
    else:
        lines.append(f"No single purchase is needed for {MODE_LABEL[plan['target_mode']]} at these venues."
                     if all(r["ok"] for r in plan["after"].values()) else
                     "No single purchase fixes the failing venues; their own displays are the limit.")
    lines.append("Pack: " + ", ".join(n(i) for i in plan["pack"]) + ".")
    if plan["leave"]:
        lines.append("Leave at home: " + ", ".join(n(i) for i in plan["leave"]) + ".")
    if plan["power"]:
        p = plan["power"][0]
        verdict = {"fast-charge": "fast-charges", "full-speed": "charges at full speed",
                   "below-recommended": "charges below the recommended wattage", "unknown": "charges"}[p["verdict"]]
        lines.append(f"Charging: {n(p['charger'])} + {', '.join(n(i) for i in p['chain'][1:-1]) or 'no cable'} "
                     f"{verdict} ({p['capacity_w']} W; weakest link {n(p['weakest_item'])}).")
    return lines
