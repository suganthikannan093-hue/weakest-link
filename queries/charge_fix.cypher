// Q5 best purchase for charging: which ONE purchasable item (or, if the bag has no power source
// at all, which charger + cable pair) gets the most power into $laptop's battery? Ranked by the
// verdict it reaches (fast-charge > full-speed > below-recommended), then a cable, a charger, a
// charger + cable pair, and a dock last, then the smallest wattage that does the job (usually the
// cheapest). Only purchases that beat what the bag delivers today are returned.
// Params: $laptop, $bag, $strict (true = ignore low-confidence links)
// Written without CALL subqueries so that Relate's MCP read_cypher tool accepts it.
MATCH (lap:Item {id: $laptop})-[:HAS_ENDPOINT]->(bat:Endpoint {role: 'power-sink'})
WITH lap, bat, $bag + [$laptop] AS have
OPTIONAL MATCH p = (psu:Endpoint {role: 'power-source'})-[p0:POWER WHERE NOT $strict OR p0.confidence <> 'low']->()
  (()-[mt:MATES WHERE mt.from_item IN have AND mt.to_item IN have]->()
     -[pw:POWER WHERE pw.item IN have AND (NOT $strict OR pw.confidence <> 'low')]->()){1,4}
  (bat)
WHERE psu.item IN have AND all(k IN range(0, size(nodes(p)) - 2) WHERE NOT nodes(p)[k] IN nodes(p)[k + 1..])
WITH lap, bat, have, p,
     reduce(lo = 1.0e9, r IN [x IN relationships(p) WHERE type(x) = 'POWER'] | CASE WHEN r.watts IS NOT NULL AND r.watts < lo THEN r.watts ELSE lo END) AS w
WITH lap, bat, have, max(CASE WHEN p IS NULL THEN null ELSE w END) AS now_w
OPTIONAL MATCH (src:Item)-[:HAS_ENDPOINT]->(:Endpoint {role: 'power-source'}) WHERE src.id IN have
WITH lap, bat, have, now_w, count(src) > 0 AS has_source
MATCH (c:Item {purchasable: true}) WHERE NOT c.id IN have AND c.kind IN ['cable', 'charger', 'adapter']
WITH lap, bat, have, now_w, has_source, collect(c) AS cands
UNWIND cands AS c1
UNWIND [null] + [x IN cands WHERE NOT has_source AND c1.kind = 'charger' AND x.kind = 'cable'] AS c2
WITH lap, bat, have, now_w, c1, c2, [c1.id] + CASE WHEN c2 IS NULL THEN [] ELSE [c2.id] END AS buy
WITH lap, bat, now_w, c1, c2, buy, have + buy AS have2
OPTIONAL MATCH p = (psu:Endpoint {role: 'power-source'})-[p0:POWER WHERE NOT $strict OR p0.confidence <> 'low']->()
  (()-[mt:MATES WHERE mt.from_item IN have2 AND mt.to_item IN have2]->()
     -[pw:POWER WHERE pw.item IN have2 AND (NOT $strict OR pw.confidence <> 'low')]->()){1,4}
  (bat)
WHERE psu.item IN have2 AND all(k IN range(0, size(nodes(p)) - 2) WHERE NOT nodes(p)[k] IN nodes(p)[k + 1..])
WITH lap, now_w, c1, c2, buy, p,
     reduce(lo = 1.0e9, r IN [x IN relationships(p) WHERE type(x) = 'POWER'] | CASE WHEN r.watts IS NOT NULL AND r.watts < lo THEN r.watts ELSE lo END) AS w
WITH lap, now_w, c1, c2, buy, max(CASE WHEN p IS NULL THEN null ELSE w END) AS new_w
WHERE new_w IS NOT NULL AND (now_w IS NULL OR new_w > now_w)
WITH lap, now_w, c1, c2, buy, new_w,
     CASE WHEN lap.pd_fast_w IS NOT NULL AND new_w >= lap.pd_fast_w THEN 'fast-charge'
          WHEN lap.pd_recommended_w IS NOT NULL AND new_w >= lap.pd_recommended_w THEN 'full-speed'
          WHEN lap.pd_recommended_w IS NULL THEN 'unknown'
          ELSE 'below-recommended' END AS verdict,
     CASE WHEN now_w IS NULL THEN 'none'
          WHEN lap.pd_fast_w IS NOT NULL AND now_w >= lap.pd_fast_w THEN 'fast-charge'
          WHEN lap.pd_recommended_w IS NOT NULL AND now_w >= lap.pd_recommended_w THEN 'full-speed'
          WHEN lap.pd_recommended_w IS NULL THEN 'unknown'
          ELSE 'below-recommended' END AS verdict_now
WITH buy, c1, c2, new_w, now_w, verdict, verdict_now,
     {`fast-charge`: 3, `full-speed`: 2, unknown: 1, `below-recommended`: 1, none: 0} AS rank
WHERE rank[verdict] > rank[verdict_now] OR (verdict = 'unknown' AND verdict_now IN ['unknown', 'none'])
     OR (verdict = verdict_now AND verdict <> 'fast-charge')
WITH buy, c1, c2, new_w, now_w, verdict, verdict_now, rank,
     CASE WHEN c2 IS NOT NULL THEN c2 WHEN c1.kind = 'cable' THEN c1 ELSE null END AS cab
RETURN buy, [c1.name] + CASE WHEN c2 IS NULL THEN [] ELSE [c2.name] END AS names,
       new_w AS capacity_w, now_w AS capacity_now_w, verdict, verdict_now
// ties: the plainest cable that does the job (least video, lowest rating, not Thunderbolt/USB4), generic before branded
ORDER BY rank[verdict] DESC,
         CASE WHEN c2 IS NOT NULL THEN 2 WHEN c1.kind = 'cable' THEN 0 WHEN c1.kind = 'charger' THEN 1 ELSE 3 END,
         new_w ASC,
         CASE WHEN cab IS NULL THEN 0 ELSE reduce(hi = 0.0, x IN [(cab)-[:HAS_PORT]->()-[v:VIDEO]->() | v.gbps] | CASE WHEN x > hi THEN x ELSE hi END) END,
         CASE WHEN cab IS NULL THEN 0 ELSE reduce(hi = 0, x IN [(cab)-[:HAS_PORT]->()-[r:POWER]->() | r.watts] | CASE WHEN x > hi THEN x ELSE hi END) END,
         CASE WHEN cab IS NOT NULL AND (cab.name CONTAINS 'Thunderbolt' OR cab.name CONTAINS 'USB4') THEN 1 ELSE 0 END,
         CASE WHEN c1.class = 'generic' THEN 0 ELSE 1 END,
         CASE WHEN cab IS NULL OR cab.class = 'generic' THEN 0 ELSE 1 END, buy
