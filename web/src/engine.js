// Thin wrapper around @relate/relate-wasm: loads the committed graph (data/build/graph.json,
// built from the same cited sources as data/weakest-link.rl) with the same import script the
// CLI uses, and runs the same query files the CLI tests run.
import init, { RelateDb } from '@relate/relate-wasm';
import wasmUrl from '@relate/relate-wasm/relate_bg.wasm?url';
import graphUrl from '../../data/build/graph.json?url';
import importScript from '../../scripts/import.cypher?raw';
import reachQ from '../../queries/reach.cypher?raw';
import chainsQ from '../../queries/chains.cypher?raw';
import bestFixQ from '../../queries/best_fix.cypher?raw';
import powerQ from '../../queries/power.cypher?raw';
import chargeFixQ from '../../queries/charge_fix.cypher?raw';

export const QUERIES = { reach: reachQ, chains: chainsQ, best_fix: bestFixQ, power: powerQ, charge_fix: chargeFixQ };

let db = null;

export async function loadEngine() {
  const t0 = performance.now();
  const [, graph] = await Promise.all([
    init({ module_or_path: wasmUrl }),
    fetch(graphUrl).then((r) => {
      if (!r.ok) throw new Error(`could not load graph (${r.status})`);
      return r.json();
    }),
  ]);
  db = new RelateDb();
  for (const env of db.executeScript(importScript, JSON.stringify({ g: graph }))) {
    const r = JSON.parse(env);
    if (r.error) throw new Error(`graph import failed: ${r.error}`);
  }
  const counts = run('MATCH (n) WITH count(n) AS nodes MATCH ()-[r]->() RETURN nodes, count(r) AS rels')[0];
  return { ms: Math.round(performance.now() - t0), ...counts };
}

export function run(cypher, params = {}) {
  const r = JSON.parse(db.execute(cypher, JSON.stringify(params)));
  if (r.error) throw new Error(r.error);
  return r.rows;
}

export function query(name, params) {
  const t0 = performance.now();
  const rows = run(QUERIES[name], { strict: false, ...params });
  return { rows, ms: performance.now() - t0 };
}

export function catalog() {
  return {
    items: run(`MATCH (i:Item)
      OPTIONAL MATCH (i)-[:HAS_PORT]->(p:Port)
      WITH i, collect(DISTINCT p.connector) AS connectors
      OPTIONAL MATCH (i)-[:HAS_ENDPOINT]->(ps:Endpoint {role: 'power-source'})
      WITH i, connectors, count(ps) > 0 AS power_source
      OPTIONAL MATCH (i)-[:HAS_ENDPOINT]->(bat:Endpoint {role: 'power-sink'})<-[pw:POWER]-()
      WITH i, connectors, power_source, count(pw) > 0 AS charges
      RETURN i.id AS id, i.name AS name, i.kind AS kind, i.class AS class, i.maker AS maker,
             i.purchasable AS purchasable, i.pd_recommended_w AS pd_recommended_w, i.pd_fast_w AS pd_fast_w,
             connectors, power_source, charges ORDER BY i.kind, i.name`),
    venues: run(`MATCH (v:Venue)
      OPTIONAL MATCH (v)-[:PROVIDES]->(i:Item)
      WITH v, collect(i.id) AS provides
      RETURN v.id AS id, v.name AS name, v.description AS description, provides ORDER BY v.name`),
    modes: run('MATCH (m:Mode) RETURN m.id AS id, m.gbps AS gbps, m.rank AS rank ORDER BY m.rank'),
    panelModes: run(`MATCH (v:Venue)-[:PROVIDES]->(:Item {kind: 'display'})-[:HAS_ENDPOINT]->(:Endpoint)-[:SUPPORTS_MODE]->(m:Mode)
      WITH v, m ORDER BY m.rank DESC
      RETURN v.id AS venue, collect(m.id)[0] AS max_mode`),
    standards: run(`MATCH (s:Standard) WHERE s.data_gbps IS NOT NULL
      RETURN s.id AS id, s.family AS family, s.data_gbps AS gbps ORDER BY s.family, s.data_gbps`),
  };
}

// A user-described display is written into the in-browser graph as a real Item/Port/Endpoint
// subgraph (the browser counterpart of the agent's write_cypher), so every query treats it like
// catalog equipment.
const CUSTOM_SCRIPT = `
MATCH (n) WHERE n.id = 'custom' OR n.id STARTS WITH 'custom-display' DETACH DELETE n;
CREATE (i:Item {id: 'custom-display', kind: 'display', class: 'user', name: $name, purchasable: false, license: 'user'})
CREATE (e:Endpoint {id: 'custom-display:panel', item: 'custom-display', name: 'panel', role: 'video-sink'})
CREATE (i)-[:HAS_ENDPOINT]->(e);
UNWIND $inputs AS inp
MATCH (i:Item {id: 'custom-display'}), (e:Endpoint {id: 'custom-display:panel'}), (s:Standard {id: inp.standard})
CREATE (p:Port {id: 'custom-display:' + inp.id, item: 'custom-display', name: inp.id, connector: inp.connector,
                gender: 'receptacle', dual_mode: false, requires_dual_mode: false})
CREATE (i)-[:HAS_PORT]->(p)
CREATE (p)-[:VIDEO {item: 'custom-display', from_item: 'custom-display', to_item: 'custom-display',
                    gbps: s.data_gbps, standard: s.id, source: 'user', confidence: 'user'}]->(e);
MATCH (p:Port {item: 'custom-display'}), (q:Port {gender: 'plug'})
WHERE q.connector = p.connector AND NOT q.requires_dual_mode
CREATE (p)-[:MATES {from_item: 'custom-display', to_item: q.item, connector: p.connector}]->(q),
       (q)-[:MATES {from_item: q.item, to_item: 'custom-display', connector: p.connector}]->(p);
MATCH (e:Endpoint {id: 'custom-display:panel'}), (m:Mode) WHERE m.rank <= $maxRank
CREATE (e)-[:SUPPORTS_MODE]->(m);
CREATE (v:Venue {id: 'custom', name: $venueName, description: $description});
MATCH (v:Venue {id: 'custom'}), (i:Item) WHERE i.id IN $provides
CREATE (v)-[:PROVIDES]->(i);
`;

export function setCustomDisplay({ name, inputs, maxRank, cable }) {
  const provides = ['custom-display', ...(cable ? [cable] : [])];
  const params = {
    name: name || 'My display',
    venueName: 'Custom: ' + (name || 'My display'),
    description: 'A display you described.',
    inputs, maxRank, provides,
  };
  for (const env of db.executeScript(CUSTOM_SCRIPT, JSON.stringify(params))) {
    const r = JSON.parse(env);
    if (r.error) throw new Error(`custom display: ${r.error}`);
  }
}
