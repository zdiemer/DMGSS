const {test,expect}=require('@playwright/test');
const {pathToFileURL}=require('node:url');
const fs=require('node:fs/promises');
const read=(page,keys)=>page.locator('.machine').evaluate((el,keys)=>{const s=getComputedStyle(el);return Object.fromEntries(keys.map(k=>[k,Number(s.getPropertyValue('--'+k))]))},keys);
async function upload(page,buffer,{format='raw',mode='portable',name='test.bin',delivery='open'}={}){
  await page.goto('/convert/');
  await page.locator('#rom').setInputFiles({name,mimeType:'application/octet-stream',buffer});
  await page.locator('#format').selectOption(format);
  await page.locator('#mode').selectOption(mode);
  await page.locator(`button[value="${delivery}"]`).click();
}
const halt=(page,timeout=15000)=>expect.poll(()=>read(page,['halted','fault']),{timeout}).toEqual({halted:1,fault:0});
for(const mode of ['portable','automatic','checkpoint','streaming']){
  test(`converter sample executes in ${mode} with no runtime requests`,async({page},info)=>{
    test.skip(mode==='streaming'&&info.project.name==='webkit-mobile','Streaming remains Chromium-only');
    const buffer=await (await page.request.get('/convert/sample.gb')).body();
    await upload(page,buffer,{format:'gb',mode,name:'sample.gb'});
    await expect(page.locator('.conversion-caveat')).toContainText('Python outside the browser');
    expect(await page.locator('script').count()).toBe(0);
    expect(await page.locator('link[rel=stylesheet]').count()).toBe(0);
    // Streaming resolves its first animation bank after power-on.
    expect(await read(page,mode==='streaming'?['ticks']:['ticks','pc'])).toEqual(mode==='streaming'?{ticks:0}:{ticks:0,pc:256});
    const requests=[];page.on('request',r=>requests.push(r.url()));
    await page.locator('.power-switch').click();await halt(page,20000);
    expect(await read(page,['ticks','pc','sp','a','b','c','m49154','m49214','m49215'])).toEqual({ticks:53,pc:358,sp:49216,a:165,b:0,c:0,m49154:165,m49214:89,m49215:1});
    await expect(page.locator('.halt-message')).toHaveText('HALTED');
    expect(requests).toEqual([]);
    await page.locator('.reset').click();
    expect(requests.some(url=>url.endsWith('/convert/'))).toBe(true);
    // Streaming resolves its first animation bank after power-on.
    expect(await read(page,mode==='streaming'?['ticks']:['ticks','pc'])).toEqual(mode==='streaming'?{ticks:0}:{ticks:0,pc:256});
  });
}
test('converter maps cartridge offsets 0000 through 7FFF and zero padding',async({page})=>{
  const rom=Buffer.alloc(32768);rom[0]=77;rom[32767]=88;
  rom.set([0xC3,0,0x40],0x100);
  rom.set([0xFA,0,0,0xEA,0,0xC0,0xFA,0xFF,0x7F,0xEA,1,0xC0,0xFA,0,0x20,0xEA,2,0xC0,0x76],0x4000);
  await upload(page,rom,{format:'gb',name:'addresses.gb'});
  await page.locator('.power-switch').click();await halt(page);
  expect(await read(page,['ticks','pc','m49152','m49153','m49154'])).toEqual({ticks:8,pc:16403,m49152:77,m49153:88,m49154:0});
});
test('converter accepts the complexity limit with FF padding and resets within the request limit',async({page})=>{
  const rom=Buffer.alloc(32768,255);
  rom.set([0xFA,0,0x20,0xEA,0,0xC0,0x76],0x100);
  for(const address of [0x143,0x147,0x148,0x149])rom[address]=0;
  rom.fill(0,0x1000,0x1000+1013); // Exactly 1024 bytes differ from FF.
  await upload(page,rom,{format:'gb',name:'padded.gb'});
  await page.locator('.power-switch').click();await halt(page);
  expect(await read(page,['ticks','m49152'])).toEqual({ticks:3,m49152:255});
  const request=page.waitForRequest(r=>r.method()==='POST');
  await page.locator('.reset').click();
  expect((await request).postDataBuffer().length).toBeLessThanOrEqual(65536);
  expect(await read(page,['ticks','pc'])).toEqual({ticks:0,pc:256});
});
test('converter automatic raw program continues beyond a batch',async({page})=>{
  await upload(page,Buffer.from([0xFA,0,0xC0,0x3C,0xEA,0,0xC0,0x18,0xF7]),{mode:'automatic'});
  await page.locator('.power-switch').click();
  await expect.poll(async()=> (await read(page,['ticks'])).ticks,{timeout:15000}).toBeGreaterThanOrEqual(256);
  await page.locator('.power-switch').click();await page.waitForTimeout(150);
  const state=await read(page,['ticks','pc','m49152','fault']);
  expect(state.pc).toBe(256);expect(state.fault).toBe(0);expect(state.m49152).toBe((state.ticks/4)%256);
});
test('converter preserves traps instead of pretending an imported ROM passes',async({page})=>{
  await upload(page,Buffer.from([0x21,0,1,0x3E,7,0x22]));await page.locator('.power-switch').click();
  await expect(page.locator('.fault-message')).toBeVisible();
  expect(await read(page,['ticks','pc','h','l','a','fault'])).toEqual({ticks:2,pc:261,h:1,l:0,a:7,fault:1});
});
test('converter download is one offline HTML file and metadata stays text',async({page},info)=>{
  await page.goto('/convert/');
  await page.locator('#rom').setInputFiles({name:'<b>original</b>.bin',mimeType:'application/octet-stream',buffer:Buffer.from([0x3E,42,0xEA,0,0xC0,0x76])});
  await page.locator('#format').selectOption('raw');
  const promise=page.waitForEvent('download');
  await page.locator('button[value=download]').click();
  const download=await promise;
  const file=info.outputPath('converted.html');await download.saveAs(file);
  const document=await fs.readFile(file,'utf8');
  expect(document).not.toContain('<script');expect(document).not.toContain('<link');
  expect(document).not.toContain('<b>original</b>');expect(document).not.toContain('action="/convert/"');
  const requests=[];page.on('request',r=>{if(/^https?:/.test(r.url()))requests.push(r.url())});
  await page.goto(pathToFileURL(file).href);
  await page.locator('.power-switch').click();await halt(page);
  expect(await read(page,['ticks','m49152'])).toEqual({ticks:3,m49152:42});
  await page.locator('.reset').click();
  expect(await read(page,['ticks'])).toEqual({ticks:0});expect(requests).toEqual([]);
});
test('converter rejects banking and exposes the caveat on mobile',async({page},info)=>{
  const rom=Buffer.alloc(32768);rom[0x147]=1;
  await upload(page,rom,{format:'gb',name:'banked.gb'});
  await expect(page.getByRole('alert')).toContainText('ROM ONLY');
  await expect(page.locator('.caveat')).toContainText('Python on the server');
  await page.setViewportSize({width:320,height:844});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  await page.screenshot({path:info.outputPath('loader.png'),fullPage:true});
});
