// Ingest (or re-ingest) a venue described in an email, a booking page or a tech-rider PDF.
// ONE write statement, so it can be sent as-is through MCP `write_cypher`.
// Param $v (see agent/schemas/venue.schema.json):
//   {id, name, description, confidence, source: {id, kind, publisher, title, url, supports},
//    display: {name, max_mode, inputs: [{connector, standard, confidence, note}]},
//    provides: [catalog Item.id]}
// It refuses to overwrite a catalog venue: if $v.id names a venue that was not ingested, it
// writes nothing (MCP write_cypher then reports nodes_created = 0).
// The display becomes Item `<id>-display` with an input Port per input, a panel Endpoint,
// VIDEO edges at the input standard's data rate, MATES to every compatible plug in the graph,
// and SUPPORTS_MODE up to max_mode. Every new edge carries the source and confidence.
OPTIONAL MATCH (clash:Venue {id: $v.id})
WITH clash WHERE clash IS NULL OR clash.ingested = true
CALL () {
  OPTIONAL MATCH (n) WHERE n.id = $v.id + '-display' OR n.item = $v.id + '-display'
  DETACH DELETE n
}
CALL () {
  OPTIONAL MATCH (old:Venue {id: $v.id})
  DETACH DELETE old
}
MERGE (src:Source {id: $v.source.id})
SET src.kind = coalesce($v.source.kind, 'email'), src.publisher = $v.source.publisher,
    src.title = $v.source.title, src.url = $v.source.url, src.supports = $v.source.supports,
    src.ingested = true
CREATE (ven:Venue {id: $v.id, name: $v.name, description: $v.description,
                   source: $v.source.id, confidence: $v.confidence, ingested: true})
CREATE (d:Item {id: $v.id + '-display', kind: 'display', class: 'ingested', name: $v.display.name,
                purchasable: false, license: 'user', confidence: $v.confidence, ingested: true})
CREATE (e:Endpoint {id: $v.id + '-display:panel', item: $v.id + '-display', name: 'panel', role: 'video-sink'})
CREATE (d)-[:HAS_ENDPOINT]->(e), (ven)-[:PROVIDES]->(d), (d)-[:CITES]->(src)
WITH ven, d, e, src
CALL (d, e, src) {
  UNWIND range(0, size($v.display.inputs) - 1) AS k
  WITH d, e, src, k, $v.display.inputs[k] AS inp
  MATCH (s:Standard {id: inp.standard})
  CREATE (p:Port {id: d.id + ':in' + toString(k + 1), item: d.id, name: toLower(inp.connector) + toString(k + 1),
                  connector: inp.connector, gender: 'receptacle', dual_mode: false, requires_dual_mode: false})
  CREATE (d)-[:HAS_PORT]->(p)
  CREATE (p)-[:VIDEO {item: d.id, from_item: d.id, to_item: d.id, gbps: s.data_gbps, standard: s.id,
                      source: src.id, source_url: src.url, confidence: coalesce(inp.confidence, $v.confidence),
                      note: coalesce(inp.note, 'From ' + coalesce(src.title, src.id))}]->(e)
  MERGE (d)-[:CONFORMS_TO]->(s)
  WITH d, p, d.id AS did, p.connector AS c
  MATCH (q:Port {gender: 'plug', connector: c})
  WHERE q.item <> did AND NOT q.requires_dual_mode
  WITH p, q, did, c, q.item AS qi
  CREATE (p)-[:MATES {from_item: did, to_item: qi, connector: c}]->(q)
  CREATE (q)-[:MATES {from_item: qi, to_item: did, connector: c}]->(p)
  RETURN count(*) AS mates
}
CALL (e) {
  MATCH (top:Mode {id: $v.display.max_mode}), (m:Mode) WHERE m.rank <= top.rank
  CREATE (e)-[:SUPPORTS_MODE]->(m)
  RETURN count(m) AS modes
}
CALL (ven) {
  UNWIND coalesce($v.provides, []) AS pid
  MATCH (i:Item {id: pid})
  CREATE (ven)-[:PROVIDES]->(i)
  RETURN count(i) AS provided
}
RETURN ven.id AS venue, d.id AS display, modes, provided
