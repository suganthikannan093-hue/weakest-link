// Loads data/build/graph.json (bound as $g) into a Relate store.
// Same script runs in the CLI (scripts/build_store.py) and in the browser (relate-wasm executeScript).
CREATE INDEX item_id IF NOT EXISTS FOR (n:Item) ON (n.id);
CREATE INDEX port_id IF NOT EXISTS FOR (n:Port) ON (n.id);
CREATE INDEX endpoint_id IF NOT EXISTS FOR (n:Endpoint) ON (n.id);
CREATE INDEX mode_id IF NOT EXISTS FOR (n:Mode) ON (n.id);
CREATE INDEX venue_id IF NOT EXISTS FOR (n:Venue) ON (n.id);
UNWIND $g.sources AS r CREATE (n:Source) SET n = r;
UNWIND $g.standards AS r CREATE (n:Standard) SET n = r;
UNWIND $g.modes AS r CREATE (n:Mode) SET n = r;
UNWIND $g.items AS r CREATE (n:Item) SET n = r;
UNWIND $g.ports AS r CREATE (n:Port) SET n = r;
UNWIND $g.endpoints AS r CREATE (n:Endpoint) SET n = r;
UNWIND $g.venues AS r CREATE (n:Venue) SET n = r;
UNWIND $g.has_port AS r MATCH (i:Item {id: r.item}), (p:Port {id: r.port}) CREATE (i)-[:HAS_PORT]->(p);
UNWIND $g.has_endpoint AS r MATCH (i:Item {id: r.item}), (e:Endpoint {id: r.endpoint}) CREATE (i)-[:HAS_ENDPOINT]->(e);
UNWIND $g.video AS r MATCH (a) WHERE a.id = r.from AND (a:Port OR a:Endpoint) MATCH (b) WHERE b.id = r.to AND (b:Port OR b:Endpoint) CREATE (a)-[x:VIDEO]->(b) SET x = r.props;
UNWIND $g.power AS r MATCH (a) WHERE a.id = r.from AND (a:Port OR a:Endpoint) MATCH (b) WHERE b.id = r.to AND (b:Port OR b:Endpoint) CREATE (a)-[x:POWER]->(b) SET x = r.props;
UNWIND $g.mates AS r MATCH (a:Port {id: r.from}), (b:Port {id: r.to}) CREATE (a)-[x:MATES]->(b) SET x = r.props;
UNWIND $g.supports_mode AS r MATCH (e:Endpoint {id: r.endpoint}), (m:Mode {id: r.mode}) CREATE (e)-[:SUPPORTS_MODE]->(m);
UNWIND $g.provides AS r MATCH (v:Venue {id: r.venue}), (i:Item {id: r.item}) CREATE (v)-[:PROVIDES]->(i);
UNWIND $g.conforms_to AS r MATCH (i:Item {id: r.item}), (s:Standard {id: r.standard}) CREATE (i)-[:CONFORMS_TO]->(s);
UNWIND $g.cites AS r MATCH (i:Item {id: r.item}), (s:Source {id: r.source}) CREATE (i)-[:CITES]->(s);
