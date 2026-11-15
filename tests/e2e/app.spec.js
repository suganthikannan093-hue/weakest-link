// Main user flows of the Weakest Link web UI, run against the production build (vite preview).
// Screenshots for the README land in docs/screenshots/.
import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

const SHOTS = 'docs/screenshots';

test.use({ reducedMotion: 'reduce' });

async function open(page, hash = '') {
  const errors = [];
  page.on('pageerror', (e) => errors.push(e.message));
  await page.goto('/' + hash);
  await expect(page.locator('body')).toHaveAttribute('data-ready', 'true');
  return errors;
}
const example = (page, name) => page.getByRole('button', { name, exact: true }).click();
const verdict = (page, tab = 'connect') => page.locator(`#panel-${tab} .verdict`).first();

test('engine loads the graph in the browser and answers the default example', async ({ page }, info) => {
  const errors = await open(page);
  await expect(page.locator('#engine-status')).toContainText('499 nodes and 7,958 relationships');
  await expect(verdict(page)).toHaveAttribute('data-verdict', 'warn');
  await expect(verdict(page)).toContainText("Not at 4K at 60 Hz. You'll get 4K at 30 Hz instead.");
  const weak = page.locator('#panel-connect .hop.weak');
  await expect(weak).toHaveCount(1);
  await expect(weak.locator('.hop-name')).toContainText('USB-C multiport hub');
  // generic items cite the public spec page of the standard they claim, never the repo
  await expect(weak.locator('a.src')).toHaveAttribute('href', 'https://www.hdmi.org/spec/hdmi1_4b');
  await expect(page.locator('#panel-connect .hop')).toHaveCount(4);
  if (info.project.name === 'desktop') await page.screenshot({ path: `${SHOTS}/desktop-connect-weakest-link.png`, fullPage: true });
  else await page.screenshot({ path: `${SHOTS}/mobile-connect.png` });
  expect(errors).toEqual([]);
});

test('old Apple adapter: the one-purchase fix turns the verdict green', async ({ page }) => {
  await open(page);
  await example(page, 'Old Apple adapter + 4K TV');
  await page.getByRole('checkbox', { name: /USB-C multiport hub/ }).uncheck();
  await expect(page.locator('#panel-connect .hop.weak .hop-name')).toContainText('older model A1621');
  await expect(page.locator('#panel-connect .hop.weak a.src')).toHaveAttribute('href', 'https://support.apple.com/en-us/119850');
  await page.locator('#panel-connect .fix').getByRole('button', { name: 'Add to bag' }).click();
  await expect(verdict(page)).toHaveAttribute('data-verdict', 'ok');
  await expect(verdict(page)).toContainText('will show 4K at 60 Hz');
});

test('a 240 W USB 2.0 cable carries no video', async ({ page }) => {
  await open(page);
  await example(page, '240 W cable at a USB-C monitor');
  await expect(verdict(page)).toHaveAttribute('data-verdict', 'bad');
  await expect(verdict(page)).toContainText('Nothing in your bag connects your laptop to this display');
  await expect(verdict(page)).toContainText('USB 2.0 charge cables carry no video');
  await expect(page.locator('#panel-connect .fix')).toContainText('One purchase fixes it');
});

test("venue's own cable is named as the weakest link and lowering the mode works", async ({ page }) => {
  await open(page);
  await example(page, "Venue's old HDMI cable");
  await expect(verdict(page)).toContainText("the venue's own");
  await expect(page.locator('#panel-connect .hop.weak .owner')).toHaveText('At the venue');
  await expect(page.locator('#panel-connect .hop.weak .hop-name')).toContainText('Standard HDMI cable');
  await page.getByText('720p · 60 Hz', { exact: true }).click();
  await expect(verdict(page)).toHaveAttribute('data-verdict', 'ok');
});

test('custom display becomes part of the graph', async ({ page }, info) => {
  await open(page);
  await page.getByLabel('Laptop').selectOption('x1c-g11');
  await page.getByRole('button', { name: 'Clear' }).click();
  await page.getByRole('checkbox', { name: /USB-C to VGA adapter/ }).check();
  await page.getByLabel('Venue', { exact: true }).selectOption('custom');
  const custom = page.locator('#custom');
  await expect(custom).toBeVisible();
  await custom.getByLabel('Name').fill('Old lecture-hall projector');
  for (const box of await custom.locator('#custom-inputs input').all()) await box.setChecked(false);
  await custom.getByLabel('VGA', { exact: true }).check();
  await custom.getByLabel('Best picture it can show').selectOption('1080p60');
  await custom.getByLabel('Cable the venue leaves out').selectOption('cable-vga');
  await page.getByText('1080p · 60 Hz', { exact: true }).click();
  await expect(verdict(page)).toHaveAttribute('data-verdict', 'ok');
  await expect(verdict(page)).toContainText('Old lecture-hall projector');
  await expect(page.locator('#panel-connect .hop').last().locator('.conf')).toHaveText('You entered this');
  if (info.project.name === 'desktop') {
    await custom.scrollIntoViewIfNeeded();
    await custom.screenshot({ path: `${SHOTS}/desktop-custom-display-form.png` });
    await page.screenshot({ path: `${SHOTS}/desktop-custom-display.png`, fullPage: true });
  }
  await page.getByText('4K · 60 Hz', { exact: true }).click();
  await expect(verdict(page)).toContainText("can't show 4K at 60 Hz at all");
});

test('best single purchase across my venues', async ({ page }, info) => {
  await open(page);
  await example(page, 'One purchase, all venues');
  await expect(page.getByRole('tab', { name: 'Best purchase' })).toHaveAttribute('aria-selected', 'true');
  await expect(verdict(page, 'fix')).toContainText('USB-C to HDMI cable, 4K60');
  const top = page.locator('#panel-fix .rank').first();
  await expect(top).toContainText('fixes 3 of 9');
  await expect(top.locator('.vchip.ok')).toHaveCount(3);
  if (info.project.name === 'desktop') await page.screenshot({ path: `${SHOTS}/desktop-best-purchase.png`, fullPage: true });
  else await page.screenshot({ path: `${SHOTS}/mobile-best-purchase.png` });
  await page.locator('#panel-fix .venue-pick').getByLabel(/Conference demo booth/).uncheck();
  await expect(page.locator('#panel-fix .rank').first()).toContainText('fixes 2 of 8');
});

test('charging: a thin cable throttles a big charger', async ({ page }, info) => {
  await open(page);
  await example(page, 'Big charger, thin cable');
  await expect(verdict(page, 'power')).toHaveAttribute('data-verdict', 'warn');
  await expect(verdict(page, 'power')).toContainText('Charges slowly. Only 60 W gets through.');
  await expect(page.locator('#panel-power .hop.weak .hop-name')).toContainText('USB 2.0, 60 W');
  if (info.project.name === 'desktop') await page.screenshot({ path: `${SHOTS}/desktop-charging.png`, fullPage: true });
  else await page.screenshot({ path: `${SHOTS}/mobile-charging.png` });
  await page.getByRole('checkbox', { name: /240 W EPR/ }).check();
  await expect(page.locator('#panel-power .verdict').first()).toContainText('Fast-charges');
});

test('setup is kept in the URL and survives a reload', async ({ page }) => {
  await open(page);
  await example(page, "Venue's old HDMI cable");
  await page.getByRole('tab', { name: 'Charging' }).click();
  await page.reload();
  await expect(page.locator('body')).toHaveAttribute('data-ready', 'true');
  await expect(page.getByRole('tab', { name: 'Charging' })).toHaveAttribute('aria-selected', 'true');
  await expect(page.getByLabel('Laptop')).toHaveValue('mbp14-m3');
  await expect(page.getByLabel('Venue', { exact: true })).toHaveValue('studio-tv');
});

test('tabs work from the keyboard', async ({ page }) => {
  await open(page);
  await page.getByRole('tab', { name: 'Will it connect?' }).focus();
  await page.keyboard.press('ArrowRight');
  await expect(page.getByRole('tab', { name: 'Best purchase' })).toBeFocused();
  await expect(page.locator('#panel-fix')).toBeVisible();
  await page.keyboard.press('End');
  await expect(page.getByRole('tab', { name: 'Charging' })).toHaveAttribute('aria-selected', 'true');
});

test('no serious accessibility violations (axe)', async ({ page }) => {
  await open(page);
  for (const tab of ['Will it connect?', 'Best purchase', 'Charging']) {
    await page.getByRole('tab', { name: tab }).click();
    const res = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa']).analyze();
    const serious = res.violations.filter((v) => ['serious', 'critical'].includes(v.impact));
    expect(serious.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(' ')).slice(0, 3).join(', ')}`)).toEqual([]);
  }
});

test('answers quickly once loaded', async ({ page }) => {
  await open(page);
  await example(page, 'One purchase, all venues');
  const ms = Number(await page.locator('body').getAttribute('data-last-render-ms'));
  expect(ms).toBeLessThan(1500);
});

test('phones and tablets: a Pixel 7a has no wired video, a Pixel 8 does', async ({ page }) => {
  const errors = await open(page, '#l=pixel-7a&b=cable-usbc-dp14&v=conference-booth&m=1080p60&t=connect');
  await expect(page.locator('#laptop optgroup')).toHaveCount(3);
  await expect(page.locator('#laptop optgroup[label="Phones"] option[value="iphone-15"]')).toHaveCount(1);
  await expect(verdict(page)).toHaveAttribute('data-verdict', 'bad');
  await expect(verdict(page)).toContainText('your phone');
  await page.locator('#laptop').selectOption('pixel-8');
  await expect(verdict(page)).toHaveAttribute('data-verdict', 'ok');
  expect(errors).toEqual([]);
});

test('a dock with its own power supply counts as a charger', async ({ page }) => {
  const errors = await open(page, '#l=t14-g4&b=dock-lenovo-universal&v=meetup-hall&m=4K60&t=power');
  const card = page.locator('#panel-power .power-card').first();
  await expect(card).toContainText('Fast-charges. Up to 65 W');
  await expect(card.locator('a.src').first()).toHaveAttribute('href', /^https:\/\/(techtoday\.lenovo\.com|psref\.lenovo\.com)\//);
  expect(errors).toEqual([]);
});

test('no source link in the UI points at the repo', async ({ page }) => {
  await open(page, '#l=mba-m2&b=adp-apple-av-a1621,hub-usbc-4k30,chg-gen-65w,cable-usbc-usb2-60w&v=meetup-hall&m=4K60&t=connect');
  const hrefs = [];
  for (const tab of ['connect', 'fix', 'power']) {
    await page.locator(`#tab-${tab}`).click();
    await expect(page.locator(`#panel-${tab}`)).toBeVisible();
    hrefs.push(...await page.locator(`#panel-${tab} a.src`).evaluateAll((as) => as.map((a) => a.href)));
  }
  expect(hrefs.length).toBeGreaterThan(3);
  for (const h of hrefs) expect(h).not.toContain('github.com');
});
