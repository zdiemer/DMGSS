const {readState}=require('./helpers/state');
const {test, expect} = require('@playwright/test');
// Active-bank tap/readback cycles include full mapped-memory fetch evaluation.
// Overall time is separate from the existing per-progress and exact-state checks.
test.describe.configure({timeout:120000});
// Read-only inspection; page JavaScript is disabled. Only native user controls
// start/pause/reset the machine. Nothing in the harness copies or clocks state.
const read = readState;
// Expanded banks took about 19s per active read locally, and exceeded 30s
// on shared Chromium CI. Range membership gates reduce local reads to 12–13s;
// allow 60s for observation on shared runners. Keep all coherence assertions
// and the unattended interval; these bounds do not drive the CSS clock.
const STATE_TIMEOUT = 60000;
const ticks = async page => (await read(page, ['ticks'])).ticks;
const toggle = page => test.info().project.name.endsWith('mobile')
  ? page.locator('.power-switch').tap() : page.locator('.power-switch').click();
const counterKeys = ['ticks','tcycles','m65284','div-low','pc','a','m49152','halted','fault'];
function assertCounter(state, initial=0) {
  expect(state.ticks % 128).toBe(initial % 128);
  const value = ((state.ticks - initial + 65536) % 65536 / 4) % 256;
  const cycles=((state.ticks-initial+65536)%65536*12)%65536;
  expect(state).toEqual({ticks:state.ticks, tcycles:cycles, m65284:Math.floor(cycles/256), 'div-low':cycles%256, pc:256, a:value, m49152:value, halted:0, fault:0});
}

test('automatic state advances beyond 1,000 instructions with one input, then pauses/resumes/resets', async ({page}, info) => {
  // RAM, timer and serial state expand retention to 16627 cells, with mapped-RAM
  // fetches. Budget repeated tap/readback cycles; retain bounded progress checks.
  // The full VRAM map doubles the retained RAM; the complete mobile interaction
  // sequence exceeded ten minutes on shared CI. Individual progress stays bounded.
  test.setTimeout(1200000);
  await page.goto('/automatic/');
  expect(await page.locator('script').count()).toBe(0);
  expect(await page.locator('input').count()).toBe(1);
  expect(await page.locator('.scroll-memory').count()).toBe(16627);
  expect(await page.locator('.pipeline-execute').count()).toBe(128);
  const nodes = await page.locator('*').count();
  await toggle(page);
  // No inspection or input during this interval: reads must not be its clock.
  // Full HRAM takes more than 2s for two batches on shared WebKit runners.
  await page.waitForTimeout(10000);
  expect(await ticks(page)).toBeGreaterThanOrEqual(256);
  // Sample coherent committed state while the other bank is being rewritten.
  for (let i=0; i<6; i++) {
    await page.waitForTimeout(150);
    assertCounter(await read(page, counterKeys));
  }
  await expect.poll(() => ticks(page), {timeout:STATE_TIMEOUT}).toBeGreaterThanOrEqual(1024);
  await toggle(page);
  await page.waitForTimeout(150); // Allow an in-flight layout/timeline sample to settle.
  const paused = await read(page, counterKeys);
  assertCounter(paused);
  await expect(page.locator('.auto-paused')).toBeVisible();
  await page.waitForTimeout(300);
  expect(await read(page, counterKeys)).toEqual(paused);
  await page.locator('#power').focus();
  await page.keyboard.press('Space');
  await expect.poll(() => ticks(page), {timeout:STATE_TIMEOUT}).toBeGreaterThan(paused.ticks);
  await toggle(page);
  expect(await page.locator('*').count()).toBe(nodes);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({path:info.outputPath(`automatic-${info.project.name}.png`),fullPage:true});
  await Promise.all([page.waitForNavigation({waitUntil:'load'}), page.locator('.reset').click()]);
  await expect.poll(() => read(page,counterKeys),{timeout:STATE_TIMEOUT}).toEqual({ticks:0,tcycles:0,m65284:0,'div-low':0,pc:256,a:0,m49152:0,halted:0,fault:0});
  await toggle(page);
  await expect.poll(() => ticks(page), {timeout:STATE_TIMEOUT}).toBeGreaterThanOrEqual(256);
  assertCounter(await read(page, counterKeys));
});

for (const [path, expected, message] of [
  ['diagnostic/', {ticks:24,pc:286,a:165,m49152:16,m49153:20,m49154:165,halted:1,fault:0}, '.passed'],
  ['tests/long-loop/', {ticks:304,pc:268,a:100,b:0,f:192,m49152:100,halted:1,fault:0}, '.halt-message'],
  ['tests/register-vram/', {ticks:132,a:170,b:1,c:2,d:4,e:8,h:16,l:32,m32783:170,m49215:170,halted:1,fault:0}, '.halt-message'],
  ['tests/trap/', {ticks:0,pc:256,halted:0,fault:1}, '.fault-message'],
  ['tests/addressing-trap/', {ticks:2,pc:261,a:7,h:1,l:0,halted:0,fault:1}, '.fault-message'],
]) {
  test(`automatic commits the complete stopped state: ${path}`, async ({page}) => {
    await page.goto('/automatic/'+path);
    await toggle(page);
    await expect.poll(() => read(page, Object.keys(expected)), {timeout:STATE_TIMEOUT}).toEqual(expected);
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
  await expect.poll(() => read(page, ['ticks','pc','halted','fault']),{timeout:STATE_TIMEOUT}).toEqual({ticks:86,pc:275,halted:1,fault:0});
  await expect(page.locator('.tile-ready')).toBeVisible();
  const colors = await page.locator('.tile-grid i').evaluateAll(nodes => nodes.map(el => getComputedStyle(el).backgroundColor));
  expect(colors).toHaveLength(64);
  expect(new Set(colors).size).toBe(4);
  await toggle(page);
  expect(await page.locator('.tile-grid i').evaluateAll(nodes => nodes.map(el => getComputedStyle(el).backgroundColor))).toEqual(colors);
  await expect(page.locator('.tile-preview')).toBeVisible();
});

test('automatic pointer loops fill RAM then copy backwards to VRAM across banks', async ({page}) => {
  // Three full-memory batches exceeded the old 60s wall-clock bound on WebKit CI.
  // Keep the exact retired state and every destination byte checked below.
  test.setTimeout(300000);
  await page.goto('/automatic/tests/addressing-loop/'); await toggle(page);
  await expect.poll(() => read(page, ['halted']), {timeout:180000}).toEqual({halted:1});
  expect(await read(page, ['ticks','pc','a','b','h','l','d','e','sp','f','fault'])).toEqual({ticks:344,pc:286,a:48,b:0,h:192,l:47,d:128,e:16,sp:65244,f:192,fault:0});
  const keys = [...Array.from({length:64}, (_,i)=>`m${0xC000+i}`), ...Array.from({length:16}, (_,i)=>`m${0x8000+i}`)];
  const memory = await read(page, keys);
  for (let i=0;i<64;i++) expect(memory[`m${0xC000+i}`]).toBe(i);
  for (let i=0;i<16;i++) expect(memory[`m${0x8000+i}`]).toBe(63-i);
});

test('automatic bookkeeping wraps through 65535 without losing CPU state', async ({page}) => {
  test.setTimeout(180000); // Active read plus native pause each evaluate the expanded banks.
  await page.goto('/automatic/tests/tick-wrap/');
  expect(await ticks(page)).toBe(65472);
  await toggle(page);
  await expect.poll(() => ticks(page), {timeout:STATE_TIMEOUT}).toBeLessThan(4096);
  await toggle(page); await page.waitForTimeout(150);
  assertCounter(await read(page, counterKeys), 65472);
});

test('automatic repeated pause/resume preserves committed state', async ({page}) => {
  // Five complete tap/readback cycles need the same overall budget as above.
  test.setTimeout(1200000);
  await page.goto('/automatic/');
  for (let i=0; i<5; i++) {
    const before = await ticks(page);
    await toggle(page);
    await expect.poll(() => ticks(page), {timeout:STATE_TIMEOUT}).toBeGreaterThan(before);
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
  // Observe after the three-second warning animation. Chromium can block a
  // visibility poll during that transition through the full-memory pipeline.
  await page.waitForTimeout(4000);
  await expect(page.locator('.stall-message')).toBeVisible({timeout:6000});
  expect(await ticks(page)).toBe(0);
  await expect(page.locator('.on-screen')).not.toBeVisible();
});
test('automatic nested calls return after transferring the live stack across banks', async ({page}) => {
  await page.goto('/automatic/tests/stack-continuation/'); await toggle(page);
  const expected={ticks:131,pc:266,b:18,c:52,sp:49216,m49210:14,m49211:1,m49212:52,m49213:18,m49214:9,m49215:1,halted:1,fault:0};
  await expect.poll(() => read(page,Object.keys(expected)),{timeout:STATE_TIMEOUT}).toEqual(expected);
  await page.waitForTimeout(350);
  expect(await read(page,Object.keys(expected))).toEqual(expected);
});
test('automatic rejected PUSH commits only the trap, with no partial stack write', async ({page}) => {
  await page.goto('/automatic/tests/stack-trap/'); await toggle(page);
  const expected={ticks:2,pc:262,b:18,c:52,sp:49153,m49152:0,halted:0,fault:1};
  await expect.poll(() => read(page,Object.keys(expected))).toEqual(expected);
  await expect(page.locator('.fault-message')).toBeVisible();
});
test('automatic stack lab is reachable and finishes with a restored SP', async ({page}) => {
  await page.goto('/automatic/');
  await page.getByRole('link',{name:'Stack lab',exact:true}).click();
  await expect(page).toHaveURL(/\/automatic\/stack\/$/);
  await toggle(page);
  await expect.poll(() => read(page,['ticks','sp','m49154','halted','fault'])).toEqual({ticks:52,sp:49216,m49154:165,halted:1,fault:0});
  await expect(page.locator('.passed')).toBeVisible();
  await page.setViewportSize({width:320,height:844});
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  expect(await page.locator('.cartridges').evaluate(el => el.scrollWidth <= el.clientWidth)).toBe(true);
  await expect(page.locator('.cartridges [aria-current="page"]')).toHaveText('Stack lab');
});

test('automatic continuation carries flags into ADC after a bank transfer',async({page})=>{
  await page.goto('/automatic/tests/alu-carry/');await toggle(page);
  await expect.poll(()=>read(page,['ticks','a','f','m49154','halted','fault']),{timeout:STATE_TIMEOUT}).toEqual({ticks:131,a:0,f:176,m49154:0,halted:1,fault:0});
});

test('automatic retires a whole CB memory instruction before transferring its result',async({page})=>{
  await page.goto('/automatic/tests/cb-carry/');await toggle(page);
  await expect.poll(()=>read(page,['ticks','pc','f','m49152','halted','fault']),{timeout:STATE_TIMEOUT}).toEqual({ticks:130,pc:391,f:48,m49152:192,halted:1,fault:0});
});

test('automatic transfers a live HRAM restart frame and both RAM endpoints',async({page})=>{
  await page.goto('/automatic/tests/high-continuation/');await toggle(page);
  const expected={ticks:133,pc:390,a:3,c:254,f:16,sp:65534,m65408:129,m65532:133,m65533:1,m65534:3,halted:1,fault:0};
  await expect.poll(()=>read(page,Object.keys(expected)),{timeout:STATE_TIMEOUT}).toEqual(expected);
});
test('automatic commits all 127 HRAM bytes before stopping',async({page})=>{
  await page.goto('/automatic/tests/high-fill/');await toggle(page);
  await expect.poll(()=>read(page,['ticks','pc','halted','fault']),{timeout:STATE_TIMEOUT}).toEqual({ticks:129,pc:513,halted:1,fault:0});
  const keys=Array.from({length:127},(_,i)=>`m${0xFF80+i}`);
  expect(await read(page,keys)).toEqual(Object.fromEntries(keys.map(k=>[k,90])));
});

for(const [kind,expected] of [
  ['delay',{ticks:132,tcycles:588,pc:391,b:1,sp:65534,ime:1,'ime-delay':0,'halt-bug':0,m65295:224,m65535:1,m65532:134,m65533:1,halted:1,fault:0}],
  ['service',{ticks:130,tcycles:580,pc:389,b:1,sp:65534,ime:1,'ime-delay':0,'halt-bug':0,m65295:224,m65535:1,m65532:132,m65533:1,halted:1,fault:0}],
  ['bug',{ticks:133,tcycles:568,pc:394,b:2,sp:65534,ime:0,'ime-delay':0,'halt-bug':0,m65295:224,m65535:1,halted:1,fault:0}],
])test(`automatic retains interrupt ${kind} across banks`,async({page})=>{
  await page.goto(`/automatic/tests/interrupt-${kind}/`);await toggle(page);
  await expect.poll(()=>read(page,Object.keys(expected)),{timeout:STATE_TIMEOUT}).toEqual(expected);
  await page.waitForTimeout(300);
  expect(await read(page,Object.keys(expected))).toEqual(expected);
});
test('automatic commits a wakeup from a seeded halted source',async({page})=>{
  await page.goto('/automatic/tests/interrupt-wake/');await toggle(page);
  const expected={ticks:2,pc:257,sp:65534,ime:1,m65295:224,halted:1,fault:0};
  await expect.poll(()=>read(page,Object.keys(expected)),{timeout:STATE_TIMEOUT}).toEqual(expected);
});
