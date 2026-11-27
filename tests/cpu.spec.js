const {readState}=require('./helpers/state');
const { test, expect } = require('@playwright/test');
const cases = [...require('./cpu-cases.json'), ...require('./addressing-cases.json'), ...require('./stack-cases.json'), ...require('./alu-cases.json'), ...require('./cb-cases.json'), ...require('./high-cases.json'), ...require('./interrupt-cases.json')];
const state = async (page,key) => (await readState(page,[key]))[key];
for (const item of cases) {
  test(item.name, async ({page}) => {
    await page.goto(`/tests/${item.name}/`);
    await page.locator('.power-switch').click();
    if (item.initial?.halted) await expect.poll(() => state(page,'ticks'), {timeout:15000}).toBe(item.expect.ticks);
    await expect.poll(() => state(page, item.fault ? 'fault' : 'halted'), { timeout: 15000 }).toBe(1);
    for (const [key,value] of Object.entries(item.expect)) expect(await state(page,key), key).toBe(value);
    if (item.fault) {
      await expect(page.locator('.fault-message')).toBeVisible();
      await expect(page.locator('.startup-screen')).not.toBeVisible();
    }
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
test('tile ROM writes VRAM and CSS decodes both bitplanes', async ({page}, info) => {
  test.setTimeout(45000);
  await page.goto('/tile/');
  await page.locator('.power-switch').click();
  // The pointer loop takes 84 instructions at the streaming clock's 240ms/step.
  await expect.poll(() => state(page,'halted'), { timeout: 35000 }).toBe(1);
  expect(await state(page,'ticks')).toBe(84);
  expect(await state(page,'pc')).toBe(271);
  expect(await state(page,'fault')).toBe(0);
  const rows = ['00333300','03111130','31211213','31111113','31211213','31122113','03111130','00333300'];
  for(let y=0;y<8;y++) for(let plane=0;plane<2;plane++) {
    const expected = [...rows[y]].reduce((v,pixel,x)=>v|(((Number(pixel)>>plane)&1)<<(7-x)),0);
    expect(await state(page,`m${0x8000+y*2+plane}`)).toBe(expected);
  }
  const shades = await page.locator('.tile-grid i').evaluateAll(elements=>elements.map(el=>Number(getComputedStyle(el).getPropertyValue('--shade'))));
  expect(shades).toEqual([...rows.join('')].map(Number));
  await expect(page.locator('.tile-ready')).toBeVisible();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  await page.screenshot({path:`test-results/tile-${info.project.name}.png`,fullPage:true});
});
test('stack lab runs nested calls and restores the loop counter', async ({page}) => {
  await page.goto('/stack/'); await page.locator('.power-switch').click();
  await expect.poll(() => state(page,'halted'), {timeout:25000}).toBe(1);
  for (const [key,value] of Object.entries({ticks:52,pc:278,a:165,b:0,c:0,sp:49216,f:192,m49154:165,m49214:9,m49215:1,m49212:0,m49213:1,m49210:28,m49211:1,fault:0})) expect(await state(page,key),key).toBe(value);
  await expect(page.locator('.passed')).toBeVisible();
});
