const {test,expect}=require('@playwright/test');
const {readState:read}=require('./helpers/state');
const fs=require('node:fs/promises');
for(const decoder of ['math','native'])test(`LCD boundary contracts with ${decoder} decoder`,async({page},info)=>{
  test.skip(decoder==='native'&&info.project.name==='webkit-mobile','CSS if() requires Chromium');
  await page.goto(`/tests/lcd/${decoder}.html`);
  await page.locator('#power').check();
  const cases=JSON.parse(await fs.readFile('dist/tests/lcd/cases.json','utf8'));
  for(const item of cases)expect(await read(page,Object.keys(item.expect),`[id="${item.name}"]`),item.name).toEqual(item.expect);
});
for(const mode of ['automatic','checkpoint','streaming'])test(`LCD lab wakes HALT through STAT in ${mode}`,async({page},info)=>{
  test.skip(mode==='streaming'&&info.project.name==='webkit-mobile','Streaming requires Chromium');
  // Streaming commits over 200 individual CPU/idle steps (~114s locally).
  // Leave progress headroom on shared runners without reducing assertions.
  test.setTimeout(mode==='automatic'?180000:300000);
  const prefix=mode==='streaming'?'':`/${mode}`;
  await page.goto(`${prefix}/lcd/`);
  // Deliberately inspect accessibility before Run: Chromium used to cache
  // group 0 as hidden when the manual save controls were still powered off.
  await expect(page.getByRole('link',{name:'LCD timing',exact:true})).toHaveAttribute('aria-current','page');
  await page.locator('.power-switch').click();
  if(mode==='checkpoint')await copy(page);
  const expected={ticks:26,tcycles:236,a:165,b:3,sp:65534,m49154:165,m65344:0,m65345:192,m65348:0,m65349:2,'lcd-line':0,'lcd-dot':0,'lcd-stat':0,halted:1,fault:0};
  await expect.poll(()=>read(page,Object.keys(expected)),{timeout:mode==='streaming'?240000:120000,intervals:[1000]}).toEqual(expected);
  await expect(page.locator('.passed')).toBeVisible();
  await page.locator('.debug summary').click();
  await page.setViewportSize({width:320,height:844});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  await page.screenshot({path:info.outputPath('lcd-lab.png'),fullPage:true});
  await Promise.all([page.waitForNavigation({waitUntil:'load'}),page.locator('.reset').click()]);
  expect(await read(page,['ticks','m65344','m65345','lcd-dot'])).toEqual({ticks:0,m65344:0,m65345:132,'lcd-dot':0});
});
async function copy(page){
  await expect(page.locator('.checkpoint-controls')).toBeVisible();
  const keys=['ticks','tcycles','pc','halted','m65344','m65345','m65348','m65349','lcd-line','lcd-dot','lcd-stat','m65295'];
  const before=await read(page,keys);
  let count=0;
  while(true){
    const state=await read(page,['copy-index','copy-remaining','bank-phase'],'.checkpoint-select');
    if(!state['copy-remaining'])break;
    expect(count++).toBeLessThan(200); // This fixture changes only a small number of bits.
    await page.locator(`.bank${1-state['bank-phase']}.copy-${state['copy-index']}`).click();
    await expect.poll(async()=>(await read(page,['copy-remaining'],'.checkpoint-select'))['copy-remaining']).toBe(state['copy-remaining']-1);
    expect(await read(page,keys)).toEqual(before);
    if(count===1){
      await page.locator('.power-switch').click();await page.locator('.power-switch').click();
      await expect.poll(async()=>(await read(page,['copy-remaining'],'.checkpoint-select'))['copy-remaining']).toBe(state['copy-remaining']-1);
    }
  }
  await page.locator('.commit-control label').click();
}
test('compatible LCD lab stops while waiting for scanline 2',async({page})=>{
  await page.goto('/portable/lcd/');await page.locator('.power-switch').click();
  expect(await read(page,['halted','fault','m65344','m65348','m65349','m49154'])).toEqual({halted:1,fault:0,m65344:128,m65348:1,m65349:2,m49154:0});
  await expect(page.locator('.timer-message')).toBeVisible();
  await expect(page.locator('.lcd-note')).toContainText('multiple batches');
});
for(const mode of ['automatic','checkpoint'])test(`VBlank request crosses ${mode} bank`,async({page})=>{
  test.setTimeout(240000);
  await page.goto(`/${mode}/tests/lcd-boundary/`);await page.locator('.power-switch').click();
  if(mode==='checkpoint'){
    const expected={ticks:0,tcycles:0,halted:1,'lcd-line':143,'lcd-dot':452,m65348:143,m65345:128,m65295:224};
    expect(await read(page,Object.keys(expected))).toEqual(expected);
    await copy(page);
  }
  const expected={ticks:7,tcycles:84,a:165,b:1,sp:65534,m49154:165,m65295:224,m65344:0,m65345:128,'lcd-line':0,'lcd-dot':0,'lcd-stat':0,halted:1,fault:0};
  await expect.poll(()=>read(page,Object.keys(expected)),{timeout:90000,intervals:[1000]}).toEqual(expected);
  await page.waitForTimeout(200);expect(await read(page,Object.keys(expected))).toEqual(expected);
});
test('LCD continues with IE off and pause freezes its retained phase',async({page})=>{
  await page.goto('/automatic/tests/lcd-idle/');await page.locator('.power-switch').click();
  await page.waitForTimeout(3500); // No script inspection supplies a clock.
  await page.locator('.power-switch').click();
  const keys=['ticks','tcycles','clocked','halted','fault','lcd-line','lcd-dot','lcd-stat','m65345','m65348','m65295'];
  const paused=await read(page,keys);
  expect(paused).toMatchObject({ticks:0,tcycles:0,clocked:1,halted:1,fault:0});
  expect(paused['lcd-line']*456+paused['lcd-dot']).toBeGreaterThan(0);
  await expect(page.locator('.startup-screen')).not.toBeVisible();
  await page.waitForTimeout(300);expect(await read(page,keys)).toEqual(paused);
  await page.locator('.power-switch').click();
  await expect.poll(async()=>{const s=await read(page,['lcd-line','lcd-dot']);return s['lcd-line']*456+s['lcd-dot'];}).not.toBe(paused['lcd-line']*456+paused['lcd-dot']);
});

test('downloaded HTML polls LY offline without runtime requests',async({page},info)=>{
  const {pathToFileURL}=require('node:url');
  // Turn on LCD, poll line 1, preserve it in B, turn off LCD, then HALT.
  const buffer=Buffer.from([0x3E,0x80,0xE0,0x40,0xF0,0x44,0xFE,1,0x20,0xFA,0x47,0xAF,0xE0,0x40,0x78,0x76]);
  await page.goto('/convert/');
  await page.locator('#rom').setInputFiles({name:'lcd-poll.bin',mimeType:'application/octet-stream',buffer});
  await page.locator('#format').selectOption('raw');await page.locator('#mode').selectOption('portable');
  const downloading=page.waitForEvent('download');await page.locator('button[value="download"]').click();
  const path=info.outputPath('lcd.html');await (await downloading).saveAs(path);
  await page.goto(pathToFileURL(path).href);
  expect(await page.locator('script,link[rel=stylesheet]').count()).toBe(0);
  const requests=[];page.on('request',r=>requests.push(r.url()));
  await page.locator('.power-switch').click();
  expect(await read(page,['a','b','m65344','m65348','halted','fault'])).toEqual({a:1,b:1,m65344:0,m65348:0,halted:1,fault:0});
  expect(await page.locator('.passed').count()).toBe(0);expect(requests).toEqual([]);
});

test('manual bank retains a high STAT signal without retriggering',async({page})=>{
  test.setTimeout(180000);
  await page.goto('/checkpoint/tests/lcd-blocked/');await page.locator('.power-switch').click();
  const before={ticks:5,halted:1,m65295:224,'lcd-line':145,'lcd-dot':76,'lcd-stat':1};
  expect(await read(page,Object.keys(before))).toEqual(before);
  await copy(page);
  const after={ticks:5,halted:1,fault:0,m65295:224,'lcd-line':146,'lcd-dot':132,'lcd-stat':1};
  expect(await read(page,Object.keys(after))).toEqual(after);
});
