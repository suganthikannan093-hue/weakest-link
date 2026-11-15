---
name: pack-my-bag
description: Decide what to pack and the one item to buy so a laptop reaches a venue's projector or TV (and charges), using the Weakest Link graph over Relate MCP. Use when the user pastes a venue's AV email or an adapter spec page, or asks "will my laptop work at …", "what should I bring", or "which adapter should I buy".
---

# Pack my bag (Weakest Link over Relate MCP)

You need the `weakest-link-mybag` MCP server (writable) and optionally `weakest-link-catalog`
(read-only). See `agent/README.md` for client setup.

1. **Discover**: `MATCH (r:Recipe) RETURN r.name, r.kind, r.description, r.example_params` on
   `weakest-link-mybag`. Recipes are vetted Cypher. Fetch `r.cypher` and pass it verbatim.
2. **Know the user**: ask for (or look up) their laptop and bag ids with
   `MATCH (i:Item) RETURN i.id, i.name, i.kind ORDER BY i.kind`.
3. **Ingest** what they paste:
   - a venue email or page → follow [prompts/ingest-venue-email.md](prompts/ingest-venue-email.md) → `ingest_venue` via `write_cypher`
   - a product spec page → follow [prompts/ingest-spec-page.md](prompts/ingest-spec-page.md) → `ingest_item` via `write_cypher`
   - verify with the check queries in [CYPHER.md](CYPHER.md) (`write_cypher` returns only counters)
4. **Answer** with [prompts/what-to-pack.md](prompts/what-to-pack.md): `reach` → `chains` → `best_fix` → `reach` per
   venue → `power`.
5. **Explain** in plain English with the weakest link's standard, confidence and source. Never state
   a number that did not come from a query.

Rules and answer shape: [prompts/system.md](prompts/system.md). Every recipe, check query and JSON schema is in [CYPHER.md](CYPHER.md), and the prompts are copied into `prompts/`,
so this skill works even in a host that cannot read the repo.
