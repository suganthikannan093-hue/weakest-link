// Ingest (or re-ingest) an adapter, hub, cable or charger from its spec page.
// ONE write statement, so it can be sent as-is through MCP `write_cypher`.
// Param $it (see agent/schemas/item.schema.json):
//   {id, name, kind, maker, purchasable, confidence, source: {id, kind, publisher, title, url, supports},
//    ports: [{name, connector, gender, dual_mode, requires_dual_mode}],
//    endpoints: [{name, role}],                       // chargers only: {name:'psu', role:'power-source'}
//    video: [{from, to, standard, gbps, note, both_ways}],
//    power: [{from, to, standard, watts, note, both_ways}]}
// `from`/`to` are port or endpoint names. gbps defaults to the standard's data rate and watts to the
// standard's wattage, so a spec that only says "HDMI 2.0" still gets a cited number.
// It refuses to overwrite a catalog item: if $it.id names an item that was not ingested, it writes
// nothing (MCP write_cypher then reports nodes_created = 0). Use ids that start with `my-`.
OPTIONAL MATCH (clash:Item {id: $it.id})
WITH clash WHERE clash IS NULL OR clash.ingested = true
CALL () {
  OPTIONAL MATCH (n) WHERE n.id = $it.id OR n.item = $it.id
  DETACH DELETE n
}
MERGE (src:Source {id: $it.source.id})
SET src.kind = coalesce($it.source.kind, 'manufacturer'), src.publisher = $it.source.publisher,
    src.title = $it.source.title, src.url = $it.source.url, src.supports = $it.source.supports,
    src.ingested = true
CREATE (i:Item {id: $it.id, kind: $it.kind, class: 'ingested', name: $it.name, maker: $it.maker,
                purchasable: coalesce($it.purchasable, true), license: 'user',
                confidence: $it.confidence, ingested: true})
CREATE (i)-[:CITES]->(src)
WITH i, src
CALL (i) {
  UNWIND coalesce($it.ports, []) AS pt
  WITH i, pt, i.id AS iid
  CREATE (p:Port {id: iid + ':' + pt.name, item: iid, name: pt.name, connector: pt.connector,
                  gender: pt.gender, dual_mode: coalesce(pt.dual_mode, false),
                  requires_dual_mode: coalesce(pt.requires_dual_mode, false)})
  CREATE (i)-[:HAS_PORT]->(p)
  RETURN count(p) AS ports
}
CALL (i) {
  UNWIND coalesce($it.endpoints, []) AS ep
  WITH i, ep, i.id AS iid
  CREATE (e:Endpoint {id: iid + ':' + ep.name, item: iid, name: ep.name, role: ep.role})
  CREATE (i)-[:HAS_ENDPOINT]->(e)
  RETURN count(e) AS endpoints
}
CALL (i, src) {
  UNWIND coalesce($it.video, []) AS vd
  UNWIND CASE WHEN coalesce(vd.both_ways, false) THEN [[vd.from, vd.to], [vd.to, vd.from]] ELSE [[vd.from, vd.to]] END AS dir
  MATCH (s:Standard {id: vd.standard})
  MATCH (a) WHERE a.id = i.id + ':' + dir[0] AND (a:Port OR a:Endpoint)
  MATCH (b) WHERE b.id = i.id + ':' + dir[1] AND (b:Port OR b:Endpoint)
  CREATE (a)-[:VIDEO {item: i.id, from_item: i.id, to_item: i.id, gbps: coalesce(vd.gbps, s.data_gbps),
                      standard: s.id, source: src.id, source_url: src.url, confidence: $it.confidence,
                      note: vd.note}]->(b)
  MERGE (i)-[:CONFORMS_TO]->(s)
  RETURN count(*) AS video
}
CALL (i, src) {
  UNWIND coalesce($it.power, []) AS pw
  UNWIND CASE WHEN coalesce(pw.both_ways, false) THEN [[pw.from, pw.to], [pw.to, pw.from]] ELSE [[pw.from, pw.to]] END AS dir
  MATCH (s:Standard {id: pw.standard})
  MATCH (a) WHERE a.id = i.id + ':' + dir[0] AND (a:Port OR a:Endpoint)
  MATCH (b) WHERE b.id = i.id + ':' + dir[1] AND (b:Port OR b:Endpoint)
  CREATE (a)-[:POWER {item: i.id, from_item: i.id, to_item: i.id, watts: coalesce(pw.watts, s.watts),
                      standard: s.id, source: src.id, source_url: src.url, confidence: $it.confidence,
                      note: pw.note}]->(b)
  MERGE (i)-[:CONFORMS_TO]->(s)
  RETURN count(*) AS power
}
CALL (i) {
  MATCH (i)-[:HAS_PORT]->(p:Port), (q:Port)
  WHERE q.item <> i.id AND q.connector = p.connector AND q.gender <> p.gender
    AND NOT (p.gender = 'plug' AND p.requires_dual_mode AND NOT q.dual_mode)
    AND NOT (q.gender = 'plug' AND q.requires_dual_mode AND NOT p.dual_mode)
  WITH p, q, i.id AS iid, q.item AS qi, p.connector AS c
  CREATE (p)-[:MATES {from_item: iid, to_item: qi, connector: c}]->(q)
  CREATE (q)-[:MATES {from_item: qi, to_item: iid, connector: c}]->(p)
  RETURN count(*) AS mates
}
RETURN i.id AS item, ports, endpoints, video, power, mates
