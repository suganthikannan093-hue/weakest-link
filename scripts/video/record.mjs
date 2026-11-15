// Records the demo video's scenes from the local preview build (vite preview on :4173) and a real
// terminal, by screen-capturing an Xvfb display with ffmpeg (x11grab). Nothing leaves localhost.
//   Xvfb :99 -screen 0 1920x1200x24 &   npx vite preview --port 4173 --strictPort &
//   DISPLAY=:99 node scripts/video/record.mjs [scene ...]
// v2: no drawn pointer. Emphasis is a soft highlight box around the element, clicks get a ripple,
// and every action is scheduled against the narration's word timestamps (words.json from transcribe.py).
import { chromium } from 'playwright';
import { spawn } from 'child_process';
import { readFileSync, mkdirSync, writeFileSync } from 'fs';
import { fileURLToPath } from 'url';
import path from 'path';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, '../..');
const WORK = process.env.WL_VIDEO_WORK || '/workspace/wlvideo-work';
const DISPLAY = process.env.DISPLAY || ':99';
const TOP = 109; // browser toolbar height in device px (window 1536x950 DIP at 1.25x); capture starts below it
const APP = 'http://localhost:4173/';
const T = JSON.parse(readFileSync(path.join(HERE, 'timing.json'), 'utf8'));
mkdirSync(`${WORK}/scenes`, { recursive: true });
const durs = JSON.parse(readFileSync(`${WORK}/tts_durations.json`, 'utf8'));
const words = JSON.parse(readFileSync(`${WORK}/words.json`, 'utf8'));
const target = (id) => durs[id] + T.lead + (T.tail[id] ?? T.tail.default);
// scene time (s) at which the narration of `id` says `word` (n-th occurrence), plus an offset
const at = (id, word, off = 0, n = 1) => {
  const hits = words[id].words.filter((w) => w.word.toLowerCase().replace(/[^a-z0-9']/g, '') === word.toLowerCase());
  if (hits.length < n) throw new Error(`${id}: no word '${word}' #${n}`);
  return T.lead + hits[n - 1].start + off;
};
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const live = new Set();
const watchdog = setTimeout(() => { console.error('watchdog: giving up'); for (const p of live) p.kill('SIGKILL'); process.exit(2); }, 300_000);
const marks = {};

function startRec(id) {
  const out = `${WORK}/scenes/${id}.mp4`;
  const ff = spawn('ffmpeg', ['-loglevel', 'error', '-y', '-f', 'x11grab', '-draw_mouse', '0', '-framerate', '30',
    '-video_size', '1920x1080', '-i', `${DISPLAY}+0,${TOP}`, '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '14',
    '-pix_fmt', 'yuv420p', out], { stdio: ['pipe', 'inherit', 'inherit'] });
  live.add(ff);
  const t0 = Date.now();
  marks[id] = [];
  return {
    until: async (s) => { const left = s * 1000 - (Date.now() - t0); if (left > 0) await sleep(left); },
    mark: (label) => marks[id].push([label, +((Date.now() - t0) / 1000).toFixed(2)]),
    async stop(minSeconds) {
      const left = (minSeconds + 0.5) * 1000 - (Date.now() - t0); // margin: ffmpeg starts a little after t0
      if (left > 0) await sleep(left);
      ff.stdin.write('q');
      await new Promise((r) => ff.on('close', r));
      live.delete(ff);
      console.log(`${id}: ${((Date.now() - t0) / 1000).toFixed(1)} s (target ${minSeconds.toFixed(1)})`);
    },
  };
}

// highlight boxes and click ripples, drawn in the page (document coordinates, so they follow scrolling)
const FX = `(() => {
  if (window.__spot) return;
  const st = document.createElement('style');
  st.textContent = '.__spot{position:absolute;z-index:99998;pointer-events:none;border-radius:12px;border:3px solid #0b6bcb;box-shadow:0 0 0 6px rgba(11,107,203,.18),0 8px 30px rgba(11,107,203,.25);opacity:0;transition:opacity .35s ease,transform .35s ease;transform:scale(1.04)}'
    + '.__spot.on{opacity:1;transform:none}.__spot.weak{border-color:#e11d48;box-shadow:0 0 0 6px rgba(225,29,72,.18),0 8px 30px rgba(225,29,72,.25)}'
    + '.__rip{position:absolute;z-index:99999;pointer-events:none;width:44px;height:44px;margin:-22px 0 0 -22px;border-radius:50%;background:rgba(11,107,203,.35);border:3px solid #0b6bcb}';
  document.head.append(st);
  window.__spot = (x, y, w, h, ms, cls) => {
    const d = document.createElement('div'); d.className = '__spot ' + (cls || '');
    Object.assign(d.style, { left: (x - 6) + 'px', top: (y - 6) + 'px', width: (w + 12) + 'px', height: (h + 12) + 'px' });
    document.body.append(d); requestAnimationFrame(() => d.classList.add('on'));
    setTimeout(() => { d.classList.remove('on'); setTimeout(() => d.remove(), 400); }, ms);
  };
  window.__ripple = (x, y) => {
    const r = document.createElement('div'); r.className = '__rip';
    Object.assign(r.style, { left: x + 'px', top: y + 'px' }); document.body.append(r);
    r.animate([{ transform: 'scale(.3)', opacity: 1 }, { transform: 'scale(1.6)', opacity: 0 }], { duration: 600, easing: 'cubic-bezier(.2,.7,.3,1)' }).onfinish = () => r.remove();
  };
})()`;

async function box(page, loc) {
  await loc.scrollIntoViewIfNeeded();
  const b = await loc.boundingBox();
  const s = await page.evaluate(() => [scrollX, scrollY]);
  return { x: b.x + s[0], y: b.y + s[1], w: b.width, h: b.height, vx: b.x, vy: b.y };
}
async function spot(page, loc, ms = 1600, cls = '') {
  await page.evaluate(FX);
  const b = await box(page, loc);
  await page.evaluate(([x, y, w, h, ms, cls]) => window.__spot(x, y, w, h, ms, cls), [b.x, b.y, b.w, b.h, ms, cls]);
}
async function tap(page, loc, { before = 350 } = {}) {
  await page.evaluate(FX);
  const b = await box(page, loc);
  await page.evaluate(([x, y, w, h]) => window.__spot(x, y, w, h, 700, ''), [b.x, b.y, b.w, b.h]);
  await sleep(before); // a short pause before the click
  await page.evaluate(([x, y]) => window.__ripple(x, y), [b.x + Math.min(b.w / 2, 80), b.y + b.h / 2]);
  await loc.click();
}
const smoothTo = (page, sel, block = 'start') => page.evaluate(([s, b]) => document.querySelector(s)?.scrollIntoView({ behavior: 'smooth', block: b }), [sel, block]);
async function load(page, hash) {
  await page.goto(APP + hash);
  await page.reload(); // a hash-only change does not reload the app
  await page.waitForSelector('body[data-ready="true"]');
  await page.evaluate(FX);
}

const SCENES = {
  async hook(page) {
    await page.goto('file://' + path.join(HERE, 'cards/hook.html'));
    await sleep(150);
    const r = startRec('hook');
    await r.stop(target('hook'));
  },
  async ui(page) {
    // venue-first-safe order: start from a working bag so no empty state is ever on screen
    await load(page, '#l=mbp14-m3&b=hub-usbc-4k30,chg-apple-70w,cable-usbc-usb2-60w&v=studio-tv&m=1080p60&t=connect');
    await page.evaluate(() => window.scrollTo(0, 0));
    await sleep(300);
    const r = startRec('ui');
    await r.until(at('ui', 'pick', 0.1));
    await tap(page, page.getByLabel('Laptop'), { before: 300 });
    await page.keyboard.press('Escape');
    await page.getByLabel('Laptop').selectOption('mba-m2'); r.mark('laptop');
    await r.until(at('ui', 'tick', 0.3));
    await tap(page, page.locator('#bag label.chip', { hasText: /older model A1621/ }).first(), { before: 300 }); r.mark('tick');
    await r.until(at('ui', 'venue', 0.2));
    await tap(page, page.getByLabel('Venue', { exact: true }), { before: 250 });
    await page.keyboard.press('Escape');
    await page.getByLabel('Venue', { exact: true }).selectOption('meetup-hall'); r.mark('venue');
    await r.until(at('ui', 'picture', 0.2));
    await tap(page, page.locator('#modes label', { hasText: '4K · 60 Hz' }), { before: 250 }); r.mark('4K60');
    await r.until(at('ui', 'browser', 0.0));
    await spot(page, page.locator('#engine-status'), 1800);
    await sleep(1300);
    await smoothTo(page, '#results', 'start');
    await r.stop(target('ui'));
  },
  async diagram(page) {
    await smoothTo(page, '#results', 'start');
    await sleep(700);
    const r = startRec('diagram');
    const hops = page.locator('#panel-connect .hop');
    const names = ['port', 'hub', 'cable', 'projector'];
    for (let i = 0; i < 4; i++) { await r.until(at('diagram', names[i], 0.05)); await spot(page, hops.nth(i), i === 3 ? 900 : 650); }
    await r.until(at('diagram', 'weakest', 0.1));
    await spot(page, page.locator('#panel-connect .hop.weak'), 3200, 'weak');
    await r.until(at('diagram', 'hdmi', 0.0));
    await spot(page, page.locator('#panel-connect .hop.weak .hop-metric'), 1800, 'weak');
    await r.until(at('diagram', 'source', -0.1));
    await spot(page, page.locator('#panel-connect .hop.weak a.src'), 1500);
    await r.until(at('diagram', 'confidence', -0.2));
    await spot(page, page.locator('#panel-connect .hop.weak .conf'), 1500);
    await r.stop(target('diagram'));
  },
  async fix(page) {
    await load(page, '#l=mba-m2&b=adp-apple-av-a1621&v=meetup-hall&m=4K60&t=fix');
    await page.evaluate(() => document.querySelector('#results').scrollIntoView({ block: 'start' }));
    await sleep(300);
    const r = startRec('fix');
    await r.until(at('fix', 'across', 0));
    await spot(page, page.locator('#panel-fix .venue-pick'), 2200);
    await r.until(at('fix', 'one', 0));
    await spot(page, page.locator('#panel-fix .rank').first(), 3200);
    await r.until(at('fix', 'display', -0.2));
    const lim = page.locator('#panel-fix .rank').first().locator('.vchip', { has: page.locator('em') }).first();
    if (await lim.count()) await spot(page, lim, 2400, 'weak');
    await r.stop(target('fix'));
  },
  async charge(page) {
    await load(page, '#l=mbp14-m3&b=chg-apple-140w,cable-usbc-usb2-60w&v=meetup-hall&m=4K60&t=power');
    await page.evaluate(() => document.querySelector('#results').scrollIntoView({ block: 'start' }));
    await sleep(300);
    const r = startRec('charge');
    await r.until(at('charge', '140', 0));
    await spot(page, page.locator('#panel-power .verdict').first(), 1700);
    await r.until(at('charge', 'thin', 0));
    await spot(page, page.locator('#panel-power .hop.weak').first(), 1700, 'weak');
    await r.until(at('charge', 'names', 0));
    await spot(page, page.locator('#panel-power .charge-fix .fix-main').first(), 1500);
    await r.until(at('charge', 'click', -0.3));
    await tap(page, page.locator('#panel-power .charge-fix').getByRole('button', { name: 'Add to bag' }).first(), { before: 300 }); r.mark('add');
    await page.evaluate(() => document.querySelector('#results').scrollIntoView({ block: 'start' }));
    await r.until(at('charge', 'fast', 0));
    await spot(page, page.locator('#panel-power .verdict').first(), 1500);
    await r.stop(target('charge'));
  },
  async close(page) {
    await page.goto('file://' + path.join(HERE, 'cards/close.html'));
    await sleep(150);
    const r = startRec('close');
    await r.stop(target('close'));
  },
};

async function terminalScene() {
  // a real xfce4-terminal running the offline agent demo over relate serve --mcp, in --brief mode
  const A = T.agent;
  const cmd = `python3 scripts/agent_demo.py --brief --pace ${A.pace}`;
  const sh = `unset NO_COLOR FORCE_COLOR; cd ${ROOT}; clear; printf '\\033[1;32mweakest-link\\033[0m $ '; sleep ${A.type_at};
    s='${cmd}'; for i in $(seq 0 $((\${#s}-1))); do printf '%s' "\${s:$i:1}"; sleep 0.03; done; echo; ${cmd}; sleep 60`;
  const term = spawn('xfce4-terminal', ['--disable-server', '--hide-menubar', '--hide-toolbar', '--hide-scrollbar',
    `--geometry=${A.cols}x${A.rows}+0+${TOP}`, `--font=DejaVu Sans Mono ${A.font_pt}`, '--color-bg=#0b1120', '--color-text=#e6ebf5',
    '--title=weakest-link', '-x', 'bash', '-c', sh], { stdio: 'ignore', env: { ...process.env, DISPLAY } });
  live.add(term);
  const r = startRec('agent');
  await r.stop(target('agent'));
  term.kill(); live.delete(term);
}

const only = process.argv.slice(2);
const want = (id) => !only.length || only.includes(id);
const browser = await chromium.launch({ headless: false, ignoreDefaultArgs: ['--enable-automation'],
  args: ['--window-position=0,0', '--window-size=1536,950', '--force-device-scale-factor=1.25', '--disable-infobars', '--hide-scrollbars'] });
const ctx = await browser.newContext({ viewport: null });
const page = await ctx.newPage();
page.setDefaultTimeout(10_000);
try {
  for (const id of ['hook', 'ui', 'diagram', 'fix', 'charge']) if (want(id)) await SCENES[id](page);
  if (want('agent')) {
    await page.goto('about:blank');
    await page.evaluate(() => { document.body.style.background = '#0b1120'; });
    await terminalScene();
  }
  if (want('close')) await SCENES.close(page);
} finally {
  for (const p of live) p.kill('SIGKILL');
  await browser.close();
  clearTimeout(watchdog);
  let prev = {};
  try { prev = JSON.parse(readFileSync(`${WORK}/marks.json`, 'utf8')); } catch { /* first run */ }
  writeFileSync(`${WORK}/marks.json`, JSON.stringify({ ...prev, ...marks }, null, 1));
}
