const {test, expect} = require('@playwright/test');
// Manual bank transfers perform many native bit saves and full-pipeline style
// reads across 1,770-bit banks. Each bit still has its own progress bound.
test.describe.configure({timeout:120000});
const read = (page, keys, selector='.machine') => page.locator(selector).evaluate((el,keys)=>Object.fromEntries(keys.map(k=>[k,Number(getComputedStyle(el).getPropertyValue(`--${k}`))])),keys);
const copyState = page => read(page,['copy-index','copy-remaining','bank-phase'],'.checkpoint-select');
async function saveBit(page, keyboard=false) {
  const before = await copyState(page);
  const control = page.locator(`.bank${1-before['bank-phase']}.copy-${before['copy-index']}`);
  const input = page.locator('#'+await control.locator('label').getAttribute('for'));
  await expect(control).toBeVisible();
  if (keyboard) { await page.keyboard.press('Tab'); await expect(control.locator('a')).toBeFocused(); await page.keyboard.press('Enter'); await expect(input).toBeFocused(); await page.keyboard.press('Space'); }
  else if (test.info().project.name.endsWith('mobile')) await control.locator('label').tap();
  else await control.locator('label').click();
  await expect.poll(async ()=>(await copyState(page))['copy-remaining']).toBe(before['copy-remaining']-1);
}
async function continueBatch(page) {
  const state = await read(page,['ticks','pc','a','b','f','m49152']);
  let saved = 0;
  while ((await copyState(page))['copy-remaining']) {
    expect(saved++).toBeLessThan(1770);
    await expect(page.locator('.commit-control')).not.toBeVisible();
    await saveBit(page);
    // Partial writes to the inactive bank must never alter this batch's result.
    expect(await read(page,Object.keys(state))).toEqual(state);
  }
  await expect(page.locator('.commit-control')).toBeVisible();
  if (test.info().project.name.endsWith('mobile')) await page.locator('.commit-control label').tap();
  else await page.locator('.commit-control label').click();
  await expect.poll(async ()=>(await read(page,['ticks'])).ticks).not.toBe(state.ticks);
}
test('checkpoint reuses two banks across nine batches and byte wrap', async ({page},info)=>{
  test.setTimeout(240000);
  await page.goto('/checkpoint/');
  expect(await page.locator('script').count()).toBe(0);
  const inputs=await page.locator('input').count();
  expect(inputs).toBe(3542); // 2 × 1770 bits, commit, power; no growing trace.
  await page.locator('.power-switch').click();
  for(let batch=1;batch<=9;batch++) {
    expect(await read(page,['ticks','pc','a','m49152','halted','fault'])).toEqual({ticks:batch*128,pc:256,a:(batch*32)%256,m49152:(batch*32)%256,halted:0,fault:0});
    if(batch<9) await continueBatch(page);
  }
  expect(await page.locator('input').count()).toBe(inputs);
  expect(await page.locator('.pipeline-execute').count()).toBe(128);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  await page.screenshot({path:`test-results/checkpoint-${info.project.name}.png`,fullPage:true});
});
test('checkpoint preserves branches and flags until a later HALT', async ({page})=>{
  await page.goto('/checkpoint/tests/long-loop/'); await page.locator('.power-switch').click();
  expect((await read(page,['ticks'])).ticks).toBe(128);
  await continueBatch(page); await continueBatch(page);
  expect(await read(page,['ticks','pc','a','b','f','m49152','halted'])).toEqual({ticks:304,pc:268,a:100,b:0,f:192,m49152:100,halted:1});
  await expect(page.locator('.halt-message')).toBeVisible();
  await expect(page.locator('.checkpoint-controls')).not.toBeVisible();
});
test('checkpoint pause retains a partial copy and reset clears both banks', async ({page})=>{
  await page.goto('/checkpoint/'); await page.locator('.power-switch').click();
  await saveBit(page);
  const partial = (await copyState(page))['copy-remaining'];
  await page.locator('.power-switch').click();
  await expect(page.locator('.checkpoint-controls')).not.toBeVisible();
  await page.locator('.power-switch').click();
  expect((await copyState(page))['copy-remaining']).toBe(partial);
  await continueBatch(page);
  await saveBit(page);
  await page.locator('.power-switch').click();
  expect(await read(page,['ticks','m49152'])).toEqual({ticks:128,m49152:32});
  await page.locator('.power-switch').click();
  expect(await read(page,['ticks','m49152'])).toEqual({ticks:256,m49152:64});
  await page.locator('.reset').click();
  expect(await read(page,['ticks','m49152'])).toEqual({ticks:0,m49152:0});
  await page.locator('.power-switch').click();
  expect(await read(page,['ticks','m49152'])).toEqual({ticks:128,m49152:32});
});
test('checkpoint controls can be used with Tab, Enter and Space', async ({page})=>{
  await page.goto('/checkpoint/');
  await page.locator('#power').focus(); await page.keyboard.press('Space');
  while((await copyState(page))['copy-remaining']) await saveBit(page,true);
  await page.keyboard.press('Tab'); await expect(page.locator('.commit-control a')).toBeFocused();
  await page.keyboard.press('Enter'); await expect(page.locator('#commit')).toBeFocused();
  await page.keyboard.press('Space');
  await expect.poll(async ()=>(await read(page,['ticks'])).ticks).toBe(256);
});
for(const [path,message] of [['diagnostic/','.passed'],['tile/','.tile-ready'],['tests/trap/','.fault-message']]) {
  test(`checkpoint stops copying when cartridge stops: ${path}`, async ({page})=>{
    await page.goto('/checkpoint/'+path); await page.locator('.power-switch').click();
    await expect(page.locator(message)).toBeVisible();
    await expect(page.locator('.checkpoint-controls')).not.toBeVisible();
  });
}

test('checkpoint copies every register and retained VRAM back into the CPU', async ({page})=>{
  // Each native bit save re-evaluates the full CPU pipeline on shared runners.
  // Per-bit progress still has its own bound; allow time for the whole copy.
  test.setTimeout(120000);
  await page.goto('/checkpoint/tests/register-vram/'); await page.locator('.power-switch').click();
  expect((await read(page,['ticks'])).ticks).toBe(128);
  await continueBatch(page);
  expect(await read(page,['ticks','a','b','c','d','e','h','l','m32783','m49215','halted'])).toEqual({ticks:132,a:170,b:1,c:2,d:4,e:8,h:16,l:32,m32783:170,m49215:170,halted:1});
});
test('checkpoint retains a 16-bit stack pointer and HL across the bank boundary', async ({page})=>{
  await page.goto('/checkpoint/tests/addressing/'); await page.locator('.power-switch').click();
  expect(await read(page,['ticks','sp','h','l'])).toEqual({ticks:128,sp:65244,h:192,l:0});
  await continueBatch(page);
  expect(await read(page,['ticks','sp','h','l','a','m49152','halted','fault'])).toEqual({ticks:131,sp:65244,h:192,l:1,a:42,m49152:42,halted:1,fault:0});
});
test('checkpoint instruction bookkeeping wraps at its documented 16-bit width', async ({page})=>{
  await page.goto('/checkpoint/tests/tick-wrap/');
  expect((await read(page,['ticks'])).ticks).toBe(65472);
  await page.locator('.power-switch').click();
  expect((await read(page,['ticks'])).ticks).toBe(64);
});
test('checkpoint capability failure hides copy controls', async ({page})=>{
  await page.route('**/*.css', async route=>{
    const response=await route.fetch();
    await route.fulfill({response,body:(await response.text()).replaceAll('@supports (width:calc(1px * mod(round(down, abs(-3), 1), 2) * sign(1)))','@supports (unknown-property: unsupported)')});
  });
  await page.goto('/checkpoint/'); await page.locator('.power-switch').click();
  await expect(page.locator('.unsupported-screen')).toBeVisible();
  await expect(page.locator('.checkpoint-controls')).not.toBeVisible();
});
test('checkpoint preserves live nested-call frames across a manual bank transfer', async ({page})=>{
  test.setTimeout(120000);
  await page.goto('/checkpoint/tests/stack-continuation/'); await page.locator('.power-switch').click();
  expect(await read(page,['ticks','pc','b','c','sp','m49212','m49213','m49214','m49215'])).toEqual({ticks:128,pc:270,b:171,c:205,sp:49212,m49212:52,m49213:18,m49214:9,m49215:1});
  await continueBatch(page);
  expect(await read(page,['ticks','pc','b','c','sp','m49210','m49211','m49212','m49213','m49214','m49215','halted','fault'])).toEqual({ticks:131,pc:266,b:18,c:52,sp:49216,m49210:14,m49211:1,m49212:52,m49213:18,m49214:9,m49215:1,halted:1,fault:0});
});
test('checkpoint stack lab needs no extra batch', async ({page})=>{
  await page.goto('/checkpoint/'); await page.getByRole('link',{name:'Stack lab',exact:true}).click();
  await expect(page).toHaveURL(/\/checkpoint\/stack\/$/);
  await page.locator('.power-switch').click();
  expect(await read(page,['ticks','sp','m49154','halted','fault'])).toEqual({ticks:52,sp:49216,m49154:165,halted:1,fault:0});
  await expect(page.locator('.checkpoint-controls')).not.toBeVisible();
});

test('checkpoint continuation carries flags into ADC after bit saves',async({page})=>{
  await page.goto('/checkpoint/tests/alu-carry/');await page.locator('.power-switch').click();
  expect(await read(page,['ticks','a','f'])).toEqual({ticks:128,a:255,f:16});
  await continueBatch(page);
  expect(await read(page,['ticks','a','f','m49154','halted','fault'])).toEqual({ticks:131,a:0,f:176,m49154:0,halted:1,fault:0});
});

test('checkpoint transfers a complete CB memory result and carry flag',async({page})=>{
  await page.goto('/checkpoint/tests/cb-carry/');await page.locator('.power-switch').click();
  expect(await read(page,['ticks','pc','f','m49152'])).toEqual({ticks:128,pc:388,f:16,m49152:192});
  await continueBatch(page);
  expect(await read(page,['ticks','pc','f','m49152','halted','fault'])).toEqual({ticks:130,pc:391,f:48,m49152:192,halted:1,fault:0});
});

test('checkpoint transfers a live restart frame at the end of HRAM',async({page})=>{
  test.setTimeout(120000);
  await page.goto('/checkpoint/tests/high-continuation/');await page.locator('.power-switch').click();
  expect(await read(page,['ticks','pc','sp','m65532','m65533','m65534'])).toEqual({ticks:128,pc:0,sp:65532,m65532:133,m65533:1,m65534:129});
  await continueBatch(page);
  expect(await read(page,['ticks','pc','a','c','f','sp','m65408','m65532','m65533','m65534','halted','fault'])).toEqual({ticks:133,pc:390,a:3,c:254,f:16,sp:65534,m65408:129,m65532:133,m65533:1,m65534:3,halted:1,fault:0});
});
