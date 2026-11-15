# Prompt: what should I pack, and what one thing should I buy?

Inputs: the user's laptop id, the ids in their bag, the venue (just ingested or from the catalog),
their usual venues, and the mode they need (default `1080p60` for slides; use the display's best
mode as the stretch goal).

Steps (all reads on `weakest-link-mybag`, recipes passed verbatim):

1. `reach` at the display's best mode and at the needed mode. `ok: true` means it works today.
2. `chains` for the venue. The first row is the widest chain. Its `weakest_item`,
   `weakest_standard`, `weakest_confidence` and `weakest_source` are the weakest link to explain.
3. If the user asked about a product, ingest it (`ingest-spec-page.md`) and rerun `reach` and
   `chains` with it added to the bag. Say plainly whether it moves the weakest link.
4. `best_fix` with `venues` = the new venue plus the usual venues. The top `venues_fixed` wins. Break
   a tie with `best_fix` at `4K60` (prefer what also fixes the most venues there), then by id.
   Report ties as "equally good", and `still_failing` as venue-limited, not something to buy.
5. Rerun `reach` for every venue with the purchase added. Pack the bag items that appear in a
   working `chain`, and say which items can stay at home.
6. `power` with the final bag. Report the verdict (`fast-charge`, `full-speed`,
   `below-recommended`) and its weakest link.

Answer in the shape given in `system.md`. Every number comes from a query result.
