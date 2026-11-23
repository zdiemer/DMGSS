const {test, expect} = require('@playwright/test');
const cases = [...require('./cpu-cases.json'), ...require('./addressing-cases.json')];
const state = (page, key) => page.locator('.machine').evaluate((el,k)=>Number(getComputedStyle(el).getPropertyValue(`--${k}`)),key);
for (const item of cases) {
  test(`portable ${item.name}`, async ({page})=>{
    await page.goto(`/portable/tests/${item.name}/`);
    expect(await state(page,'ticks')).toBe(0);
    expect(await state(page,'pc')).toBe(256);
    await page.locator('.power-switch').click();
    await expect.poll(()=>state(page,item.fault?'fault':'halted')).toBe(1);
    for(const [key,value] of Object.entries(item.expect)) expect(await state(page,key), key).toBe(value);
    if(item.fault) await expect(page.locator('.fault-message')).toBeVisible();
    await expect(page.locator('.unsupported-screen')).not.toBeVisible();
  });
}
test('portable diagnostic runs without CSS if and resets to initial state', async ({page},info)=>{
  await page.route('**/style.css', async route=>{
    const response=await route.fetch();
    await route.fulfill({response,body:(await response.text()).replaceAll('@supports (width:if(style(--x:1):1px;else:2px))','@supports (unknown-property: unsupported)')});
  });
  await page.goto('/portable/');
  expect(await page.locator('script').count()).toBe(0);
  expect(await page.locator('.pipeline-execute').count()).toBe(128);
  const css=await (await page.request.get('/portable/machine.css')).text();
  expect(css).not.toMatch(/\bif\(/);
  await page.locator('.power-switch').click();
  await expect(page.locator('.passed')).toBeVisible();
  for(const [key,value] of Object.entries({ticks:24,halted:1,fault:0,m49152:16,m49153:20,m49154:165})) expect(await state(page,key)).toBe(value);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  await page.screenshot({path:`test-results/portable-${info.project.name}.png`,fullPage:true});
  await page.locator('.power-switch').click();
  expect(await state(page,'ticks')).toBe(0);
  expect(await state(page,'m49154')).toBe(0);
  await page.locator('#power').focus(); await page.keyboard.press('Space');
  await expect(page.locator('.passed')).toBeVisible();
});
test('portable tile cartridge decodes actual VRAM into all four shades', async ({page},info)=>{
  await page.goto('/portable/tile/'); await page.locator('.power-switch').click();
  await expect(page.locator('.tile-ready')).toBeVisible();
  expect(await state(page,'ticks')).toBe(84);
  const rows=['00333300','03111130','31211213','31111113','31211213','31122113','03111130','00333300'];
  const shades=await page.locator('.tile-grid i').evaluateAll(els=>els.map(e=>Number(getComputedStyle(e).getPropertyValue('--shade'))));
  expect(shades).toEqual([...rows.join('')].map(Number));
  const colors=await page.locator('.tile-grid i').evaluateAll(els=>[...new Set(els.map(e=>getComputedStyle(e).backgroundColor))]);
  expect(colors.sort()).toEqual(['rgb(177, 195, 126)','rgb(139, 175, 98)','rgb(82, 117, 71)','rgb(49, 69, 44)'].sort());
  await page.screenshot({path:`test-results/portable-tile-${info.project.name}.png`,fullPage:true});
});
test('portable infinite loop stops at the budget without inventing HALT', async ({page})=>{
  await page.goto('/portable/tests/loop/'); await page.locator('.power-switch').click();
  expect(await state(page,'ticks')).toBe(128); expect(await state(page,'pc')).toBe(256);
  expect(await state(page,'halted')).toBe(0); expect(await state(page,'fault')).toBe(0);
  await expect(page.locator('.running-message')).toHaveText('STEP LIMIT');
  await expect(page.locator('.running-message')).toBeVisible();
  await page.waitForTimeout(350); expect(await state(page,'ticks')).toBe(128);
});
test('portable tile trap remains visible', async ({page})=>{
  await page.goto('/portable/tests/tile-fault/'); await page.locator('.power-switch').click();
  await expect(page.locator('.fault-message')).toBeVisible();
  await expect(page.locator('.tile-preview')).not.toBeVisible();
});
for (const path of ['/portable/', '/portable/tile/']) {
  test(`portable missing math support explains the limitation on ${path}`, async ({page})=>{
    await page.route('**/portable.css', async route=>{
      const response=await route.fetch();
      await route.fulfill({response,body:(await response.text()).replaceAll('@supports (width:calc(1px * mod(round(down, abs(-3), 1), 2) * sign(1)))','@supports (unknown-property: unsupported)')});
    });
    await page.goto(path);
    await expect(page.locator('.unsupported-screen')).toBeVisible();
    await page.locator('.power-switch').click();
    await expect(page.locator('.unsupported-screen')).toBeVisible();
    await expect(page.locator('.on-screen')).not.toBeVisible();
    await expect(page.locator('.tile-preview')).not.toBeVisible();
  });
}
