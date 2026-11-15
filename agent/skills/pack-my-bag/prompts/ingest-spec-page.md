# Prompt: turn an adapter, cable or charger spec page into a graph item

Read the product page below and produce **one JSON object** that matches
`agent/schemas/item.schema.json`. Send it as parameter `it` with the `ingest_item` recipe through
`write_cypher` on `weakest-link-mybag`, then verify it.

## Rules

- `id` starts with `my-` (for example `my-example-labs-usbc-hdmi20`). Catalog ids are refused.
- `ports`: one entry per physical connector. A captive plug on the device or its tail is
  `gender: "plug"`; a socket is `"receptacle"`. Name them `in`, `out`, `pd`, `a`, `b`.
- Passive DisplayPort-to-HDMI adapters: set `requires_dual_mode: true` on the DP plug.
- `video`: one link per direction the picture can travel, with `standard` set to a graph Standard id:
  - HDMI out: "HDMI 2.1" → `HDMI-2.1-FRL`; "HDMI 2.0" or "4K@60Hz" → `HDMI-2.0`;
    "4K@30Hz" or "HDMI 1.4" → `HDMI-1.4`. If both a version and a resolution are given and they
    disagree, use the slower.
  - DP out: "DP 1.4", "8K" or "4K@120/144" → `DP-1.4-HBR3`; otherwise `DP-1.2-HBR2`.
  - VGA out → `VGA-1200p`.
  - Passive cables: one link with `both_ways: true`.
  - Leave `gbps` out unless the page states a lower data rate. The recipe fills it from the standard.
- `power` (USB-PD pass-through or a cable's rating): link `pd → in` with `watts` set to what reaches
  the laptop ("up to 85W to the laptop" means 85), standard `USB-PD-5A` above 60 W, else `USB-PD-3A`.
- Chargers: add `endpoints: [{name: "psu", role: "power-source"}]` and a power link `psu → out`.
- `confidence`: `high` only for the maker's own page that states the standard; `medium` for a
  retailer page or when you mapped a resolution to a standard; `low` when you inferred.
- `source.supports`: copy the spec lines you used.

After the write, run the item check query from `CYPHER.md`. Then answer the user's real question,
which is usually "would this help at venue X?": run `reach` and `chains` with the bag plus the new id.
