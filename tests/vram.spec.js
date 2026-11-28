const {test,expect}=require('@playwright/test');
const {readState:read}=require('./helpers/state');
const fs=require('node:fs/promises');
const {pathToFileURL}=require('node:url');
const tile=[60,60,126,66,219,165,255,129,219,165,231,153,126,66,60,60];
async function run(page,expected,timeout=180000){
  await page.locator('.power-switch').click();
  await expect.poll(()=>read(page,Object.keys(expected)),{timeout,intervals:[1000,3000]}).toEqual(expected);
}
for(const decoder of ['math','native'])test(`full VRAM CPU access and boundaries with ${decoder}`,async({page},info)=>{
  test.skip(decoder==='native'&&info.project.name==='webkit-mobile','CSS if() requires Chromium');
  test.setTimeout(240000);
  await page.goto(`/tests/video/${decoder}.html`);await page.locator('#power').check();
  const cases=JSON.parse(await fs.readFile('dist/tests/video/cases.json','utf8'));
  for(const item of cases)expect(await read(page,Object.keys(item.expect),`[id="${item.name}"]`),item.name).toEqual(item.expect);
});
for(const mode of ['portable','automatic','checkpoint','streaming'])test(`VRAM lab copies the last page across a ${mode} bank`,async({page},info)=>{
  test.skip(mode==='streaming'&&info.project.name==='webkit-mobile','Streaming requires Chromium');
  test.setTimeout(900000);
  page.setDefaultTimeout(30000);
  page.setDefaultNavigationTimeout(180000);
  await page.goto(mode==='streaming'?'/video/':`/${mode}/video/`);
  const requests=[];page.on('request',request=>requests.push(request.url()));
  await page.locator('.power-switch').click();
  if(mode==='checkpoint'){
    expect(await page.locator('.checkpoint-select').evaluate(el=>{let depth=0;for(;el;el=el.parentElement)depth++;return depth})).toBeLessThan(500);
    const before={ticks:128,pc:317,m32768:0,m40944:60,m40959:60};
    expect(await read(page,Object.keys(before))).toEqual(before);
    let saves=0, point;
    while(true){
      const state=await read(page,['copy-index','copy-remaining','bank-phase'],'.checkpoint-select');
      if(!state['copy-remaining'])break;
      expect(saves++).toBeLessThan(200);
      const label=page.locator(`.bank${1-state['bank-phase']}.copy-${state['copy-index']}`);
      if(saves===1){
        await label.locator('a').focus();await page.keyboard.press('Enter');await page.keyboard.press('Space');
      }else{
        // The single visible save control stays in place. Use native pointer
        // events at its actual position; no forced actions or state writes.
        if(!point){await label.scrollIntoViewIfNeeded();const box=await label.boundingBox();expect(box).not.toBeNull();point={x:box.x+box.width/2,y:box.y+box.height/2};}
        if(info.project.name.endsWith('mobile'))await page.touchscreen.tap(point.x,point.y);else await page.mouse.click(point.x,point.y);
      }
      await expect.poll(async()=>(await read(page,['copy-remaining'],'.checkpoint-select'))['copy-remaining']).toBe(state['copy-remaining']-1);
      expect(await read(page,Object.keys(before))).toEqual(before);
    }
    await page.locator('.commit-control label').click();
  }
  const expected=mode==='portable'?{ticks:128,pc:317,halted:0,fault:0}:{ticks:212,pc:332,halted:1,fault:0};
  await expect.poll(()=>read(page,Object.keys(expected)),{timeout:300000,intervals:[1000,5000]}).toEqual(expected);
  const keys=Array.from({length:16},(_,i)=>'m'+(0x9FF0+i));
  expect(await read(page,keys)).toEqual(Object.fromEntries(keys.map((k,i)=>[k,tile[i]])));
  const visible=keys.map((_,i)=>'m'+(0x8000+i));
  expect(await read(page,visible)).toEqual(Object.fromEntries(visible.map((k,i)=>[k,mode==='portable'?0:tile[i]])));
  expect(requests).toEqual([]);expect(await page.locator('script').count()).toBe(0);
  expect(await page.locator('.cartridges [aria-current=page]').textContent()).toBe('VRAM');
  await page.setViewportSize({width:320,height:844});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  if(mode==='automatic')await page.screenshot({path:info.outputPath('video-lab.png'),fullPage:true});
});
test('all 8192 VRAM bytes survive automatic banks and every page write',async({page})=>{
  test.setTimeout(900000);
  await page.goto('/tests/video/all-bytes/');
  await run(page,{ticks:133,pc:521,sp:8240,a:32,b:17,c:32,halted:1,fault:0},600000);
  const expected={m49152:165,m57343:90};
  for(let i=0;i<8192;i++)expected['m'+(32768+i)]=(i*43+(i>>8)*31+7)&255;
  for(let p=0;p<32;p++){expected['m'+(32768+p*256+127)]=p+17;expected['m'+(32768+p*256+128)]=p+1;}
  expect(await read(page,Object.keys(expected))).toEqual(expected);
  expect(await page.locator('.scroll-memory').count()).toBe(16627);
});
for(const seed of [0,0x3412])test(`VRAM reactivates after returning to seed ${seed}`,async({page})=>{
  test.setTimeout(900000);await page.goto(`/tests/video/reactivate-${seed}/`);
  await run(page,{ticks:516,pc:792,sp:43981,a:171,b:205,m40958:205,m40959:171,halted:1,fault:0},600000);
});
test('downloaded VRAM lab executes offline with the math decoder',async({page},info)=>{
  test.setTimeout(240000);
  // A small program crosses 8FFF/9000 and fetches its result back from VRAM.
  await page.goto('/convert/');
  await page.locator('#rom').setInputFiles({name:'vram.bin',mimeType:'application/octet-stream',buffer:Buffer.from([0x31,0x34,0x12,0x08,0xFF,0x8F,0xFA,0,0x90,0x76])});
  await page.locator('#format').selectOption('raw');await page.locator('#mode').selectOption('portable');
  const pending=page.waitForEvent('download');await page.locator('button[value=download]').click();
  const download=await pending;const file=info.outputPath('vram.html');await download.saveAs(file);
  // Disable the optional acceleration before loading, never mutate runtime state.
  await fs.writeFile(file,(await fs.readFile(file,'utf8')).replaceAll('(width:if(style(--x:1):1px;else:2px))','(unknown-property: unsupported)'));
  const requests=[];page.on('request',r=>{if(/^https?:/.test(r.url()))requests.push(r.url())});
  await page.goto(pathToFileURL(file).href);
  await run(page,{ticks:4,pc:266,sp:4660,a:18,m36863:52,m36864:18,halted:1,fault:0});
  expect(requests).toEqual([]);expect(await page.locator('script,.passed').count()).toBe(0);
});
