const {readState}=require('./helpers/state');
const {test,expect}=require('@playwright/test');
const {pathToFileURL}=require('node:url');
const fs=require('node:fs/promises');
// Worst-case dense documents are several MiB; the isolated probes decode over
// 750 addresses. Give parsing/readback headroom on shared browser runners.
test.describe.configure({timeout:120000});
const read = readState;
async function upload(page,buffer,mode='portable',format='gb',delivery='open'){
  await page.goto('/convert/');
  await page.locator('#rom').setInputFiles({name:format==='gb'?'dense.gb':'dense.bin',mimeType:'application/octet-stream',buffer});
  await page.locator('#format').selectOption(format);await page.locator('#mode').selectOption(mode);
  if(delivery==='open')await Promise.all([page.waitForNavigation({waitUntil:'load'}),page.locator('button[value="open"]').click()]);
  else {const download=page.waitForEvent('download');await page.locator('button[value="download"]').click();return download;}
}
const sample=async page=>(await page.request.get('/convert/dense.gb')).body();
const stopped=async(page,expected,timeout=45000)=>{
  const state={...expected,halted:1,fault:0};
  await expect.poll(()=>read(page,Object.keys(state)),{timeout,intervals:[1000,5000]}).toEqual(state);
};
for(const mode of ['math','native'])test(`dense ROM lookup decodes page edges and packed pairs with ${mode}`,async({page},info)=>{
  test.skip(mode==='native'&&info.project.name==='webkit-mobile','Native CSS if() is Chromium-only');
  const data=await fs.readFile('dist/tests/rom-lookup/data.bin');
  expect(data.length).toBe(32768);
  await page.goto(`/tests/rom-lookup/${mode}.html`);
  const results=await page.locator('.case').evaluateAll(nodes=>nodes.map(el=>[Number(el.dataset.address),Number(getComputedStyle(el).getPropertyValue('--result'))]));
  expect(results.length).toBeGreaterThan(750);
  for(const [address,value] of results)expect(value,`address ${address}`).toBe(address>=0&&address<data.length?data[address]:address===32768?17:address===65535?203:255);
});
for(const mode of ['portable','automatic','checkpoint'])test(`dense ROM executes in ${mode}`,async({page})=>{
  test.setTimeout(90000);
  await upload(page,await sample(page),mode);
  expect(await page.locator('script').count()).toBe(0);
  const requests=[];page.on('request',r=>requests.push(r.url()));
  await page.locator('.power-switch').click();
  // The final equal CP sets both Z and N; LD/HALT preserve those flags.
  await stopped(page,{ticks:31,tcycles:332,pc:405,a:165,f:192,m49154:165});
  expect(await page.locator('.passed').count()).toBe(0);expect(requests).toEqual([]);
  await Promise.all([page.waitForNavigation({waitUntil:'load'}),page.locator('.reset').click()]);
  expect(await read(page,['ticks','m49154'])).toEqual({ticks:0,m49154:0});
});
test('dense streaming conversion gives an actionable mode error',async({page})=>{
  await upload(page,await sample(page),'streaming');
  await expect(page.getByRole('alert')).toContainText('Dense ROMs require Compatible, Automatic or Manual checkpoints');
  expect(await page.locator('.machine').count()).toBe(0);
});
test('dense page crossing covers immediate fetch, post-increment and both word lanes',async({page})=>{
  const rom=await sample(page);rom.set([0xC3,0xFF,1],0x100);
  rom.set([0x01,0x34,0x12,0x21,0xFF,0x1F,0x2A,0x47,0x2A,0x4F,0x31,0xFF,0x1F,0xD1,
    0x3E,0x99,0xEA,0,0x80,0x31,0xFF,0x7F,0xC1,0x76],0x1FF);
  await upload(page,rom);await page.locator('.power-switch').click();
  await stopped(page,{ticks:14,pc:535,a:153,b:153,c:42,d:254,e:1,h:32,l:1,sp:32769,m32768:153});
});
test('dense opcode fetch crosses ROM into executable VRAM',async({page})=>{
  const rom=await sample(page);
  rom.set([0x3E,7,0xEA,0,0x80,0x3E,0x76,0xEA,1,0x80,0x3E,0x81,0xC3,0xFF,0x7F],0x100);rom[32767]=0xCB;
  await upload(page,rom);await page.locator('.power-switch').click();
  await stopped(page,{ticks:8,pc:32770,a:3,f:16,m32768:7,m32769:118});
});
test('dense operand fetch wraps from IE into ROM zero',async({page})=>{
  const rom=await sample(page);rom[0]=42;rom[1]=0x76;
  rom.set([0x3E,0x3E,0xE0,0xFF,0xC3,0xFF,0xFF],0x100);
  await upload(page,rom);await page.locator('.power-switch').click();
  await stopped(page,{ticks:5,pc:2,a:42,m65535:62});
});
test('dense ROM writes still trap atomically',async({page})=>{
  const rom=await sample(page);rom.set([0x21,0,0x40,0x3E,7,0x22],0x100);
  await upload(page,rom);await page.locator('.power-switch').click();
  expect(await read(page,['ticks','pc','h','l','a','fault'])).toEqual({ticks:2,pc:261,h:64,l:0,a:7,fault:1});
});
test('dense sample detects altered ROM data',async({page})=>{
  const rom=await sample(page);rom[0]=1; // First CP expects zero; take failure branch.
  await upload(page,rom);await page.locator('.power-switch').click();
  await stopped(page,{ticks:7,tcycles:80,pc:411,a:255,f:64,m49154:255});
  expect(await page.locator('.passed').count()).toBe(0);
});
test('dense repeated pages preserve byte selection',async({page})=>{
  const rom=Buffer.from(Array.from({length:32768},(_,i)=>i&255));
  for(const address of [0x143,0x147,0x148,0x149])rom[address]=0;
  rom.set([0xC3,0,0x40],0x100);
  rom.set([0xFA,0xAB,0x12,0xEA,0,0xC0,0xFA,0xFF,0x7F,0xEA,1,0xC0,0x76],0x4000);
  await upload(page,rom);await page.locator('.power-switch').click();
  await stopped(page,{ticks:6,pc:16397,a:255,m49152:171,m49153:255});
});
for(const size of [4095,4096])test(`dense raw ${size}-byte range rejects its missing operand`,async({page})=>{
  const raw=(await sample(page)).subarray(0,size);const last=256+size-1;
  raw.set([0xC3,last&255,last>>8]);raw[size-1]=0x3E;
  await upload(page,raw,'portable','raw');await page.locator('.power-switch').click();
  expect(await read(page,['ticks','pc','a','fault'])).toEqual({ticks:1,pc:last,a:0,fault:1});
});
for(const mode of ['automatic','checkpoint'])test(`dense execution continues across a ${mode} bank`,async({page},info)=>{
  test.setTimeout(900000);
  const rom=await sample(page);
  // Manual input invalidates the pipeline on every saved bit. Use dense but
  // repeating data pages for this storage check; the isolated lookup probes
  // and other modes cover the full set of distinct worst-case pages.
  if(mode==='checkpoint')for(let i=0x200;i<rom.length;i++)rom[i]=i&255;
  rom.fill(0,0x150,0x1CF);rom.set([0xC3,0xFF,0x3F],0x1CF);
  rom.set([0x3E,42,0xEA,0,0xC0,0x76],0x3FFF);
  await upload(page,rom,mode);await page.locator('.power-switch').click();
  if(mode==='checkpoint'){
    expect(await read(page,['ticks','pc'])).toEqual({ticks:128,pc:463});
    let saved=0;
    while(true){
      const before=await read(page,['copy-index','copy-remaining','bank-phase'],'.checkpoint-select');
      if(!before['copy-remaining'])break;
      expect(saved++).toBeLessThan(132522);
      const label=page.locator(`.bank${1-before['bank-phase']}.copy-${before['copy-index']}`);
      if(info.project.name.endsWith('mobile'))await label.tap();else await label.click();
      await expect.poll(async()=>(await read(page,['copy-remaining'],'.checkpoint-select'))['copy-remaining']).toBe(before['copy-remaining']-1);
      expect(await read(page,['ticks','pc','m49152'])).toEqual({ticks:128,pc:463,m49152:0});
    }
    await page.locator('.commit-control label').click();
  }
  await stopped(page,{ticks:132,tcycles:568,pc:16389,a:42,m49152:42},90000);
});
test('dense downloaded HTML runs offline without requests',async({page},info)=>{
  test.setTimeout(90000);
  const download=await upload(page,await sample(page),'automatic','gb','download');
  const file=info.outputPath('dense.html');await download.saveAs(file);
  const html=await fs.readFile(file,'utf8');expect(html).not.toContain('<script');expect(html).not.toContain('<link');
  expect(Buffer.byteLength(html)).toBeLessThan(24*1024*1024);
  const requests=[];page.on('request',r=>{if(/^https?:/.test(r.url()))requests.push(r.url())});
  await page.goto(pathToFileURL(file).href);await page.locator('.power-switch').click();
  await stopped(page,{ticks:31,pc:405,a:165,m49154:165});
  await Promise.all([page.waitForNavigation({waitUntil:'load'}), page.locator('.reset').click()]);expect(await read(page,['ticks'])).toEqual({ticks:0});
  expect(requests).toEqual([]);
});
