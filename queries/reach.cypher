// Q1 reachability: can $laptop drive the display at venue $venue at $mode, using only
// items in $bag plus what the venue provides? Returns the shortest working chain and its bottleneck.
// Params: $laptop (Item.id), $venue (Venue.id), $bag (list of Item.id), $mode (Mode.id)
MATCH (m:Mode {id: $mode}), (v:Venue {id: $venue})
MATCH (:Item {id: $laptop})-[:HAS_ENDPOINT]->(src:Endpoint {role: 'video-source'})
MATCH (v)-[:PROVIDES]->(d:Item {kind: 'display'})-[:HAS_ENDPOINT]->(sink:Endpoint {role: 'video-sink'})
WITH m, v, d, src, sink,
     [(v)-[:PROVIDES]->(i:Item) | i.id] + $bag + [$laptop] AS have,
     EXISTS { (sink)-[:SUPPORTS_MODE]->(m) } AS panel_ok
OPTIONAL MATCH p = SHORTEST 1
  (src)-[f:VIDEO WHERE f.gbps >= m.gbps]->()
  (()-[mt:MATES WHERE mt.from_item IN have AND mt.to_item IN have]->()
     -[vv:VIDEO WHERE vv.item IN have AND vv.gbps >= m.gbps]->()){1,6}
  (sink)
WITH m, v, d, panel_ok, p, [r IN relationships(p) WHERE type(r) = 'VIDEO'] AS links
WITH m, v, d, panel_ok, p, links,
     reduce(lo = 1.0e9, r IN links | CASE WHEN r.gbps < lo THEN r.gbps ELSE lo END) AS bottleneck
RETURN v.id AS venue, d.id AS display, m.id AS mode, m.gbps AS need_gbps,
       panel_ok AND p IS NOT NULL AS ok,
       panel_ok,
       [r IN links | r.item] AS chain,
       CASE WHEN p IS NULL THEN null ELSE bottleneck END AS bottleneck_gbps,
       [r IN links WHERE r.gbps = bottleneck | r.item][0] AS weakest_item
ORDER BY ok DESC
LIMIT 1
