import './style.css';
import { loadEngine, catalog, query, run, setCustomDisplay, QUERIES } from './engine.js';

// ---------- constants & helpers ----------
const MODE_LABEL = { '720p60': '720p · 60 Hz', '1080p60': '1080p · 60 Hz', '1440p60': '1440p · 60 Hz', '4K30': '4K · 30 Hz', '4K60': '4K · 60 Hz' };
const MODE_PHRASE = { '720p60': '720p at 60 Hz', '1080p60': '1080p (Full HD) at 60 Hz', '1440p60': '1440p at 60 Hz', '4K30': '4K at 30 Hz', '4K60': '4K at 60 Hz' };
const STD_LABEL = {
  'HDMI-Standard-cable': 'Standard HDMI (720p/1080i)', 'HDMI-1.4': 'HDMI 1.4', 'HDMI-2.0': 'HDMI 2.0', 'HDMI-2.1-FRL': 'HDMI 2.1',
  'DP-1.2-HBR2': 'DisplayPort 1.2', 'DP-1.4-HBR3': 'DisplayPort 1.4', 'DP-2.1-UHBR10': 'DisplayPort UHBR10',
  'DP-Alt-4L-HBR3': 'USB-C DisplayPort, 4 lanes', 'DP-Alt-2L-HBR3': 'USB-C DisplayPort, 2 lanes', 'VGA-1200p': 'VGA (analog)',
  'USB-PD-3A': 'USB PD 3 A', 'USB-PD-5A': 'USB PD 5 A', 'USB-PD-EPR': 'USB PD 240 W EPR',
};
const CONF_LABEL = { high: 'High confidence', medium: 'Medium confidence', low: 'Low confidence', user: 'You entered this' };
const CUSTOM_INPUTS = [
  { id: 'hdmi14', connector: 'HDMI', standard: 'HDMI-1.4', label: 'HDMI 1.4' },
  { id: 'hdmi20', connector: 'HDMI', standard: 'HDMI-2.0', label: 'HDMI 2.0' },
  { id: 'hdmi21', connector: 'HDMI', standard: 'HDMI-2.1-FRL', label: 'HDMI 2.1' },
  { id: 'dp12', connector: 'DP', standard: 'DP-1.2-HBR2', label: 'DisplayPort 1.2' },
  { id: 'dp14', connector: 'DP', standard: 'DP-1.4-HBR3', label: 'DisplayPort 1.4' },
  { id: 'usbc', connector: 'USB-C', standard: 'DP-Alt-4L-HBR3', label: 'USB-C (DisplayPort)' },
  { id: 'vga', connector: 'VGA', standard: 'VGA-1200p', label: 'VGA' },
];
const BAG_GROUPS = [['adapter', 'Adapters & hubs'], ['cable', 'Cables'], ['charger', 'Chargers']];
const ICON = {
  laptop: '<path d="M5 6h14v9H5z"/><path d="M2 18h20"/>',
  adapter: '<rect x="6" y="4" width="12" height="16" rx="3"/><path d="M10 8h4M10 16h4"/>',
  cable: '<path d="M4 7c6 0 4 10 10 10h6"/><rect x="2" y="5" width="4" height="4" rx="1"/><rect x="18" y="15" width="4" height="4" rx="1"/>',
  charger: '<rect x="6" y="6" width="12" height="14" rx="3"/><path d="M10 2v4M14 2v4M13 10l-3 4h4l-3 4"/>',
  display: '<rect x="3" y="4" width="18" height="12" rx="2"/><path d="M9 20h6M12 16v4"/>',
};
const EXAMPLES = [
  { label: 'Old Apple adapter + 4K TV', state: { laptop: 'mba-m2', bag: ['adp-apple-av-a1621', 'hub-usbc-4k30', 'chg-apple-70w', 'cable-usbc-usb2-60w'], venue: 'meetup-hall', mode: '4K60', tab: 'connect' } },
  { label: '240 W cable at a USB-C monitor', state: { laptop: 'mba-m2', bag: ['cable-usbc-usb2-240w', 'chg-apple-70w'], venue: 'conference-booth', mode: '4K60', tab: 'connect' } },
  { label: "Venue's old HDMI cable", state: { laptop: 'mbp14-m3', bag: [], venue: 'studio-tv', mode: '4K60', tab: 'connect' } },
  { label: 'One purchase, six venues', state: { laptop: 'mba-m2', bag: ['adp-apple-av-a1621'], venue: 'meetup-hall', mode: '4K60', tab: 'fix' } },
  { label: 'Big charger, thin cable', state: { laptop: 'mbp14-m3', bag: ['chg-apple-140w', 'cable-usbc-usb2-60w'], venue: 'meetup-hall', mode: '4K60', tab: 'power' } },
];

const $ = (sel) => document.querySelector(sel);
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const fmt = (n, d = 2) => (n == null ? '–' : Number(n).toLocaleString('en', { maximumFractionDigits: d }));
const icon = (kind, cls = 'icon') => `<svg class="${cls}" viewBox="0 0 24 24" aria-hidden="true">${ICON[kind] || ICON.adapter}</svg>`;

let CAT = null;
let ITEM = new Map();
let VENUE = new Map();
let MODE = new Map();

const state = {
  laptop: 'mba-m2', bag: new Set(EXAMPLES[0].state.bag), venue: 'meetup-hall', mode: '4K60', tab: 'connect',
  venues: null, // null = all venues (for best purchase)
  custom: { name: 'Venue projector', inputs: ['hdmi14', 'vga'], max: '1080p60', cable: '' },
};

const itemName = (id) => ITEM.get(id)?.name ?? id;
const shortName = (id) => {
  const n = itemName(id);
  return n.replace(/\s*\((?!model|older model)[^)]*\)\s*$/i, '').replace(/^Generic\s+/i, '');
};
const article = (s) => s;

// ---------- URL state ----------
function readHash() {
  const p = new URLSearchParams(location.hash.slice(1));
  if (p.has('l')) state.laptop = p.get('l');
  if (p.has('b')) state.bag = new Set(p.get('b').split(',').filter(Boolean));
  if (p.has('v')) state.venue = p.get('v');
  if (p.has('m')) state.mode = p.get('m');
  if (p.has('t')) state.tab = p.get('t');
  if (p.has('vs')) state.venues = new Set(p.get('vs').split(',').filter(Boolean));
  if (p.has('c')) {
    try { Object.assign(state.custom, JSON.parse(p.get('c'))); } catch { /* ignore */ }
  }
}
function writeHash() {
  const p = new URLSearchParams();
  p.set('l', state.laptop); p.set('b', [...state.bag].join(',')); p.set('v', state.venue); p.set('m', state.mode); p.set('t', state.tab);
  if (state.venues) p.set('vs', [...state.venues].join(','));
  if (state.venue === 'custom') p.set('c', JSON.stringify(state.custom));
  history.replaceState(null, '', '#' + p.toString());
}
function sanitizeState() {
  if (!ITEM.has(state.laptop) || ITEM.get(state.laptop).kind !== 'laptop') state.laptop = 'mba-m2';
  state.bag = new Set([...state.bag].filter((id) => ITEM.has(id) && ['adapter', 'cable', 'charger'].includes(ITEM.get(id).kind)));
  if (state.venue !== 'custom' && !VENUE.has(state.venue)) state.venue = 'meetup-hall';
  if (!MODE.has(state.mode)) state.mode = '4K60';
  if (!['connect', 'fix', 'power'].includes(state.tab)) state.tab = 'connect';
}

// ---------- controls ----------
function renderControls() {
  const laptops = CAT.items.filter((i) => i.kind === 'laptop');
  $('#laptop').innerHTML = laptops.map((i) => `<option value="${i.id}">${esc(i.name)}</option>`).join('');
  $('#laptop').value = state.laptop;

  $('#venue').innerHTML = CAT.venues.map((v) => `<option value="${v.id}">${esc(v.name)}</option>`).join('')
    + '<option value="custom">Describe a display…</option>';
  $('#venue').value = state.venue;

  $('#modes').innerHTML = CAT.modes.map((m) => `
    <label class="seg"><input type="radio" name="mode" value="${m.id}" ${m.id === state.mode ? 'checked' : ''} />
      <span>${esc(MODE_LABEL[m.id] || m.id)}</span></label>`).join('');

  $('#custom-inputs').innerHTML = CUSTOM_INPUTS.map((c) => `
    <label class="check"><input type="checkbox" value="${c.id}" ${state.custom.inputs.includes(c.id) ? 'checked' : ''} /> ${esc(c.label)}</label>`).join('');
  $('#custom-max').innerHTML = CAT.modes.map((m) => `<option value="${m.id}">${esc(MODE_PHRASE[m.id])}</option>`).join('');
  $('#custom-max').value = state.custom.max;
  $('#custom-name').value = state.custom.name;
  $('#custom-cable').innerHTML = '<option value="">None</option>' + CAT.items.filter((i) => i.kind === 'cable')
    .map((i) => `<option value="${i.id}">${esc(i.name)}</option>`).join('');
  $('#custom-cable').value = state.custom.cable;

  renderBag();
  renderSetupInfo();
}

function renderBag() {
  const q = $('#bag-search').value.trim().toLowerCase();
  $('#bag').innerHTML = BAG_GROUPS.map(([kind, title]) => {
    const items = CAT.items.filter((i) => i.kind === kind && (!q || i.name.toLowerCase().includes(q) || i.id.includes(q)));
    if (!items.length) return '';
    return `<div class="bag-group"><p class="sub-legend">${title}</p><div class="chips">${items.map((i) => `
      <label class="chip ${state.bag.has(i.id) ? 'on' : ''}">
        <input type="checkbox" value="${i.id}" ${state.bag.has(i.id) ? 'checked' : ''} />
        ${icon(kind, 'icon sm')}<span>${esc(i.name)}</span></label>`).join('')}</div></div>`;
  }).join('') || '<p class="hint">No items match.</p>';
  $('#bag-count').textContent = `(${state.bag.size} item${state.bag.size === 1 ? '' : 's'})`;
}

function renderSetupInfo() {
  const lap = ITEM.get(state.laptop);
  $('#laptop-ports').textContent = lap ? `Ports: ${lap.connectors.join(', ')}` : '';
  $('#custom').hidden = state.venue !== 'custom';
  if (state.venue === 'custom') {
    $('#venue-desc').textContent = 'Tell us what the venue has. It becomes a real node in the graph.';
  } else {
    const v = VENUE.get(state.venue);
    $('#venue-desc').innerHTML = `${esc(v.description)}<br><span class="provides">At the venue: ${v.provides.map((id) => esc(shortName(id))).join(' · ')}</span>`;
  }
  const venueName = state.venue === 'custom' ? state.custom.name : VENUE.get(state.venue)?.name;
  $('#setup-summary span').textContent = `${shortName(state.laptop)} · ${state.bag.size} in bag · ${venueName} · ${MODE_LABEL[state.mode]}`;
}

function applyCustom() {
  const inputs = CUSTOM_INPUTS.filter((c) => state.custom.inputs.includes(c.id))
    .map(({ id, connector, standard }) => ({ id, connector, standard }));
  setCustomDisplay({ name: state.custom.name, inputs, maxRank: MODE.get(state.custom.max)?.rank ?? 2, cable: state.custom.cable || null });
}

// ---------- chain diagram ----------
function hopOwner(id) {
  if (id === state.laptop) return 'Your laptop';
  const venueProvides = state.venue === 'custom' ? ['custom-display', state.custom.cable] : VENUE.get(state.venue)?.provides || [];
  if (state.bag.has(id) && !venueProvides.includes(id)) return 'In your bag';
  if (venueProvides.includes(id)) return 'At the venue';
  return 'In your bag';
}

function chainDiagram(hops, joints, { unit, need, weakest, owner = hopOwner }) {
  const val = (h) => (unit === 'W' ? h.watts : h.gbps);
  const max = Math.max(need || 0, ...hops.map((h) => val(h) || 0));
  const parts = [];
  hops.forEach((h, i) => {
    const v = val(h);
    const kind = ITEM.get(h.item)?.kind || (h.item.startsWith('custom') ? 'display' : 'adapter');
    const isWeak = h.item === weakest;
    const below = need != null && v != null && v < need;
    const pct = v == null ? 100 : Math.max(4, Math.min(100, (v / max) * 100));
    const needPct = need ? Math.min(100, (need / max) * 100) : null;
    const metric = v == null ? (unit === 'W' ? 'draws what it needs' : '') : `${fmt(v)} ${unit === 'W' ? 'W' : 'Gbps'}`;
    const std = h.standard ? STD_LABEL[h.standard] || h.standard : '';
    const src = h.source_url
      ? `<a class="src" href="${esc(h.source_url)}" target="_blank" rel="noopener">Source<span class="visually-hidden"> for ${esc(shortName(h.item))} (opens in new tab)</span> ↗</a>`
      : '<span class="src muted">Entered by you</span>';
    parts.push(`
      <li class="hop ${isWeak ? 'weak' : ''} ${below ? 'below' : ''}" data-item="${esc(h.item)}">
        ${isWeak ? '<span class="badge">Weakest link</span>' : ''}
        <div class="hop-head">${icon(kind)}<span class="owner">${owner(h.item)}</span></div>
        <p class="hop-name" title="${esc(itemName(h.item))}">${esc(itemName(h.item))}</p>
        <p class="hop-metric"><strong>${metric}</strong>${std ? ` <span class="std">${esc(std)}</span>` : ''}</p>
        ${v != null ? `<div class="meter" role="img" aria-label="${metric}${need ? ` of ${fmt(need)} needed` : ''}">
          <span class="fill" style="width:${pct}%"></span>${needPct != null ? `<span class="need" style="left:${needPct}%"></span>` : ''}</div>` : ''}
        ${below ? `<p class="hop-warn">Below the ${fmt(need)} ${unit === 'W' ? 'W' : 'Gbps'} needed</p>` : ''}
        <p class="hop-meta"><span class="conf ${esc(h.confidence)}">${esc(CONF_LABEL[h.confidence] || h.confidence)}</span> ${src}</p>
        ${h.note ? `<p class="hop-note">${esc(h.note)}</p>` : ''}
      </li>`);
    if (i < hops.length - 1) parts.push(`<li class="joint" aria-label="plugs in via ${esc(joints[i] || '')}"><span>${esc(joints[i] || '')}</span></li>`);
  });
  return `<ol class="chain" aria-label="Connection chain, ${hops.length} items">${parts.join('')}</ol>`;
}

function cypherDetails(runs) {
  return `<details class="cypher"><summary>Show the Cypher (${runs.map((r) => `${r.name} ${fmt(r.ms, 1)} ms`).join(', ')})</summary>
    ${runs.map((r) => `<p class="hint">${esc(r.name)}.cypher with params <code>${esc(JSON.stringify(r.params))}</code></p><pre><code>${esc(QUERIES[r.name])}</code></pre>`).join('')}
  </details>`;
}

function verdictCard(kind, title, body) {
  const sym = { ok: '✓', warn: '!', bad: '✕' }[kind];
  return `<div class="verdict ${kind}" data-verdict="${kind}"><span class="v-icon" aria-hidden="true">${sym}</span>
    <div><p class="v-title">${title}</p>${body ? `<p class="v-body">${body}</p>` : ''}</div></div>`;
}

const listNames = (ids) => ids.map((id) => `<strong>${esc(shortName(id))}</strong>`).join(' → ');

// ---------- Connect tab ----------
function renderConnect() {
  const venueIds = [state.venue];
  const bag = [...state.bag];
  const p1 = { laptop: state.laptop, venue: state.venue, bag, mode: state.mode };
  const p2 = { laptop: state.laptop, venue: state.venue, bag };
  const r = query('reach', p1); const c = query('chains', p2);
  const reach = r.rows[0]; const chains = c.rows;
  const runs = [{ name: 'reach', params: p1, ms: r.ms }, { name: 'chains', params: p2, ms: c.ms }];
  const mode = MODE.get(state.mode);
  const displayId = reach?.display;
  const display = shortName(displayId);
  const lap = shortName(state.laptop);
  const maxMode = run(`MATCH (:Item {id: $d})-[:HAS_ENDPOINT]->(:Endpoint)-[:SUPPORTS_MODE]->(m:Mode) RETURN m.id AS id ORDER BY m.rank DESC LIMIT 1`, { d: displayId })[0]?.id;

  let verdict; let diagram = ''; let fixHtml = '';
  const venueItems = state.venue === 'custom' ? ['custom-display', state.custom.cable].filter(Boolean) : VENUE.get(state.venue).provides;

  if (reach?.ok) {
    const head = Math.round((reach.bottleneck_gbps / mode.gbps - 1) * 100);
    const weakHop = reach.hops.find((h) => h.item === reach.weakest_item);
    verdict = verdictCard('ok', `Yes. Your ${esc(lap)} will show ${MODE_PHRASE[state.mode]} on the ${esc(display)}.`,
      `Connect ${listNames(reach.chain)}. The weakest link is the ${esc(shortName(reach.weakest_item))} at ${fmt(reach.bottleneck_gbps)} Gbps,
       against the ${fmt(mode.gbps)} Gbps that ${MODE_LABEL[state.mode]} needs (${head}% headroom).
       ${weakHop && weakHop.confidence !== 'high' ? `That link's figure is <em>${esc(CONF_LABEL[weakHop.confidence]).toLowerCase()}</em>, so check its source.` : ''}`);
    diagram = chainDiagram(reach.hops, reach.joints, { unit: 'Gbps', need: mode.gbps, weakest: reach.weakest_item });
  } else if (reach && !reach.panel_ok) {
    const best = chains[0];
    verdict = verdictCard('bad', `No. The ${esc(display)} can't show ${MODE_PHRASE[state.mode]} at all.`,
      `The best it can display is ${MODE_PHRASE[maxMode] || 'unknown'}. Pick that, or a different display.
       ${best?.best_mode ? `With your bag you would get ${MODE_PHRASE[best.best_mode]}.` : ''}`);
    if (best) diagram = chainDiagram(best.hops, best.joints, { unit: 'Gbps', need: mode.gbps, weakest: best.weakest_item });
  } else if (chains.length) {
    const best = chains[0];
    const weakAtVenue = venueItems.includes(best.weakest_item);
    verdict = verdictCard(best.best_mode ? 'warn' : 'bad',
      best.best_mode ? `Not at ${MODE_PHRASE[state.mode]}. You'll get ${MODE_PHRASE[best.best_mode]} instead.` : 'It connects, but the picture won\'t work at any mode we check.',
      `The weakest link is ${weakAtVenue ? 'the venue\'s own' : 'your'} <strong>${esc(shortName(best.weakest_item))}</strong>: ${fmt(best.bottleneck_gbps)} Gbps
       (${esc(STD_LABEL[best.weakest_standard] || best.weakest_standard)}). ${MODE_LABEL[state.mode]} needs ${fmt(mode.gbps)} Gbps.`);
    diagram = chainDiagram(best.hops, best.joints, { unit: 'Gbps', need: mode.gbps, weakest: best.weakest_item });
  } else {
    const dispConn = run(`MATCH (:Item {id: $d})-[:HAS_PORT]->(p:Port) RETURN collect(DISTINCT p.connector) AS c`, { d: displayId })[0]?.c || [];
    verdict = verdictCard('bad', 'No. Nothing in your bag connects your laptop to this display.',
      `Your ${esc(lap)} has ${esc(ITEM.get(state.laptop).connectors.filter((x) => x !== 'MagSafe3').join(' and '))}; the ${esc(display)} takes
       ${esc(dispConn.join(' or ') || 'nothing we know')}.${venueItems.length > 1 ? ` The venue provides ${venueItems.filter((i) => i !== displayId).map((i) => esc(shortName(i))).join(', ')}.` : ''}
       ${bag.some((id) => id.startsWith('cable-usbc-usb2')) ? ' USB 2.0 charge cables carry no video.' : ''}`);
  }

  if (reach && !reach.ok && reach.panel_ok) {
    const pf = { laptop: state.laptop, bag, venues: venueIds, mode: state.mode };
    const f = query('best_fix', pf); runs.push({ name: 'best_fix', params: pf, ms: f.ms });
    if (f.rows.length) {
      const [top, ...rest] = f.rows;
      fixHtml = `<div class="fix"><p class="eyebrow">One purchase fixes it</p>
        <p class="fix-main">${icon(ITEM.get(top.buy)?.kind)}<span><strong>${esc(top.name)}</strong></span>
          <button type="button" class="btn small" data-add="${esc(top.buy)}">Add to bag</button></p>
        ${rest.length ? `<p class="hint">Also works: ${rest.slice(0, 4).map((x) => esc(shortName(x.buy))).join(', ')}.</p>` : ''}</div>`;
    } else {
      fixHtml = `<div class="fix none"><p class="eyebrow">No single purchase fixes this</p>
        <p class="hint">The limit is at the venue. Ask for a different input or cable, or lower the target to ${MODE_PHRASE[chains[0]?.best_mode] || 'a lower mode'}.</p></div>`;
    }
  }

  const others = chains.slice(reach?.ok ? 0 : 1).filter((ch) => !(reach?.ok && JSON.stringify(ch.chain) === JSON.stringify(reach.chain)));
  const othersHtml = others.length ? `<details class="others"><summary>Other ways to connect with your bag (${others.length})</summary><ul>
      ${others.slice(0, 8).map((ch) => `<li>${listNames(ch.chain)} <span class="tag ${ch.best_mode && MODE.get(ch.best_mode).rank >= mode.rank ? 'ok' : 'warn'}">${esc(MODE_LABEL[ch.best_mode] || 'no picture')}</span>
        <span class="hint">weakest: ${esc(shortName(ch.weakest_item))}, ${fmt(ch.bottleneck_gbps)} Gbps</span></li>`).join('')}</ul></details>` : '';

  $('#panel-connect').innerHTML = verdict + diagram + fixHtml + othersHtml + cypherDetails(runs);
}

// ---------- Best purchase tab ----------
function renderFix() {
  const all = [...CAT.venues.map((v) => ({ id: v.id, name: v.name })), ...(state.venue === 'custom' ? [{ id: 'custom', name: state.custom.name + ' (custom)' }] : [])];
  const selected = all.filter((v) => !state.venues || state.venues.has(v.id)).map((v) => v.id);
  const bag = [...state.bag];
  const params = { laptop: state.laptop, bag, venues: selected, mode: state.mode };
  const f = selected.length ? query('best_fix', params) : { rows: [], ms: 0 };
  const name = (id) => all.find((v) => v.id === id)?.name || id;

  // which venues work today (also gives the "already OK" list when no purchase helps)
  const today = selected.map((id) => ({ id, ...query('reach', { laptop: state.laptop, venue: id, bag, mode: state.mode }).rows[0] }));
  const okToday = today.filter((t) => t.ok);
  const failing = today.filter((t) => !t.ok);

  let body;
  if (!selected.length) body = '<p class="hint">Pick at least one venue.</p>';
  else if (!failing.length) body = verdictCard('ok', `Nothing to buy. All ${selected.length} venues already work at ${MODE_PHRASE[state.mode]}.`, '');
  else if (!f.rows.length) {
    body = verdictCard('bad', `No single purchase helps at ${MODE_PHRASE[state.mode]}.`,
      `Every failing venue is limited by its own display or input. ${failing.filter((t) => !t.panel_ok).length ? 'Some displays cannot show this mode at all.' : ''}`);
  } else {
    const top = f.rows[0];
    body = verdictCard('ok', `Buy one <strong>${esc(top.name)}</strong> and ${top.venues_fixed} more venue${top.venues_fixed === 1 ? '' : 's'} will work.`,
      `Today ${okToday.length} of ${selected.length} work at ${MODE_PHRASE[state.mode]}; with it, ${okToday.length + top.venues_fixed} of ${selected.length}.`)
      + `<ol class="ranking">${f.rows.slice(0, 6).map((r, i) => `
        <li class="rank card-lite">
          <span class="rank-n" aria-hidden="true">${i + 1}</span>
          <div class="rank-body">
            <p class="rank-title">${icon(ITEM.get(r.buy)?.kind, 'icon sm')} <strong>${esc(r.name)}</strong>
              <span class="tag ok">fixes ${r.venues_fixed} of ${failing.length}</span></p>
            <p class="venue-chips">${r.fixed_venues.map((v) => `<span class="vchip ok">✓ ${esc(name(v))}</span>`).join('')}
              ${r.still_failing.map((v) => `<span class="vchip">✕ ${esc(name(v))}${today.find((t) => t.id === v && !t.panel_ok) ? ' <em>(display limit)</em>' : ''}</span>`).join('')}</p>
          </div>
          <button type="button" class="btn small" data-add="${esc(r.buy)}">Add to bag</button>
        </li>`).join('')}</ol>`;
  }

  $('#panel-fix').innerHTML = `
    <fieldset class="venue-pick"><legend>My venues</legend><div class="check-grid">
      ${all.map((v) => `<label class="check"><input type="checkbox" value="${v.id}" ${selected.includes(v.id) ? 'checked' : ''} /> ${esc(v.name)}
        <span class="tag ${today.find((t) => t.id === v.id)?.ok ? 'ok' : 'bad'}">${today.find((t) => t.id === v.id) ? (today.find((t) => t.id === v.id).ok ? 'works' : 'fails') : ''}</span></label>`).join('')}
    </div></fieldset>
    ${body}
    ${selected.length ? cypherDetails([{ name: 'best_fix', params, ms: f.ms }]) : ''}`;
}

// ---------- Charging tab ----------
function renderPower() {
  const lap = ITEM.get(state.laptop);
  const bag = [...state.bag];
  const chargers = bag.filter((id) => ITEM.get(id)?.kind === 'charger');
  const params = { laptop: state.laptop, bag };
  const p = query('power', params);
  let body = '';
  if (!chargers.length) {
    body = verdictCard('warn', 'Add a charger to your bag to check charging.', 'Pick one below. You will also need a cable that fits between it and the laptop.')
      + `<div class="chips">${CAT.items.filter((i) => i.kind === 'charger').map((i) => `<button type="button" class="chip as-btn" data-add="${i.id}">${icon('charger', 'icon sm')}<span>${esc(i.name)}</span></button>`).join('')}</div>`;
  } else if (lap.pd_recommended_w == null) {
    body = verdictCard('bad', `Your ${esc(shortName(state.laptop))} doesn't charge over USB-C.`, 'It charges from its own barrel-jack adapter. Its USB-C port is data only.');
  } else if (!p.rows.length) {
    body = verdictCard('bad', 'No way to plug your charger into your laptop.',
      `None of the cables in your bag fits between ${chargers.map((c) => esc(shortName(c))).join(' / ')} and your laptop. You need a USB-C to USB-C cable${lap.connectors.includes('MagSafe3') ? ' or a USB-C to MagSafe 3 cable' : ''}.`);
  } else {
    body = p.rows.map((r) => {
      const v = {
        'fast-charge': ['ok', `Fast-charges. Up to ${fmt(r.capacity_w)} W can reach the laptop.`, `The maker says fast charging needs ${fmt(r.fast_w)} W or more.`],
        'full-speed': ['ok', `Charges normally. Up to ${fmt(r.capacity_w)} W reaches the laptop.`, `That meets the ${fmt(r.recommended_w)} W recommended${r.fast_w ? `, but fast charging needs ${fmt(r.fast_w)} W` : ''}.`],
        'below-recommended': ['warn', `Charges slowly. Only ${fmt(r.capacity_w)} W gets through.`, `The weakest link is the <strong>${esc(shortName(r.weakest_item))}</strong>. The recommended minimum is ${fmt(r.recommended_w)} W, so under heavy use the battery may still drain.`],
        unknown: ['warn', `About ${fmt(r.capacity_w)} W can reach the laptop.`, ''],
      }[r.verdict];
      const need = r.verdict === 'fast-charge' ? r.fast_w : r.recommended_w;
      return `<article class="power-card"><h3 class="visually-hidden">${esc(itemName(r.charger))}</h3>${verdictCard(v[0], `${esc(shortName(r.charger))}: ${v[1]}`, v[2])}
        ${chainDiagram(r.hops, r.joints, { unit: 'W', need, weakest: r.weakest_item, owner: (id) => (id === state.laptop ? 'Your laptop' : 'In your bag') })}</article>`;
    }).join('');
    const charging = new Set(p.rows.map((r) => r.charger));
    const unplugged = chargers.filter((c) => !charging.has(c));
    if (unplugged.length) body += `<p class="hint">No cable in your bag fits ${unplugged.map((c) => esc(shortName(c))).join(', ')} to this laptop.</p>`;
  }
  $('#panel-power').innerHTML = body + cypherDetails([{ name: 'power', params, ms: p.ms }]);
}

// ---------- orchestration ----------
function renderResults() {
  renderSetupInfo();
  const t0 = performance.now();
  try {
    if (state.tab === 'connect') renderConnect();
    if (state.tab === 'fix') renderFix();
    if (state.tab === 'power') renderPower();
  } catch (e) {
    console.error(e);
    $(`#panel-${state.tab}`).innerHTML = verdictCard('bad', 'Something went wrong running the query.', esc(e.message));
  }
  document.body.dataset.lastRenderMs = String(Math.round(performance.now() - t0));
  writeHash();
}

function selectTab(tab, focus = false) {
  state.tab = tab;
  for (const t of ['connect', 'fix', 'power']) {
    const btn = $(`#tab-${t}`);
    btn.setAttribute('aria-selected', String(t === tab));
    btn.tabIndex = t === tab ? 0 : -1;
    $(`#panel-${t}`).hidden = t !== tab;
    if (focus && t === tab) btn.focus();
  }
  renderResults();
}

function applyExample(ex) {
  Object.assign(state, { ...ex.state, bag: new Set(ex.state.bag), venues: null });
  renderControls();
  selectTab(state.tab);
}

let customTimer = null;
function wire() {
  $('#laptop').addEventListener('change', (e) => { state.laptop = e.target.value; renderResults(); });
  $('#venue').addEventListener('change', (e) => {
    state.venue = e.target.value;
    if (state.venue === 'custom') applyCustom();
    renderResults();
  });
  $('#modes').addEventListener('change', (e) => { state.mode = e.target.value; renderResults(); });
  $('#bag').addEventListener('change', (e) => {
    if (e.target.type !== 'checkbox') return;
    if (e.target.checked) state.bag.add(e.target.value); else state.bag.delete(e.target.value);
    e.target.closest('.chip').classList.toggle('on', e.target.checked);
    $('#bag-count').textContent = `(${state.bag.size} item${state.bag.size === 1 ? '' : 's'})`;
    renderResults();
  });
  $('#bag-search').addEventListener('input', renderBag);
  $('#bag-clear').addEventListener('click', () => { state.bag.clear(); renderBag(); renderResults(); });
  const onCustom = () => {
    state.custom.name = $('#custom-name').value.trim() || 'My display';
    state.custom.inputs = [...document.querySelectorAll('#custom-inputs input:checked')].map((i) => i.value);
    state.custom.max = $('#custom-max').value;
    state.custom.cable = $('#custom-cable').value;
    clearTimeout(customTimer);
    customTimer = setTimeout(() => { applyCustom(); renderResults(); }, 120);
  };
  $('#custom').addEventListener('input', onCustom);
  $('#custom').addEventListener('change', onCustom);

  document.querySelector('[role=tablist]').addEventListener('click', (e) => {
    const t = e.target.closest('[role=tab]'); if (t) selectTab(t.id.replace('tab-', ''));
  });
  document.querySelector('[role=tablist]').addEventListener('keydown', (e) => {
    const order = ['connect', 'fix', 'power'];
    const i = order.indexOf(state.tab);
    const next = { ArrowRight: (i + 1) % 3, ArrowLeft: (i + 2) % 3, Home: 0, End: 2 }[e.key];
    if (next !== undefined) { e.preventDefault(); selectTab(order[next], true); }
  });
  $('#results').addEventListener('click', (e) => {
    const add = e.target.closest('[data-add]');
    if (!add) return;
    state.bag.add(add.dataset.add);
    renderBag();
    renderResults();
    $('#engine-status').textContent = `Added ${shortName(add.dataset.add)} to your bag.`;
  });
  $('#panel-fix').addEventListener('change', (e) => {
    if (e.target.type !== 'checkbox') return;
    state.venues = new Set([...document.querySelectorAll('#panel-fix .venue-pick input:checked')].map((i) => i.value));
    renderResults();
  });
  $('#share').addEventListener('click', async () => {
    writeHash();
    try { await navigator.clipboard.writeText(location.href); $('#share').textContent = 'Link copied'; } catch { $('#share').textContent = 'Copy the address bar'; }
    setTimeout(() => { $('#share').textContent = 'Copy link to this setup'; }, 2000);
  });
  $('#examples').innerHTML = EXAMPLES.map((ex, i) => `<button type="button" class="example" data-ex="${i}">${esc(ex.label)}</button>`).join('');
  $('#examples').addEventListener('click', (e) => { const b = e.target.closest('[data-ex]'); if (b) applyExample(EXAMPLES[+b.dataset.ex]); });
}

async function main() {
  try {
    const info = await loadEngine();
    CAT = catalog();
    ITEM = new Map(CAT.items.map((i) => [i.id, i]));
    VENUE = new Map(CAT.venues.map((v) => [v.id, v]));
    MODE = new Map(CAT.modes.map((m) => [m.id, m]));
    readHash();
    sanitizeState();
    if (state.venue === 'custom') applyCustom();
    renderControls();
    wire();
    selectTab(state.tab);
    $('#engine-status').textContent = `Relate (WASM) loaded ${info.nodes} nodes and ${info.rels.toLocaleString('en')} relationships in ${info.ms} ms. Everything runs in your browser.`;
    $('#app').setAttribute('aria-busy', 'false');
    document.body.dataset.ready = 'true';
  } catch (e) {
    console.error(e);
    $('#engine-status').textContent = `Could not start the graph engine: ${e.message}`;
    document.body.dataset.ready = 'error';
  }
}

main();
