const {readState}=require('./helpers/state');
const { test, expect } = require('@playwright/test');
const state = async (page,key) => (await readState(page,[key]))[key];
test('CSS clock retains state, pauses and resets without scripts', async ({ page }) => {
  await page.goto('/');
  expect(await page.locator('script').count()).toBe(0);
  expect(await state(page, 'ticks')).toBe(0);
  await page.locator('.power-switch').click();
  await expect.poll(() => state(page, 'ticks')).toBeGreaterThan(2);
  await page.locator('.power-switch').click();
  const paused = await state(page, 'ticks');
  await page.waitForTimeout(900);
  expect(await state(page, 'ticks')).toBe(paused);
  await Promise.all([page.waitForNavigation({waitUntil:'load'}), page.locator('.reset').click()]);
  expect(await state(page, 'ticks')).toBe(0);
});
test('console fits the viewport and controls are keyboard reachable', async ({ page }, info) => {
  await page.goto('/');
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  const screen = await page.locator('.lcd').boundingBox();
  expect(screen.width / screen.height).toBeCloseTo(160 / 144, 1);
  await page.locator('#power').focus();
  await page.keyboard.press('Space');
  await expect(page.locator('#power')).toBeChecked();
  await expect.poll(() => state(page, 'ticks')).toBeGreaterThan(0);
  await page.screenshot({path:info.outputPath(`${info.project.name}.png`),fullPage:true});
});
