// Q4 USB-PD charging chain: for every charger in $bag, the best way to reach $laptop's battery
// using cables in $bag, the delivered wattage (min over the chain), the weakest link, and a verdict
// against the laptop's documented recommended / fast-charge wattage. capacity_w is what the chain
// can carry; the laptop itself draws only what it needs.
// Params: $laptop, $bag
MATCH (lap:Item {id: $laptop})-[:HAS_ENDPOINT]->(bat:Endpoint {role: 'power-sink'})
MATCH (chg:Item {kind: 'charger'})-[:HAS_ENDPOINT]->(psu:Endpoint {role: 'power-source'})
WHERE chg.id IN $bag
WITH lap, bat, chg, psu, $bag + [$laptop] AS have
MATCH p = (psu)-[:POWER]->()
  (()-[mt:MATES WHERE mt.from_item IN have AND mt.to_item IN have]->()
     -[pw:POWER WHERE pw.item IN have]->()){1,4}
  (bat)
WHERE all(k IN range(0, size(nodes(p)) - 2) WHERE NOT nodes(p)[k] IN nodes(p)[k + 1..])
WITH lap, chg, [r IN relationships(p) WHERE type(r) = 'POWER'] AS links
WITH lap, chg, links,
     reduce(lo = 1.0e9, r IN links | CASE WHEN r.watts IS NOT NULL AND r.watts < lo THEN r.watts ELSE lo END) AS watts
WITH lap, chg, [r IN links | r.item] AS chain, watts,
     [r IN links WHERE r.watts = watts][0] AS weak
ORDER BY watts DESC, size(chain) ASC
WITH lap, chg, collect({chain: chain, watts: watts, weak: weak})[0] AS best
RETURN chg.id AS charger, best.chain AS chain, best.watts AS capacity_w,
       best.weak.item AS weakest_item, best.weak.source_url AS weakest_source,
       lap.pd_recommended_w AS recommended_w, lap.pd_fast_w AS fast_w,
       CASE
         WHEN lap.pd_fast_w IS NOT NULL AND best.watts >= lap.pd_fast_w THEN 'fast-charge'
         WHEN lap.pd_recommended_w IS NOT NULL AND best.watts >= lap.pd_recommended_w THEN 'full-speed'
         WHEN lap.pd_recommended_w IS NULL THEN 'unknown'
         ELSE 'below-recommended'
       END AS verdict
ORDER BY capacity_w DESC
