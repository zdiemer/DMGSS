const {test,expect}=require('@playwright/test');
const {readState:read}=require('./helpers/state');
const {pathToFileURL}=require('node:url');
function cartridge(size=65536,code=[0x76]){
  const rom=Buffer.alloc(size);rom.set([0xC3,0x50,1],0x100);
  rom[0x147]=1;rom[0x148]=Math.log2(size/32768);rom.set(code,0x150);return rom;
}
async function upload(page,rom,mode='portable',download=false){
  await page.goto('/convert/');
  await page.locator('#rom').setInputFiles({name:'mbc1.gb',mimeType:'application/octet-stream',buffer:rom});
  await page.locator('#mode').selectOption(mode);
  if(download){const event=page.waitForEvent('download');await page.locator('button[value=download]').click();return event;}
  await Promise.all([page.waitForNavigation({waitUntil:'load'}),page.locator('button[value=open]').click()]);
}
async function run(page,expected){
  await page.locator('.power-switch').click();
  await expect.poll(()=>read(page,Object.keys(expected)),{timeout:90000,intervals:[1000,3000]}).toEqual(expected);
}
for(const mode of ['portable','automatic','checkpoint','streaming'])test(`MBC1 sample switches code and data in ${mode}`,async({page},info)=>{
  test.skip(mode==='streaming'&&info.project.name==='webkit-mobile','Streaming remains Chromium-only');
  if(mode==='checkpoint')test.setTimeout(600000); // Upload and native reset each parse the full Manual bank.
  const rom=await (await page.request.get('/convert/mbc1.gb')).body();await upload(page,rom,mode);
  const requests=[];page.on('request',r=>requests.push(r.url()));
  await run(page,{ticks:13,pc:361,a:17,m49152:42,m49153:17,'mbc-bank':0,halted:1,fault:0});
  expect(requests).toEqual([]);expect(await page.locator('script,.passed').count()).toBe(0);
  await Promise.all([page.waitForNavigation({waitUntil:'load'}),page.locator('.reset').click()]);
  expect(await read(page,['ticks','mbc-bank'])).toEqual({ticks:0,'mbc-bank':0});
});
for(const mode of ['automatic','checkpoint'])test(`MBC1 selected bank survives ${mode} continuation`,async({page},info)=>{
  test.setTimeout(900000);
  const rom=cartridge(65536,[0x3E,2,0xEA,0,0x20,...Array(125).fill(0),0xC3,0,0x40]);
  // JP at 0100 + bank setup + 125 NOPs = 128. Bank 2 switches
  // to bank 3, whose instruction at the next logical PC must be fetched.
  rom.set([0x3E,3,0xEA,0,0x20],0x8000);
  rom.set([0x3E,42,0xEA,0,0xC0,0x76],0xC005);
  await upload(page,rom,mode);await page.locator('.power-switch').click();
  if(mode==='checkpoint'){
    const expected={ticks:128,pc:466,'mbc-bank':2};expect(await read(page,Object.keys(expected))).toEqual(expected);
    let saved=0;
    while(true){
      const state=await read(page,['copy-index','copy-remaining','bank-phase'],'.checkpoint-select');
      if(!state['copy-remaining'])break;
      expect(saved++).toBeLessThan(100);
      const target=page.locator(`.bank${1-state['bank-phase']}.copy-${state['copy-index']}`);
      if(info.project.name.endsWith('mobile'))await target.tap();else await target.click();
      await expect.poll(async()=>(await read(page,['copy-remaining'],'.checkpoint-select'))['copy-remaining']).toBe(state['copy-remaining']-1);
      expect(await read(page,Object.keys(expected))).toEqual(expected);
    }
    await page.locator('.commit-control label').click();
  }
  await expect.poll(()=>read(page,['ticks','pc','mbc-bank','m49152','halted','fault']),{timeout:120000}).toEqual({ticks:134,pc:16395,'mbc-bank':3,m49152:42,halted:1,fault:0});
});
test('MBC1 download runs offline and reset restores the initial bank',async({page},info)=>{
  const rom=cartridge(131072,[0x3E,7,0xEA,0,0x20,0xFA,0xFF,0x7F,0x76]);rom[rom.length-1]=123;
  const download=await upload(page,rom,'automatic',true);const file=info.outputPath('mbc1.html');await download.saveAs(file);
  const requests=[];page.on('request',r=>{if(/^https?:/.test(r.url()))requests.push(r.url())});await page.goto(pathToFileURL(file).href);
  await run(page,{ticks:5,a:123,'mbc-bank':7,halted:1,fault:0});
  await Promise.all([page.waitForNavigation({waitUntil:'load'}),page.locator('.reset').click()]);
  expect(await read(page,['ticks','mbc-bank'])).toEqual({ticks:0,'mbc-bank':0});expect(requests).toEqual([]);
});
for(const [name,code,bank] of [
  ['SP low then high',[0x31,2,3,0x08,0,0x20],3],
  ['PUSH high then low',[0x31,2,0x20,0x01,2,3,0xC5],2],
  ['word enters bank register',[0x31,2,3,0x08,0xFF,0x1F],3],
  ['word leaves bank register',[0x31,2,3,0x08,0xFF,0x3F],2],
])test(`MBC1 ${name}`,async({page})=>{
  const rom=cartridge(131072,[...code,0xFA,0,0x41,0x76]);
  for(let i=0;i<8;i++)rom[i*16384+256]=i;
  // Restore entry after bank markers.
  rom.set([0xC3,0x50,1],0x100);
  await upload(page,rom);await run(page,{a:bank,'mbc-bank':bank,halted:1,fault:0});
});
test('MBC1 fetch and word read cross the fixed/switched bank boundary',async({page})=>{
  const rom=cartridge(131072,[0x3E,7,0xEA,0,0x20,0x31,0xFF,0x3F,0xD1,0xC3,0xFF,0x3F]);
  rom[0x3FFF]=0x3E;rom.set([42,0x76],7*16384);
  await upload(page,rom);await run(page,{ticks:8,pc:16386,a:42,d:42,e:62,sp:16385,halted:1,fault:0});
});
test('MBC1 rejected word write preserves bank and stack atomically',async({page})=>{
  // FEFF is invalid, so neither lane of the attempted stack write commits.
  const rom=cartridge(65536,[0x3E,2,0xEA,0,0x20,0x31,1,0xFF,0xC5]);
  await upload(page,rom);await run(page,{ticks:4,pc:344,sp:65281,'mbc-bank':2,fault:1});
});

const fs=require('node:fs');
for(const [size,file] of [[65536,'rom_512kb'],[131072,'rom_1Mb']])for(const mode of [0,1])
test(`MBC1 ${size}-byte bank map matches upstream in mode ${mode}`,async({page})=>{
  test.setTimeout(600000);
  const source=fs.readFileSync(`${__dirname}/vendor/mooneye/mbc1/${file}.s`,'utf8');
  const expected=[...source.matchAll(/^\.db\s+([0-9 ]+)$/gm)].flatMap(m=>m[1].trim().split(/\s+/).map(Number));
  expect(expected).toHaveLength(384);
  for(let start=0;start<128;start+=4){
    const code=[0x3E,mode,0xEA,0,0x60];
    const values={halted:1,fault:0};
    for(let i=0;i<4;i++){
      const bank=start+i;
      code.push(0x3E,bank>>5,0xEA,0,0x40,0x3E,bank&31,0xEA,0,0x20,
        0xFA,0,0,0xEA,i*2,0xC0,0xFA,0,0x40,0xEA,i*2+1,0xC0);
      values[`m${49152+i*2}`]=expected[mode*128+bank];
      values[`m${49153+i*2}`]=expected[256+bank];
    }
    code.push(0x76);const rom=cartridge(size,code);
    for(let bank=0;bank<size/16384;bank++)rom[bank*16384]=bank;
    await upload(page,rom);await run(page,values);
  }
});
for(const execution of ['portable','automatic','checkpoint'])test(`dense 128 KiB MBC1 data and native reset in ${execution}`,async({page})=>{
  test.setTimeout(execution==='checkpoint'?900000:300000);
  // All physical pages differ; values are data, including unreachable bytes.
  const rom=Buffer.from(Array.from({length:131072},(_,i)=>(i*73 ^ (i>>5)*29 ^ ((i*i)>>9))&255));
  rom.fill(0,0x100,0x150);rom.set([0xC3,0x50,1],0x100);rom[0x147]=1;rom[0x148]=2;
  rom.set([0x3E,7,0xEA,0,0x20,0xFA,0xFF,0x7F,0xEA,0,0xC0,0x3E,0x10,0xEA,0,0x20,0xFA,0,0x40,0x76],0x150);
  await upload(page,rom,execution);await run(page,{ticks:9,a:rom[0],m49152:rom[131071],'mbc-bank':16,halted:1,fault:0});
  const request=page.waitForRequest(r=>r.method()==='POST');
  await Promise.all([page.waitForNavigation({waitUntil:'load'}),page.locator('.reset').click()]);
  expect((await request).postDataBuffer().length).toBeLessThanOrEqual(196608);
  expect(await read(page,['ticks','mbc-bank'])).toEqual({ticks:0,'mbc-bank':0});
});
for(const [size,expected] of [[32768,[1,1,0,1]],[65536,[1,1,0,3]],[131072,[1,1,0,7]]])test(`MBC1 ${size} zero adjustment precedes masking`,async({page})=>{
  const code=[];
  for(const [i,bank] of [0,32,16,255].entries())code.push(0x3E,bank,0xEA,0,0x20,0xFA,0,0x43,0xEA,i,0xC0);
  const rom=cartridge(size,[...code,0x76]);
  for(let bank=0;bank<size/16384;bank++)rom[bank*16384+768]=bank;
  await upload(page,rom);await run(page,{...Object.fromEntries(expected.map((x,i)=>[`m${49152+i}`,x])),'mbc-bank':31,halted:1,fault:0});
});
test('MBC1 third fetch lane and VRAM override stay independent',async({page})=>{
  const rom=cartridge(131072,[0x3E,7,0xEA,0,0x20,0x3E,0x99,0xEA,0,0x80,0x31,0xFF,0x7F,0xD1,0xC3,0xFE,0x3F]);
  rom.set([0x01,0x34],0x3FFE);rom.set([0x12,0x76],7*16384);rom[131071]=0xAB;
  await upload(page,rom);await run(page,{a:153,b:18,c:52,d:153,e:171,sp:32769,m32768:153,pc:16386,halted:1,fault:0});
});
test('sparse 128 KiB MBC1 reads the last physical byte in Streaming',async({page},info)=>{
  test.skip(info.project.name==='webkit-mobile','Streaming remains Chromium-only');
  const rom=cartridge(131072,[0x3E,7,0xEA,0,0x20,0xFA,0xFF,0x7F,0x76]);rom[131071]=123;
  await upload(page,rom,'streaming');await run(page,{ticks:5,a:123,'mbc-bank':7,halted:1,fault:0});
});
test('MBC1 CB read-modify-write changes the controller, not ROM bytes',async({page})=>{
  const rom=cartridge(65536,[0x21,0,0x20,0xCB,0xC6,0xFA,0,0x20,0x47,0xFA,0,0x41,0x76]);
  rom[0x2000]=2;rom[0xC100]=99;
  await upload(page,rom);await run(page,{a:99,b:2,'mbc-bank':3,halted:1,fault:0});
});
