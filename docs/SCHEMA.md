# Graph schema

The store is `data/weakest-link.rl`, a single-file Relate store. It is generated from `data/src/*.json`
by `scripts/build_store.py`, which runs `scripts/import.cypher` with the Relate CLI.

The graph has 499 nodes and 7,958 relationships (build of milestone 4: 100 items, 9 venues, 64 sources).

## The idea in one picture

A signal (or charging power) has to travel from an internal **endpoint** inside one item to an endpoint
inside another. It passes alternately *through* an item and *across* a physical plug-into-socket joint:

```
(mba-m2:gpu) -VIDEO-> (mba-m2:tb1) -MATES-> (adapter:in) -VIDEO-> (adapter:out) -MATES-> (cable:a)
   -VIDEO-> (cable:b) -MATES-> (tv:hdmi1) -VIDEO-> (tv:panel) -SUPPORTS_MODE-> (:Mode {id:'4K60'})
```

Every `VIDEO` hop carries the uncompressed data rate the hop can sustain (`gbps`). A chain works at a
mode when every hop's `gbps` is at least the mode's `gbps` and the panel `SUPPORTS_MODE` the mode. The
hop with the lowest `gbps` is the chain's **weakest link**. Power works the same way with `POWER`
hops and `watts`.

## Node labels

| Label | Key | Properties |
|---|---|---|
| `Item` | `id` | `kind` (laptop, phone, tablet, adapter, cable, charger, display), `class` (product or generic), `name`, `maker`, `purchasable`, `pd_recommended_w`, `pd_fast_w`, `pd_source` (laptops, phones and tablets), `license` |
| `Port` | `id` = `<item>:<port>` | `item`, `name`, `connector` (USB-C, HDMI, DP, VGA, MagSafe3), `gender` (plug or receptacle), `dual_mode` (DP++ source), `requires_dual_mode` (passive DP-to-HDMI), `note` |
| `Endpoint` | `id` = `<item>:<name>` | `item`, `name` (gpu, panel, psu, battery), `role` (video-source, video-sink, power-source, power-sink). Laptops, phones and tablets have `gpu` and `battery`; displays have `panel`; chargers, and docks or monitors with their own supply, have `psu` |
| `Mode` | `id` (e.g. `4K60`) | `width`, `height`, `hz`, `pixel_clock_mhz`, `timing` (CTA-861 or CVT-RB), `gbps` (= pixel clock × 24 bit, 8-bit RGB), `rank`, `source`, `source_url`, `confidence` |
| `Standard` | `id` (e.g. `HDMI-2.0`) | `family`, `raw_gbps`, `data_gbps` (after line coding), `encoding`, `watts` (USB-PD), `source`, `confidence`, `note` |
| `Venue` | `id` | `name`, `description` |
| `Source` | `id` | `publisher`, `kind` (spec-body, manufacturer, reference; `email` for ingested venues), `title`, `url`, `supports` (what the source says) |

## Relationship types

| Type | From → To | Properties | Meaning |
|---|---|---|---|
| `HAS_PORT` | Item → Port | | physical connector on the item |
| `HAS_ENDPOINT` | Item → Endpoint | | internal source or sink |
| `VIDEO` | Endpoint/Port → Port/Endpoint (same item) | `gbps`, `standard`, `item`, `from_item`, `to_item`, `source`, `source_url`, `confidence`, `note` | the item can pass video between these points at up to `gbps` |
| `POWER` | Endpoint/Port → Port/Endpoint (same item) | `watts` (null for a laptop's input), `standard`, `item`, `from_item`, `to_item`, `source`, `source_url`, `confidence`, `note` | USB PD power can flow this way |
| `MATES` | Port ↔ Port (different items) | `from_item`, `to_item`, `connector` | a plug physically fits that receptacle. Created both ways. A passive DP++ plug only mates with a `dual_mode` receptacle |
| `SUPPORTS_MODE` | Endpoint → Mode | | the panel (or the laptop GPU) can show the mode |
| `PROVIDES` | Venue → Item | | equipment that is already at the venue |
| `CONFORMS_TO` | Item → Standard | | standards the item's links follow |
| `CITES` | Item → Source | | sources behind the item's capability edges |

Cables are symmetric, so their internal `VIDEO`/`POWER` edges exist in both directions. Converters
such as USB-C → HDMI only go one way.

## Why queries alternate hops

The queries match `(src)-[:VIDEO]->() ( ()-[:MATES]->()-[:VIDEO]->() ){1,6} (sink)`. They use a quantified path
pattern that always alternates *across a joint* and *through an item*. This rules out physically
impossible chains, such as signal entering a laptop port and leaving through the same port into a
second cable. The availability predicates (`item IN have`) and the bandwidth predicates
(`gbps >= m.gbps`) sit inside the pattern, so Relate prunes while it expands. This matters for
`SHORTEST 1`: a `WHERE` placed after a `SHORTEST` match filters only the already-selected shortest path.

## Ownership is a query parameter, not data

What the user owns (`$bag`) is passed in on each query. The store holds the shared, cited catalog and
the venues, so one committed store serves every user. Per-user state lives in a separate writable
store (`data/work/my-bag.rl`, a git-ignored copy) that the agent writes through MCP:

- Venues and items ingested from emails or spec pages get `ingested: true`, `class: 'ingested'`, a
  `confidence`, and a `CITES` link to a `Source` (`kind: email | manufacturer | …`, `supports` = the
  quoted sentences). Their `VIDEO`/`POWER` edges carry the same `source`, `source_url` and `confidence`.
- `:Recipe {name, kind, description, example_params, cypher, file}` holds the vetted read queries and
  write statements, so an MCP host can discover them with `read_cypher`.
