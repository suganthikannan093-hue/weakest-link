// Browser-engine parity: load the same graph into @relate/relate-wasm (in memory, as the web UI
// will) with the same import script, run the same query files, and compare with the relate CLI
// running on the committed .rl store.
//   node tests/wasm_parity.mjs
import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import init, { RelateDb } from '@relate/relate-wasm';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const wasm = fs.readFileSync(path.join(root, 'node_modules/@relate/relate-wasm/relate_bg.wasm'));
await init({ module_or_path: wasm });

const db = new RelateDb();
const graph = fs.readFileSync(path.join(root, 'data/build/graph.json'), 'utf8');
const script = fs.readFileSync(path.join(root, 'scripts/import.cypher'), 'utf8');
for (const env of db.executeScript(script, JSON.stringify({ g: JSON.parse(graph) }))) {
  const r = JSON.parse(env);
  if (r.error) throw new Error('import failed: ' + r.error);
}

const scenarios = [
  ['reach', { laptop: 'mba-m2', venue: 'meetup-hall', bag: ['adp-apple-av-a1621'], mode: '1080p60' }],
  ['reach', { laptop: 'mba-m2', venue: 'meetup-hall', bag: ['adp-apple-av-a1621'], mode: '4K60' }],
  ['chains', { laptop: 'mba-m2', venue: 'meetup-hall', bag: ['adp-apple-av-a1621', 'hub-usbc-4k30', 'cable-usbc-hdmi-4k60'] }],
  ['best_fix', { laptop: 'mba-m2', bag: ['adp-apple-av-a1621'], mode: '1080p60',
                 venues: ['meetup-hall', 'college-seminar', 'hotel-ballroom', 'coworking-room', 'conference-booth', 'studio-tv'] }],
  ['power', { laptop: 'mbp14-m3', bag: ['chg-apple-140w', 'cable-usbc-usb2-60w', 'chg-apple-96w', 'cable-usbc-magsafe3'] }],
  ['chains', { laptop: 'ideapad-slim3-15iru8', venue: 'meetup-hall', bag: ['adp-usbc-hdmi-4k60', 'hub-anker-341'] }],
  ['reach', { laptop: 'ipad-10', venue: 'conference-booth', bag: ['cable-usbc-dp14'], mode: '4K60' }],
  ['best_fix', { laptop: 'iphone-15', bag: [], mode: '1080p60', venues: ['meeting-room', 'school-classroom', 'hot-desk', 'meetup-hall'] }],
  ['power', { laptop: 'mba-m2', bag: ['mon-lg-27up850', 'cable-usbc-10g-100w', 'dock-caldigit-ts4'] }],
  ['charge_fix', { laptop: 'mbp14-m3', bag: ['chg-apple-140w', 'cable-usbc-usb2-60w'] }],
  ['charge_fix', { laptop: 'iphone-15', bag: [] }],
  ['reach', { laptop: 'iphone-15', venue: 'meetup-hall', bag: ['adp-apple-av-a2119'], mode: '1080p60', strict: true }],
  ['chains', { laptop: 'gen-laptop-budget', venue: 'college-seminar', bag: ['adp-hdmi-vga'], strict: true }],
];
// every query takes $strict; default false like the UI and the CLI wrapper
for (const s of scenarios) if (!('strict' in s[1])) s[1].strict = false;

const canon = (rows) => JSON.stringify(rows.map((r) => Object.fromEntries(Object.entries(r).sort())));
let failed = 0;
for (const [name, params] of scenarios) {
  const cypher = fs.readFileSync(path.join(root, 'queries', `${name}.cypher`), 'utf8');
  const w = JSON.parse(db.execute(cypher, JSON.stringify(params)));
  if (w.error) throw new Error(`${name} (wasm): ${w.error}`);
  const args = ['--database', path.join(root, 'data/weakest-link.rl'), '--read-only', '--json', '--no-agent-mode', '--max-rows', '0'];
  for (const [k, v] of Object.entries(params)) args.push('--param', `${k}=${JSON.stringify(v)}`);
  args.push('query');
  const cli = JSON.parse(execFileSync('relate', args, { input: cypher, encoding: 'utf8' })).data;
  const same = canon(w.rows) === canon(cli);
  console.log(`${same ? 'ok  ' : 'FAIL'} ${name} ${JSON.stringify(params)} -> ${w.rows.length} rows`);
  if (!same) { failed++; console.log(' wasm:', canon(w.rows), '\n cli: ', canon(cli)); }
}
if (failed) { console.error(`${failed} parity failure(s)`); process.exit(1); }
console.log('wasm and CLI agree on all scenarios');
