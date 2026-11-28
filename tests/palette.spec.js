const {test,expect}=require('@playwright/test');
const {readState:read}=require('./helpers/state');
const fs=require('node:fs/promises');
const {pathToFileURL}=require('node:url');
const colors=['rgb(177, 195, 126)','rgb(139, 175, 98)','rgb(82, 117, 71)','rgb(49, 69, 44)'];
const ids=[...'0033330003111130312112133111111331211213311221130311113000333300'].map(Number);
const vram=Array.from({length:16},(_,i)=>`m${0x8000+i}`);
async function pixels(page){
  return page.locator('.tile-grid i').evaluateAll(nodes=>nodes.map(el=>{
    const s=getComputedStyle(el);
    return {id:Number(s.getPropertyValue('--color-index')),shade:Number(s.getPropertyValue('--shade')),color:s.backgroundColor};
  }));
}
const image=(palette)=>ids.map(id=>({id,shade:(palette>>(2*id))&3,color:colors[(palette>>(2*id))&3]}));
for(const decoder of ['math','native']){
  test(`all 256 background palettes map four opaque IDs with ${decoder}`,async({page},info)=>{
    test.skip(decoder==='native'&&info.project.name==='webkit-mobile','CSS if() requires Chromium');
    await page.goto(`/tests/palette/colors-${decoder}.html`);
    const actual=await pixels(page);
    const expected=Array.from({length:256},(_,bgp)=>Array.from({length:4},(_,id)=>({id,shade:(bgp>>(2*id))&3,color:colors[(bgp>>(2*id))&3]}))).flat();
    expect(actual).toEqual(expected);
  });
  test(`BGP CPU access and atomic traps with ${decoder}`,async({page},info)=>{
    test.skip(decoder==='native'&&info.project.name==='webkit-mobile','CSS if() requires Chromium');
    await page.goto(`/tests/palette/${decoder}.html`);await page.locator('#power').check();
    const cases=JSON.parse(await fs.readFile('dist/tests/palette/cases.json','utf8'));
    for(const item of cases)expect(await read(page,Object.keys(item.expect),`[id="${item.name}"]`),item.name).toEqual(item.expect);
  });
}
for(const mode of ['portable','automatic','checkpoint','streaming'])test(`palette lab recolors unchanged VRAM in ${mode}`,async({page},info)=>{
  test.skip(mode==='streaming'&&info.project.name==='webkit-mobile','Streaming requires Chromium');
  test.setTimeout(mode==='checkpoint'?900000:600000);
  const prefix=mode==='streaming'?'':`/${mode}`;
  await page.goto(`${prefix}/palette/`);
  await expect(page.getByRole('link',{name:'Palette lab',exact:true})).toHaveAttribute('aria-current','page');
  expect(await read(page,['m65351','ticks'])).toEqual({m65351:0,ticks:0});
  await page.locator('.power-switch').click();
  if(mode==='checkpoint'){
    expect(await read(page,['ticks','m65351','halted','b'])).toEqual({ticks:128,m65351:228,halted:0,b:3});
    expect(await pixels(page)).toEqual(image(228));
    const before=await read(page,['m65351','ticks','pc',...vram]);
    let saved=0;
    while(true){
      const s=await read(page,['copy-index','copy-remaining','bank-phase'],'.checkpoint-select');
      if(!s['copy-remaining'])break;
      expect(saved++).toBeLessThan(256);
      await page.locator(`.bank${1-s['bank-phase']}.copy-${s['copy-index']}`).click();
      await expect.poll(async()=>(await read(page,['copy-remaining'],'.checkpoint-select'))['copy-remaining']).toBe(s['copy-remaining']-1);
      expect(await read(page,Object.keys(before))).toEqual(before);
      if(saved===1){
        await page.locator('.power-switch').click();
        // Manual pause hides the recomputed batch preview; native source and
        // partially copied banks remain. Resume must reconstruct the same tile.
        await expect(page.locator('.tile-preview')).not.toBeVisible();
        await page.locator('.power-switch').click();
        expect(await pixels(page)).toEqual(image(228));
        expect((await read(page,['copy-remaining'],'.checkpoint-select'))['copy-remaining']).toBe(s['copy-remaining']-1);
      }
    }
    await page.locator('.commit-control label').click();
    expect(await read(page,vram)).toEqual(Object.fromEntries(vram.map(k=>[k,before[k]])));
  }
  const expected=mode==='portable'?{ticks:128,m65351:228,halted:0,fault:0,b:3}:{ticks:142,m65351:27,halted:1,fault:0,b:0};
  await expect.poll(()=>read(page,Object.keys(expected)),{timeout:mode==='streaming'?480000:240000,intervals:[1000]}).toEqual(expected);
  expect(await pixels(page)).toEqual(image(mode==='portable'?228:27));
  await page.locator('.debug summary').click();
  await expect(page.locator('.register-m65351')).toBeVisible();
  await page.setViewportSize({width:320,height:844});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  await page.screenshot({path:info.outputPath('palette-lab.png'),fullPage:true});
  if(mode!=='portable'){
    await page.locator('.power-switch').click();
    if(mode==='checkpoint'){
      await expect(page.locator('.tile-preview')).not.toBeVisible();
      await page.locator('.power-switch').click();
    }
    await page.waitForTimeout(200);expect(await pixels(page)).toEqual(image(27));
  }
  await Promise.all([page.waitForNavigation({waitUntil:'load'}),page.locator('.reset').click()]);
  expect(await read(page,['m65351','ticks'])).toEqual({m65351:0,ticks:0});
  expect((await pixels(page)).every(p=>p.id===0&&p.shade===0)).toBe(true);
});
test('downloaded HTML retains palette writes offline without runtime requests',async({page},info)=>{
  // Write BGP; load it back through HL and preserve it in B. Original raw ROM.
  const buffer=Buffer.from([0x3E,0x93,0xE0,0x47,0x21,0x47,0xFF,0x7E,0x47,0x76]);
  await page.goto('/convert/');
  await page.locator('#rom').setInputFiles({name:'palette.bin',mimeType:'application/octet-stream',buffer});
  await page.locator('#format').selectOption('raw');await page.locator('#mode').selectOption('automatic');
  const download=page.waitForEvent('download');await page.locator('button[value="download"]').click();
  const file=info.outputPath('palette.html');await (await download).saveAs(file);
  await page.goto(pathToFileURL(file).href);
  expect(await page.locator('script,link[rel=stylesheet]').count()).toBe(0);
  const requests=[];page.on('request',r=>requests.push(r.url()));
  await page.locator('.power-switch').click();
  await expect.poll(()=>read(page,['m65351','a','b','halted','fault']),{timeout:60000}).toEqual({m65351:147,a:147,b:147,halted:1,fault:0});
  expect(requests).toEqual([]);expect(await page.locator('.passed').count()).toBe(0);
});
