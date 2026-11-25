const {test,expect}=require('@playwright/test');
const {execFileSync}=require('node:child_process');
const cases=JSON.parse(execFileSync('python3',['-c','import sys,json;sys.path.insert(0,"tools");from timer_fixtures import cases;print(json.dumps(cases()))']));
const read=(page,keys,selector='.machine')=>page.locator(selector).evaluate((el,keys)=>{
  const s=getComputedStyle(el);return Object.fromEntries(keys.map(k=>[k,Number(s.getPropertyValue('--'+k))]));
},keys);
for(const item of cases)test(`timer matches reduced Mooneye ${item.name}`,async({page})=>{
  test.setTimeout(90000);
  await page.goto(`/automatic/tests/mooneye-${item.name}/`);
  expect(await page.locator('script').count()).toBe(0);
  await page.locator('.power-switch').click();
  await expect.poll(()=>read(page,['halted','fault']),{timeout:60000}).toEqual({halted:1,fault:0});
  expect(await read(page,Object.keys(item.expect))).toEqual(item.expect);
});

for(const mode of ['portable','automatic','checkpoint','streaming'])test(`Timer lab wakes HALT with hardware overflow in ${mode}`,async({page},info)=>{
  test.skip(mode==='streaming'&&info.project.name==='webkit-mobile','Streaming requires Chromium');
  test.setTimeout(60000);
  const prefix=mode==='streaming'?'':`/${mode}`;
  await page.goto(`${prefix}/`);
  await page.getByRole('link',{name:'Timers',exact:true}).click();
  await expect(page).toHaveURL(new RegExp(`${prefix}/timers/$`));
  await page.locator('.power-switch').click();
  await expect(page.locator('.passed')).toBeVisible({timeout:45000});
  const expected={ticks:36,tcycles:360,a:165,b:1,sp:65534,m49152:42,m49154:165,m65285:43,m65286:42,m65287:248,m65295:224,halted:1,fault:0,'timer-reload':0};
  expect(await read(page,Object.keys(expected))).toEqual(expected);
  await page.getByText('Machine inspector',{exact:true}).click();
  await page.setViewportSize({width:320,height:844});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  await page.screenshot({path:info.outputPath('timer-lab.png'),fullPage:true});
  await page.locator('.reset').click();
  // Streaming resolves register defaults on its first powered latch.
  const reset=mode==='streaming'?{ticks:0,clocked:0}:{ticks:0,clocked:0,m65284:0,m65285:0,m65287:248};
  expect(await read(page,Object.keys(reset))).toEqual(reset);
});

for(const mode of ['automatic','checkpoint'])test(`timer overflow and HALT cross a ${mode} bank`,async({page})=>{
  test.setTimeout(180000);
  await page.goto(`/${mode}/tests/timer-boundary/`);
  await page.locator('.power-switch').click();
  if(mode==='checkpoint'){
    const before={ticks:128,tcycles:512,halted:1,m65284:2,'div-low':0,m65285:0,'timer-reload':1,m65295:224};
    expect(await read(page,Object.keys(before))).toEqual(before);
    await expect(page.locator('.timer-message')).toBeVisible();
    await expect(page.locator('.checkpoint-controls')).toBeVisible();
    let saves=0;
    while(true){
      const copy=await read(page,['copy-index','copy-remaining','bank-phase'],'.checkpoint-select');
      if(!copy['copy-remaining'])break;
      expect(saves++).toBeLessThan(2032);
      await page.locator(`.bank${1-copy['bank-phase']}.copy-${copy['copy-index']} label`).click();
      expect(await read(page,Object.keys(before))).toEqual(before);
    }
    await page.locator('.power-switch').click();
    await page.locator('.power-switch').click();
    expect(await read(page,Object.keys(before))).toEqual(before);
    await page.locator('.commit-control label').click();
  }
  // Reload at phase 516, natural edges at 528/544, then TAC-disable edge at 552.
  const expected={ticks:135,tcycles:596,pc:390,a:165,b:1,sp:65534,m49154:165,m65284:2,'div-low':88,m65285:45,m65286:42,m65287:248,m65295:224,'timer-reload':0,halted:1,fault:0};
  await expect.poll(()=>read(page,Object.keys(expected)),{timeout:30000}).toEqual(expected);
  await expect(page.locator('.passed')).toBeVisible();
  await page.waitForTimeout(250);
  expect(await read(page,Object.keys(expected))).toEqual(expected);
});

test('automatic recognizes timer progress without retired instructions',async({page})=>{
  test.setTimeout(120000);
  await page.goto('/automatic/tests/timer-idle/');
  await page.locator('.power-switch').click();
  await page.waitForTimeout(3500); // No inspection supplies an execution clock.
  await page.locator('.power-switch').click();
  const keys=['ticks','tcycles','clocked','halted','fault','m65284','div-low','m65285','m65295'];
  const paused=await read(page,keys);
  expect(paused).toMatchObject({ticks:0,tcycles:0,clocked:1,halted:1,fault:0});
  await expect(page.locator('.startup-screen')).not.toBeVisible();
  await expect(page.locator('.timer-message')).toBeVisible();
  await page.waitForTimeout(250);
  expect(await read(page,keys)).toEqual(paused);
});
