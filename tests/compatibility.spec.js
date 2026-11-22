const {test, expect} = require('@playwright/test');
const ticks = page => page.locator('.machine').evaluate(el => Number(getComputedStyle(el).getPropertyValue('--ticks')));
for (const path of ['/', '/tile/']) {
  test(`startup reports actual runtime capability on ${path}`, async ({page, browserName}, info) => {
    await page.goto(path);
    await expect(page.locator('.compat-warning')).toContainText('Chrome on iOS uses WebKit');
    expect(await page.locator('script').count()).toBe(0);
    const parsesIf = await page.evaluate(() => CSS.supports('width', 'if(style(--x:1):1px;else:2px)'));
    await page.locator('.power-switch').click();
    if (browserName === 'webkit') {
      // Playwright WebKit is an engine regression test, not a real iOS device.
      // Fail loudly if it starts working so we can revisit the support policy.
      await expect(page.locator(parsesIf ? '.stall-message' : '.unsupported-screen')).toBeVisible({timeout:6000});
      expect(await ticks(page)).toBe(0);
      await expect(page.locator('.running-message')).not.toBeVisible();
      await expect(page.locator('.tile-writing')).not.toBeVisible();
    } else {
      await expect.poll(()=>ticks(page)).toBeGreaterThan(0);
      await expect(page.locator('.unsupported-screen')).not.toBeVisible();
      await expect(page.locator('.startup-screen')).not.toBeVisible();
    }
    expect(await page.evaluate(()=>document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.screenshot({path:`test-results/compatibility-${info.project.name}-${path === '/' ? 'cpu' : 'tile'}.png`,fullPage:true});
  });
  test(`missing CSS syntax gets an immediate in-screen explanation on ${path}`, async ({page}) => {
    await page.route('**/style.css', async route => {
      const response = await route.fetch();
      const body = (await response.text()).replaceAll('@supports (width:if(style(--x:1):1px;else:2px))', '@supports (unknown-property: unsupported)');
      await route.fulfill({response, body});
    });
    await page.goto(path);
    await expect(page.locator('.unsupported-screen')).toBeVisible();
    await page.locator('.power-switch').click();
    await expect(page.locator('.unsupported-screen')).toBeVisible();
    await expect(page.locator('.running-message')).not.toBeVisible();
    await expect(page.locator('.tile-writing')).not.toBeVisible();
    expect(await ticks(page)).toBe(0);
    await page.locator('.reset').click();
    await expect(page.locator('.unsupported-screen')).toBeVisible();
  });
}
