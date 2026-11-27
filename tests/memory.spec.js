const {readState}=require('./helpers/state');
const {test,expect}=require('@playwright/test');
const {pathToFileURL}=require('node:url');
test.describe.configure({timeout:120000});
const read = readState;
async function upload(page,bytes,mode='portable',format='raw',download=false){
  await page.goto('/convert/');
  await page.locator('#rom').setInputFiles({name:format==='gb'?'ram.gb':'ram.bin',mimeType:'application/octet-stream',buffer:Buffer.from(bytes)});
  await page.locator('#format').selectOption(format);await page.locator('#mode').selectOption(mode);
  if(download){const result=page.waitForEvent('download');await page.locator('button[value=download]').click();return result;}
  await Promise.all([page.waitForNavigation({waitUntil:'load'}),page.locator('button[value=open]').click()]);
}
async function run(page,expected){
  await page.locator('.power-switch').click();
  await expect.poll(()=>read(page,Object.keys(expected)),{timeout:60000,intervals:[1000,3000]}).toEqual(expected);
}
for(const mode of ['portable','automatic','checkpoint','streaming'])test(`work RAM sample shares physical bytes with echo in ${mode}`,async({page},info)=>{
  test.skip(mode==='streaming'&&info.project.name==='webkit-mobile','Streaming remains Chromium-only');
  const bytes=await (await page.request.get('/convert/ram.gb')).body();
  await upload(page,bytes,mode,'gb');
  const requests=[];page.on('request',r=>requests.push(r.url()));
  await run(page,{ticks:24,pc:394,a:165,f:192,m49152:18,m53247:52,m53248:86,m57343:120,m49154:165,halted:1,fault:0});
  expect(requests).toEqual([]);expect(await page.locator('.passed,script').count()).toBe(0);
  await Promise.all([page.waitForNavigation({waitUntil:'load'}),page.locator('.reset').click()]);
  expect(await read(page,['ticks','m53247','m57343'])).toEqual({ticks:0,m53247:0,m57343:0});
});
test('all 256 work RAM bytes survive automatic banks with distinct values',async({page})=>{
  test.setTimeout(900000);
  // LD HL,C000; loop: LD (HL),L; INC L; JR NZ,loop; HALT.
  await upload(page,[0x21,0,0xC0,0x75,0x2C,0x20,0xFC,0x76],'automatic');
  await page.locator('.power-switch').click();
  await expect.poll(()=>read(page,['ticks','pc','h','l','f','halted','fault']),{timeout:210000,intervals:[1000,5000]}).toEqual({ticks:770,pc:264,h:192,l:0,f:160,halted:1,fault:0});
  const expected=Object.fromEntries(Array.from({length:256},(_,i)=>['m'+(49152+i),i]));
  expect(await read(page,Object.keys(expected))).toEqual(expected);
  expect(await page.locator('.scroll-memory').count()).toBe(8435);
});
for(const mode of ['automatic','checkpoint'])test(`new work RAM and echo survive a ${mode} bank`,async({page},info)=>{
  test.setTimeout(900000);
  // Seven instructions set distinct bytes. NOPs finish the first 128-step bank.
  const code=[0x3E,1,0xEA,0x40,0xE0,0x3E,2,0xEA,0xFE,0xC0,0x3E,4,0xEA,0xFF,0xE0,0xAF,
    ...Array(121).fill(0),0xFA,0x40,0xC0,0x47,0xFA,0xFE,0xE0,0x4F,0xFA,0xFF,0xC0,0x76];
  await upload(page,code,mode);await page.locator('.power-switch').click();
  if(mode==='checkpoint'){
    const before={ticks:128,pc:393,a:0,m49216:1,m49406:2,m49407:4};
    expect(await read(page,Object.keys(before))).toEqual(before);
    let saved=0;
    while(true){
      const state=await read(page,['copy-index','copy-remaining','bank-phase'],'.checkpoint-select');
      if(!state['copy-remaining'])break;
      expect(saved++).toBeLessThan(67056);
      const label=page.locator(`.bank${1-state['bank-phase']}.copy-${state['copy-index']}`);
      if(info.project.name.endsWith('mobile'))await label.tap();else await label.click();
      await expect.poll(async()=>(await read(page,['copy-remaining'],'.checkpoint-select'))['copy-remaining']).toBe(state['copy-remaining']-1);
      expect(await read(page,Object.keys(before))).toEqual(before);
    }
    await page.locator('.commit-control label').click();
  }
  await expect.poll(()=>read(page,['ticks','pc','a','b','c','m49216','m49406','m49407','halted','fault']),{timeout:60000}).toEqual({ticks:134,pc:405,a:4,b:1,c:2,m49216:1,m49406:2,m49407:4,halted:1,fault:0});
});
test('echo instruction fetch preserves logical PC and CALL return address',async({page})=>{
  // Write LD A,42; RET to physical C040; call it through E040.
  await upload(page,[0x31,0,0xE1,0x21,0x40,0xC0,0x36,0x3E,0x23,0x36,42,0x23,0x36,0xC9,0xCD,0x40,0xE0,0x76]);
  await run(page,{ticks:11,pc:274,sp:57600,a:42,m49216:62,m49217:42,m49218:201,m49406:17,m49407:1,halted:1,fault:0});
});
test('echo CB writes and two-byte stores update the physical RAM',async({page})=>{
  await upload(page,[0x31,0x34,0x12,0x08,0xFE,0xE0,0x21,0xFE,0xE0,0xCB,0x36,0x2A,0x47,0x7E,0x76]);
  await run(page,{ticks:8,pc:271,h:224,l:255,a:18,b:67,f:0,m49406:67,m49407:18,halted:1,fault:0});
});
for(const invalid of [false,true])test(`interrupt entry uses the echo stack ${invalid?'atomically on failure':'and RETI returns'}`,async({page})=>{
  const rom=Buffer.alloc(32768);rom.set([0x3C,0xD9],0x40);
  rom.set([0x31,invalid?1:0,invalid?0xFE:0xE1,0x3E,1,0xEA,0xFF,0xFF,0xE0,0x0F,0xFB,0,0x76],0x100);
  await upload(page,rom,'portable','gb');
  await run(page,invalid
    ? {ticks:6,tcycles:56,pc:268,sp:65025,ime:1,m65295:225,m56831:0,halted:0,fault:1}
    : {ticks:9,tcycles:100,pc:269,sp:57600,ime:1,m65295:224,m49406:12,m49407:1,a:2,halted:1,fault:0});
});
for(const address of [0xFDFF])test(`word write at ${address.toString(16)} traps before either lane commits`,async({page})=>{
  await upload(page,[0x31,0x34,0x12,0x08,address&255,address>>8]);
  await run(page,{ticks:1,tcycles:12,pc:259,sp:4660,m56831:0,halted:0,fault:1});
});
test('echo fetch at the last byte rejects a missing immediate atomically',async({page})=>{
  await upload(page,[0x3E,0x3E,0xEA,0xFF,0xDD,0xC3,0xFF,0xFD]);
  await run(page,{ticks:3,tcycles:40,pc:65023,a:62,m56831:62,halted:0,fault:1});
});
for(const address of [0xA000,0xFE00,0xFEA0,0xFF00])test(`unimplemented memory ${address.toString(16)} remains a trap`,async({page})=>{
  await upload(page,[0x3E,0x5A,0xEA,address&255,address>>8]);
  await run(page,{ticks:1,pc:258,a:90,m49152:0,m49407:0,halted:0,fault:1});
});
for(const mode of ['portable','automatic'])test(`downloaded RAM diagnostic executes offline in ${mode} with no requests`,async({page},info)=>{
  const bytes=await (await page.request.get('/convert/ram.gb')).body();
  const download=await upload(page,bytes,mode,'gb',true);
  const file=info.outputPath('ram.html');await download.saveAs(file);
  const requests=[];page.on('request',r=>{if(/^https?:/.test(r.url()))requests.push(r.url())});
  await page.goto(pathToFileURL(file).href);
  await run(page,{ticks:24,a:165,m57343:120,halted:1,fault:0});
  expect(requests).toEqual([]);
});

for(const [seed,target] of [[0,65535],[65535,0],[65280,255],[255,65280]])test(`packed RAM preserves byte lanes and seeded offsets ${seed}`,async({page})=>{
  await page.goto(`/automatic/tests/packing/lanes-${seed}/`);
  expect(await read(page,['m49152','m49153','m65534','m65535'])).toEqual({m49152:seed&255,m49153:seed>>8,m65534:90,m65535:160});
  const low=((target&255)+1)&255;
  await run(page,{ticks:260,pc:542,sp:target,a:66,b:target&255,c:target>>8,d:low,e:target>>8,h:low,l:0,
    m49152:low,m49153:66,m65532:171,m65533:205,m65534:165,m65535:192,halted:1,fault:0});
  expect(await page.locator('.memory-b0-m65534,.memory-b0-m65535').count()).toBe(2);
  expect(await page.locator('.memory-b0-ram65534').count()).toBe(0);
  await Promise.all([page.waitForNavigation({waitUntil:'load'}), page.locator('.reset').click()]);
  expect(await read(page,['ticks','m49152','m49153','m65534','m65535'])).toEqual({ticks:0,m49152:seed&255,m49153:seed>>8,m65534:90,m65535:160});
});
for(const [seed,target] of [[0,65535],[1,0]])test(`packed RAM reaches exact scroll offset 65535 from seed ${seed}`,async({page})=>{
  await page.goto(`/automatic/tests/packing/max-${seed}/`);
  await run(page,{ticks:133,pc:397,sp:target,a:target>>8,b:target&255,c:target>>8,m49152:target&255,m49153:target>>8,halted:1,fault:0});
  for(const bank of [0,1])expect(await page.locator(`.memory-b${bank}-wram49152`).evaluate(el=>el.scrollTop)).toBe(65535);
});
test('packed RAM retains a cross-pair word and commits an atomic boundary trap',async({page})=>{
  // C001/C002 occupy different pairs. The later FDFF/FE00 write must fail whole.
  const code=[0x31,0x34,0x12,0x08,1,0xC0,0x3E,0xA5,0xEA,0xFF,0xFD,0x31,0x78,0x56,...Array(123).fill(0),0x08,0xFF,0xFD];
  await upload(page,code,'automatic');
  await run(page,{ticks:128,pc:393,sp:22136,m49152:0,m49153:52,m49154:18,m49155:0,m56830:0,m56831:165,halted:0,fault:1});
});

for(const address of [0xC0FF,0xE0FF,0xCFFF,0xEFFF,0xDFFF])test(`word store crosses ${address.toString(16)} without aliasing its lanes`,async({page})=>{
  const physical=a=>a>=0xE000&&a<0xFE00?a-0x2000:a;
  await upload(page,[0x31,0x34,0x12,0x08,address&255,address>>8,0xFA,address&255,address>>8,0x47,0xFA,(address+1)&255,(address+1)>>8,0x76]);
  await run(page,{ticks:6,pc:270,a:18,b:52,sp:4660,[`m${physical(address)}`]:52,[`m${physical(address+1)}`]:18,halted:1,fault:0});
});
for(const high of [0xCF,0xEF])test(`instruction fetch crosses ${high.toString(16)}FF with logical PC`,async({page})=>{
  await upload(page,[0x3E,0x3E,0xEA,0xFF,0xCF,0x3E,42,0xEA,0,0xD0,0x3E,0x76,0xEA,1,0xD0,0xC3,0xFF,high]);
  await run(page,{ticks:9,pc:(high+1)*256+2,a:42,m53247:62,m53248:42,m53249:118,halted:1,fault:0});
});
for(const sp of [0xE000,0xFE00])test(`stack at ${sp.toString(16)} preserves the logical pointer`,async({page})=>{
  const low=sp===0xE000?0xDFFE:0xDDFE;
  await upload(page,[0x31,sp&255,sp>>8,0x01,0x34,0x12,0xC5,0xD1,0x76]);
  await run(page,{ticks:5,pc:265,sp,d:18,e:52,[`m${low}`]:52,[`m${low+1}`]:18,halted:1,fault:0});
});
test('DE00 has no FE00 echo alias',async({page})=>{
  await upload(page,[0x3E,42,0xEA,0,0xDE,0xFA,0,0xFE]);
  await run(page,{ticks:2,pc:261,a:42,m56832:42,halted:0,fault:1});
});
test('all 8192 physical bytes survive automatic banks, including page crossings',async({page})=>{
  test.setTimeout(900000);
  await page.goto('/automatic/tests/full-ram/all-bytes/');
  await run(page,{ticks:133,pc:521,sp:8240,a:32,b:17,c:32,halted:1,fault:0});
  const expected={};
  for(let i=0;i<8192;i++)expected['m'+(49152+i)]=(i*73+(i>>8)*19+11)&255;
  for(let p=0;p<32;p++){expected['m'+(49152+p*256+127)]=p+17;expected['m'+(49152+p*256+128)]=p+1;}
  expect(await read(page,Object.keys(expected))).toEqual(expected);
  await page.waitForTimeout(1000);
  expect(await read(page,Object.keys(expected))).toEqual(expected);
});
for(const seed of [0,0x3412])test(`automatic RAM can become dormant and reactivate from seed ${seed}`,async({page})=>{
  test.setTimeout(900000);
  await page.goto(`/automatic/tests/full-ram/reactivate-${seed}/`);
  await run(page,{ticks:516,pc:788,sp:43981,a:171,b:205,m49152:205,m49153:171,halted:1,fault:0});
});
