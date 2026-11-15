// Q2 bottleneck analysis: every physically valid chain from $laptop to the venue display using
// $bag + venue items, widest first. For each chain: the weakest link (lowest-capacity edge),
// its standard, citation and confidence, and the best mode the chain can carry.
// Params: $laptop, $venue, $bag
MATCH (v:Venue {id: $venue})
MATCH (:Item {id: $laptop})-[:HAS_ENDPOINT]->(src:Endpoint {role: 'video-source'})
MATCH (v)-[:PROVIDES]->(d:Item {kind: 'display'})-[:HAS_ENDPOINT]->(sink:Endpoint {role: 'video-sink'})
WITH v, d, src, sink, [(v)-[:PROVIDES]->(i:Item) | i.id] + $bag + [$laptop] AS have
MATCH p = (src)-[:VIDEO]->()
  (()-[mt:MATES WHERE mt.from_item IN have AND mt.to_item IN have]->()
     -[vv:VIDEO WHERE vv.item IN have]->()){1,6}
  (sink)
// a physical item can only be used once in a chain
WHERE all(k IN range(0, size(nodes(p)) - 2) WHERE NOT nodes(p)[k] IN nodes(p)[k + 1..])
WITH v, d, sink, p, [r IN relationships(p) WHERE type(r) = 'VIDEO'] AS links
WITH v, d, sink, p, links,
     reduce(lo = 1.0e9, r IN links | CASE WHEN r.gbps < lo THEN r.gbps ELSE lo END) AS bottleneck
// the same items can connect through different ports or cable orientations: keep one row per item chain
WITH sink, [r IN links | r.item] AS chain, bottleneck, [r IN links WHERE r.gbps = bottleneck][0] AS weak
ORDER BY bottleneck DESC
WITH sink, chain, collect({bottleneck: bottleneck, weak: weak})[0] AS best
OPTIONAL MATCH (sink)-[:SUPPORTS_MODE]->(m:Mode) WHERE m.gbps <= best.bottleneck
WITH chain, best, m ORDER BY m.rank DESC
WITH chain, best, collect(m.id) AS modes
RETURN chain,
       best.bottleneck AS bottleneck_gbps,
       best.weak.item AS weakest_item, best.weak.standard AS weakest_standard,
       best.weak.confidence AS weakest_confidence, best.weak.source_url AS weakest_source,
       modes[0] AS best_mode
ORDER BY bottleneck_gbps DESC, size(chain) ASC
