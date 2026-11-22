const {test, expect} = require('@playwright/test');
// Read-only inspection; page JavaScript is disabled. Only native user controls
// start/pause/reset the machine. Nothing in the harness copies or clocks state.
const read = (page, keys) => page.locator('.machine').evaluate((el, keys) => {
  const style = getComputedStyle(el);
  return Object.fromEntries(keys.map(k => [k, Number(style.getPropertyValue(`--${k}`))]));
}, keys);
const ticks = async page => (await read(page, ['ticks'])).ticks;
const toggle = page => test.info().project.name.endsWith('mobile')
  ? page.locator('.power-switch').tap() : page.locator('.power-switch').click();
const counterKeys = ['ticks','pc','a','m49152','halted','fault'];
function assertCounter(state, initial=0) {
  expect(state.ticks % 128).toBe(initial % 128);
  const value = ((state.ticks - initial + 65536) % 65536 / 4) % 256;
  expect(state).toEqual({ticks:state.ticks, pc:256, a:value, m49152:value, halted:0, fault:0});
}

test('automatic state advances beyond 1,000 instructions with one input, then pauses/resumes/resets', async ({page}, info) => {
  test.setTimeout(60000);
  await page.goto('/automatic/');
  expect(await page.locator('script').count()).toBe(0);
  expect(await page.locator('input').count()).toBe(1);
  expect(await page.locator('.scroll-memory').count()).toBe(185);
  expect(await page.locator('.pipeline-execute').count()).toBe(128);
  const nodes = await page.locator('*').count();
  await toggle(page);
  // No inspection or input during this interval: reads must not be its clock.
  await page.waitForTimeout(2000);
  expect(await ticks(page)).toBeGreaterThanOrEqual(256);
  // Sample coherent committed state while the other bank is being rewritten.
  for (let i=0; i<6; i++) {
    await page.waitForTimeout(150);
    assertCounter(await read(page, counterKeys));
  }
  await expect.poll(() => ticks(page), {timeout:15000}).toBeGreaterThanOrEqual(1024);
  await toggle(page);
  await page.waitForTimeout(150); // Allow an in-flight layout/timeline sample to settle.
  const paused = await read(page, counterKeys);
  assertCounter(paused);
  await expect(page.locator('.auto-paused')).toBeVisible();
  await page.waitForTimeout(300);
  expect(await read(page, counterKeys)).toEqual(paused);
  await page.locator('#power').focus();
  await page.keyboard.press('Space');
  await expect.poll(() => ticks(page)).toBeGreaterThan(paused.ticks);
  await toggle(page);
  expect(await page.locator('*').count()).toBe(nodes);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({path:`test-results/automatic-${info.project.name}.png`,fullPage:true});
  await page.locator('.reset').click();
  await expect.poll(() => ticks(page)).toBe(0);
  expect(await read(page, counterKeys)).toEqual({ticks:0,pc:256,a:0,m49152:0,halted:0,fault:0});
  await toggle(page);
  await expect.poll(() => ticks(page)).toBeGreaterThanOrEqual(256);
  assertCounter(await read(page, counterKeys));
});

for (const [path, expected, message] of [
  ['diagnostic/', {ticks:24,pc:286,a:165,m49152:16,m49153:20,m49154:165,halted:1,fault:0}, '.passed'],
  ['tests/long-loop/', {ticks:304,pc:268,a:100,b:0,f:192,m49152:100,halted:1,fault:0}, '.halt-message'],
  ['tests/register-vram/', {ticks:132,a:170,b:1,c:2,d:4,e:8,h:16,l:32,m32783:170,m49215:170,halted:1,fault:0}, '.halt-message'],
  ['tests/trap/', {ticks:0,pc:256,halted:0,fault:1}, '.fault-message'],
]) {
  test(`automatic commits the complete stopped state: ${path}`, async ({page}) => {
    await page.goto('/automatic/'+path);
    await toggle(page);
    await expect.poll(() => read(page, Object.keys(expected))).toEqual(expected);
    await expect(page.locator(message)).toBeVisible();
    await expect(page.locator('.startup-screen')).not.toBeVisible();
    await page.waitForTimeout(350);
    expect(await read(page, Object.keys(expected))).toEqual(expected);
    await toggle(page); await toggle(page);
    expect(await read(page, Object.keys(expected))).toEqual(expected);
  });
}

test('automatic tile renders committed VRAM, including while paused', async ({page}) => {
  await page.goto('/automatic/tile/'); await toggle(page);
  await expect.poll(() => read(page, ['ticks','pc','halted','fault'])).toEqual({ticks:33,pc:337,halted:1,fault:0});
  await expect(page.locator('.tile-ready')).toBeVisible();
  const colors = await page.locator('.tile-grid i').evaluateAll(nodes => nodes.map(el => getComputedStyle(el).backgroundColor));
  expect(colors).toHaveLength(64);
  expect(new Set(colors).size).toBe(4);
  await toggle(page);
  expect(await page.locator('.tile-grid i').evaluateAll(nodes => nodes.map(el => getComputedStyle(el).backgroundColor))).toEqual(colors);
  await expect(page.locator('.tile-preview')).toBeVisible();
});

test('automatic bookkeeping wraps through 65535 without losing CPU state', async ({page}) => {
  await page.goto('/automatic/tests/tick-wrap/');
  expect(await ticks(page)).toBe(65472);
  await toggle(page);
  await expect.poll(() => ticks(page)).toBeLessThan(4096);
  await toggle(page); await page.waitForTimeout(150);
  assertCounter(await read(page, counterKeys), 65472);
});

test('automatic repeated pause/resume preserves committed state', async ({page}) => {
  test.setTimeout(60000);
  await page.goto('/automatic/');
  for (let i=0; i<5; i++) {
    const before = await ticks(page);
    await toggle(page);
    await expect.poll(() => ticks(page)).toBeGreaterThan(before);
    await toggle(page); await page.waitForTimeout(100);
    const state = await read(page, counterKeys);
    assertCounter(state);
    await page.waitForTimeout(100);
    expect(await read(page, counterKeys)).toEqual(state);
  }
});

test('automatic syntax failure offers a working fallback', async ({page}) => {
  await page.route('**/automatic.css', async route => {
    const response = await route.fetch();
    await route.fulfill({response,body:(await response.text()).replace('@supports (animation-timeline: --memory)', '@supports (unknown-property: unsupported)')});
  });
  await page.goto('/automatic/'); await toggle(page);
  await expect(page.locator('.unsupported-screen')).toBeVisible();
  await expect(page.locator('.on-screen')).not.toBeVisible();
  await page.locator('.unsupported-screen a').click();
  await expect(page).toHaveURL(/\/checkpoint\/$/);
});

test('automatic startup detects accepted syntax without working storage', async ({page}) => {
  await page.route('**/automatic.css', async route => {
    const response = await route.fetch();
    await route.fulfill({response,body:await response.text()+'\n.scroll-memory {scroll-snap-type:none !important;}'});
  });
  await page.goto('/automatic/'); await toggle(page);
  await expect(page.locator('.stall-message')).toBeVisible({timeout:6000});
  expect(await ticks(page)).toBe(0);
  await expect(page.locator('.on-screen')).not.toBeVisible();
});
