// Records the demo video's scenes from the local preview build (vite preview on :4173) and a real
// terminal, by screen-capturing an Xvfb display with ffmpeg (x11grab). Nothing leaves localhost.
//   Xvfb :99 -screen 0 1920x1200x24 &   npx vite preview --port 4173 --strictPort &
//   DISPLAY=:99 node scripts/video/record.mjs [scene ...]
import { chromium } from 'playwright';
import { spawn } from 'child_process';
import { readFileSync, mkdirSync } from 'fs';
import { fileURLToPath } from 'url';
import path from 'path';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, '../..');
const WORK = process.env.WL_VIDEO_WORK || '/workspace/wlvideo-work';
const DISPLAY = process.env.DISPLAY || ':99';
const TOP = 109; // browser toolbar height in device px (window 1536x950 DIP at 1.25x); capture starts below it
const URL = 'http://localhost:4173/';
mkdirSync(`${WORK}/scenes`, { recursive: true });
const durs = JSON.parse(readFileSync(`${WORK}/tts_durations.json`, 'utf8'));
const LEAD = 0.6, TAIL = 0.9;
const target = (id, extra = 0) => durs[id] + LEAD + TAIL + extra;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const live = new Set();
const watchdog = setTimeout(() => { console.error('watchdog: giving up'); for (const p of live) p.kill('SIGKILL'); process.exit(2); }, 300_000);

function startRec(id) {
  const out = `${WORK}/scenes/${id}.mp4`;
  const ff = spawn('ffmpeg', ['-loglevel', 'error', '-y', '-f', 'x11grab', '-draw_mouse', '0', '-framerate', '30',
    '-video_size', '1920x1080', '-i', `${DISPLAY}+0,${TOP}`, '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '14',
    '-pix_fmt', 'yuv420p', out], { stdio: ['pipe', 'inherit', 'inherit'] });
  live.add(ff);
  const t0 = Date.now();
  return {
    async stop(minSeconds) {
      const left = minSeconds * 1000 - (Date.now() - t0);
      if (left > 0) await sleep(left);
      ff.stdin.write('q');
      await new Promise((r) => ff.on('close', r));
      live.delete(ff);
      console.log(`${id}: ${((Date.now() - t0) / 1000).toFixed(1)} s (target ${minSeconds.toFixed(1)})`);
    },
  };
}

// a visible pointer: CDP input does not move the X cursor, so draw one in the page
const CURSOR = `(() => {
  if (window.__cur) return;
  const c = document.createElement('div');
  c.innerHTML = '<svg width="28" height="28" viewBox="0 0 24 24"><path d="M3 2l7 19 2.6-7.4L20 11z" fill="#fff" stroke="#0f172a" stroke-width="1.6" stroke-linejoin="round"/></svg>';
  Object.assign(c.style, { position: 'fixed', left: '0', top: '0', zIndex: 99999, pointerEvents: 'none', transition: 'transform .55s cubic-bezier(.3,.7,.3,1)', transform: 'translate(1200px, 700px)', filter: 'drop-shadow(0 2px 3px rgba(0,0,0,.35))' });
  const ring = document.createElement('div');
  Object.assign(ring.style, { position: 'fixed', width: '34px', height: '34px', margin: '-17px 0 0 -17px', borderRadius: '50%', border: '3px solid #0b6bcb', opacity: 0, zIndex: 99998, pointerEvents: 'none' });
  document.documentElement.append(c, ring);
  window.__cur = (x, y) => { c.style.transform = 'translate(' + x + 'px,' + y + 'px)'; };
  window.__tap = (x, y) => { ring.style.left = x + 'px'; ring.style.top = y + 'px'; ring.animate([{ opacity: .9, transform: 'scale(.4)' }, { opacity: 0, transform: 'scale(1.4)' }], { duration: 500 }); };
})()`;

async function point(page, loc, { click = true, pause = 250 } = {}) {
  await loc.scrollIntoViewIfNeeded();
  const b = await loc.boundingBox();
  const x = b.x + Math.min(b.width / 2, 60), y = b.y + b.height / 2;
  await page.evaluate(CURSOR);
  await page.evaluate(([x, y]) => window.__cur(x - 4, y - 3), [x, y]);
  await sleep(600);
  if (click) {
    await page.evaluate(([x, y]) => window.__tap(x, y), [x, y]);
    await loc.click();
  }
  await sleep(pause);
}
const smoothTo = (page, sel, block = 'start') => page.evaluate(([s, b]) => document.querySelector(s)?.scrollIntoView({ behavior: 'smooth', block: b }), [sel, block]);

async function ensureApp(page) {
  if (page.url().startsWith(URL)) return;
  await page.goto(URL);
  await page.evaluate(() => localStorage.setItem('wl-intro-seen', '1'));
  await ready(page, URL);
}

async function ready(page, url) {
  await page.goto(url);
  await page.waitForSelector('body[data-ready="true"]');
  await page.evaluate(CURSOR);
}

const SCENES = {
  async hook(page) {
    await page.goto('file://' + path.join(HERE, 'cards/hook.html'));
    await sleep(200);
    const r = startRec('hook');
    await r.stop(target('hook', 0.2));
  },
  async ui(page) {
    await page.goto(URL);
    await page.evaluate(() => localStorage.clear());
    await ready(page, URL);
    await page.evaluate(() => window.scrollTo(0, 0));
    await sleep(400);
    const r = startRec('ui');
    await sleep(1500);
    await point(page, page.getByRole('button', { name: 'Got it' }), { pause: 400 });
    await page.evaluate(() => window.scrollTo({ top: 0, behavior: 'smooth' }));
    await point(page, page.getByLabel('Laptop'), { click: false, pause: 150 });
    await page.getByLabel('Laptop').selectOption('mba-m2');
    await point(page, page.locator('#bag-clear'), { pause: 350 });
    for (const name of [/USB-C multiport hub/, /older model A1621/]) {
      await point(page, page.locator('#bag label.chip', { hasText: name }).first(), { click: false, pause: 0 });
      await page.getByRole('checkbox', { name }).check();
      await sleep(350);
    }
    await page.getByRole('checkbox', { name: /Apple 70W/ }).check();
    await page.getByRole('checkbox', { name: /USB 2\.0, 60 W/ }).first().check();
    await point(page, page.getByLabel('Venue', { exact: true }), { click: false, pause: 150 });
    await page.getByLabel('Venue', { exact: true }).selectOption('meetup-hall');
    await point(page, page.locator('#modes label', { hasText: '4K · 60 Hz' }), { pause: 300 });
    await smoothTo(page, '#results', 'start');
    await r.stop(target('ui'));
  },
  async diagram(page) {
    await ensureApp(page);
    await smoothTo(page, '#results', 'start');
    const r = startRec('diagram');
    await sleep(800);
    await point(page, page.locator('#panel-connect .verdict').first(), { click: false, pause: 1700 });
    await point(page, page.locator('#panel-connect .hop.weak .hop-name'), { click: false, pause: 2200 });
    await point(page, page.locator('#panel-connect .hop.weak .conf').first(), { click: false, pause: 1200 });
    await point(page, page.locator('#panel-connect .hop.weak a.src'), { click: false, pause: 1500 });
    const cy = page.locator('#panel-connect details summary').filter({ hasText: /Cypher/ }).first();
    if (await cy.count()) { await point(page, cy, { pause: 500 }); await smoothTo(page, '#panel-connect details[open] pre', 'center'); }
    await r.stop(target('diagram'));
  },
  async fix(page) {
    await ensureApp(page);
    await page.evaluate(() => window.scrollTo(0, 0));
    await sleep(300);
    const r = startRec('fix');
    await sleep(600);
    await point(page, page.getByRole('button', { name: 'One purchase, all venues', exact: true }), { pause: 1000 });
    await smoothTo(page, '#results', 'start');
    await sleep(1200);
    await point(page, page.locator('#panel-fix .rank').first(), { click: false, pause: 2500 });
    const limited = page.locator('#panel-fix').getByText(/own (display|projector)|display is the limit|limited by/i).first();
    if (await limited.count()) await point(page, limited, { click: false, pause: 1500 });
    await r.stop(target('fix'));
  },
  async charge(page) {
    await ensureApp(page);
    await page.evaluate(() => window.scrollTo(0, 0));
    await sleep(300);
    const r = startRec('charge');
    await sleep(400);
    await point(page, page.getByRole('button', { name: 'Big charger, thin cable', exact: true }), { pause: 600 });
    await smoothTo(page, '#results', 'start');
    await sleep(800);
    await point(page, page.locator('#panel-power .hop.weak').first(), { click: false, pause: 1100 });
    await point(page, page.locator('#panel-power .charge-fix .fix-main').first(), { click: false, pause: 900 });
    await point(page, page.locator('#panel-power .charge-fix').getByRole('button', { name: 'Add to bag' }).first(), { pause: 500 });
    await smoothTo(page, '#results', 'start');
    await point(page, page.locator('#panel-power .verdict').first(), { click: false, pause: 600 });
    await r.stop(target('charge'));
  },
  async close(page) {
    await page.goto('file://' + path.join(HERE, 'cards/close.html'));
    await sleep(200);
    const r = startRec('close');
    await r.stop(target('close', 0.6));
  },
};

async function terminalScene() {
  // a real xfce4-terminal running the offline agent demo over relate serve --mcp
  const cmd = 'python3 scripts/agent_demo.py --pace 1.6';
  const sh = `unset NO_COLOR FORCE_COLOR; cd ${ROOT}; clear; sleep 0.6; printf '\\033[1;32mweakest-link\\033[0m $ ';
    s='${cmd}'; for i in $(seq 0 $((\${#s}-1))); do printf '%s' "\${s:$i:1}"; sleep 0.04; done; echo; ${cmd}; sleep 60`;
  const term = spawn('xfce4-terminal', ['--disable-server', '--hide-menubar', '--hide-toolbar', '--hide-scrollbar',
    `--geometry=120x34+0+${TOP}`, '--font=DejaVu Sans Mono 20', '--color-bg=#0b1120', '--color-text=#e6ebf5', '--title=weakest-link',
    '-x', 'bash', '-c', sh], { stdio: 'ignore', env: { ...process.env, DISPLAY } });
  live.add(term);
  await sleep(700);
  const r = startRec('agent');
  await r.stop(target('agent', 1.5));
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
}
