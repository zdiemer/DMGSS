const { test, expect } = require('@playwright/test');
const cases = require('./cpu-cases.json');
const state = (page, key) => page.locator('.machine').evaluate((el, k) => Number(getComputedStyle(el).getPropertyValue(`--${k}`)), key);
for (const item of cases) {
  test(item.name, async ({page}) => {
    await page.goto(`/tests/${item.name}/`);
    await page.locator('.power-switch').click();
    await expect.poll(() => state(page, item.fault ? 'fault' : 'halted'), { timeout: 15000 }).toBe(1);
    for (const [key,value] of Object.entries(item.expect)) expect(await state(page,key), key).toBe(value);
  });
}
test('original ROM completes its branching RAM diagnostic', async ({page}) => {
  await page.goto('/');
  await page.locator('.power-switch').click();
  await expect.poll(() => state(page,'halted'), { timeout: 20000 }).toBe(1);
  expect(await state(page,'fault')).toBe(0);
  expect(await state(page,'m49152')).toBe(16);
  expect(await state(page,'m49153')).toBe(20);
  expect(await state(page,'m49154')).toBe(165);
  await expect(page.locator('.passed')).toBeVisible();
});
