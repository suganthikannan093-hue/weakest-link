// Q3 best single purchase: across the venues in $venues, which ONE purchasable item, added to
// $bag, makes $mode work at the most venues that fail today?
// Params: $laptop, $bag, $venues (list of Venue.id), $mode
// Written without CALL subqueries so that Relate's MCP read_cypher tool accepts it: each
// OPTIONAL MATCH ... SHORTEST 1 runs once per incoming row.
MATCH (m:Mode {id: $mode})
MATCH (:Item {id: $laptop})-[:HAS_ENDPOINT]->(src:Endpoint {role: 'video-source'})
UNWIND $venues AS vid
MATCH (v:Venue {id: vid})-[:PROVIDES]->(:Item {kind: 'display'})-[:HAS_ENDPOINT]->(sink:Endpoint {role: 'video-sink'})
WITH m, src, v, sink,
     [(v)-[:PROVIDES]->(i:Item) | i.id] + $bag + [$laptop] AS have,
     EXISTS { (sink)-[:SUPPORTS_MODE]->(m) } AS panel_ok
OPTIONAL MATCH p = SHORTEST 1
  (src)-[f:VIDEO WHERE f.gbps >= m.gbps]->()
  (()-[mt:MATES WHERE mt.from_item IN have AND mt.to_item IN have]->()
     -[vv:VIDEO WHERE vv.item IN have AND vv.gbps >= m.gbps]->()){1,6}
  (sink)
WITH m, src, v, sink, have, panel_ok AND p IS NOT NULL AS ok_now
WITH m, src, collect(CASE WHEN ok_now THEN null ELSE {venue: v.id, sink: sink, have: have, panel_ok: EXISTS { (sink)-[:SUPPORTS_MODE]->(m) }} END) AS failing,
     collect(CASE WHEN ok_now THEN v.id END) AS ok_venues
UNWIND failing AS fv
MATCH (c:Item {purchasable: true}) WHERE NOT c.id IN fv.have
WITH m, src, failing, ok_venues, fv, c, fv.sink AS sink, fv.have + [c.id] AS have2
OPTIONAL MATCH p = SHORTEST 1
  (src)-[f:VIDEO WHERE f.gbps >= m.gbps]->()
  (()-[mt:MATES WHERE mt.from_item IN have2 AND mt.to_item IN have2]->()
     -[vv:VIDEO WHERE vv.item IN have2 AND vv.gbps >= m.gbps]->()){1,6}
  (sink)
WITH failing, ok_venues, c, fv, p IS NOT NULL AND fv.panel_ok AS fixed
WITH failing, ok_venues, c, collect(CASE WHEN fixed THEN fv.venue END) AS fixed_venues
WHERE size(fixed_venues) > 0
RETURN c.id AS buy, c.name AS name, size(fixed_venues) AS venues_fixed, fixed_venues,
       [x IN failing WHERE NOT x.venue IN fixed_venues | x.venue] AS still_failing,
       ok_venues AS already_ok
ORDER BY venues_fixed DESC, buy
