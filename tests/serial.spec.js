const {readState}=require('./helpers/state');
const {test,expect}=require('@playwright/test');
const read = readState;
const logKeys=Array.from({length:16},(_,i)=>'serial-log'+i);
const final={ticks:5,tcycles:68,pc:262,a:165,b:1,sp:65534,halted:1,fault:0,m65281:255,m65282:127,m65295:224,
  'serial-count':0,'serial-length':16,'serial-phase':0,'serial-bits':0,'serial-tx':65};
for(const mode of ['automatic','checkpoint','portable','streaming'])test(`serial completion, output rollover and IRQ in ${mode}`,async({page},info)=>{
  test.skip(mode==='streaming'&&info.project.name==='webkit-mobile','Streaming requires Chromium');
  // Full log eviction changes many native bits; keep each bit progress-bounded.
  test.setTimeout(mode==='checkpoint'?240000:60000);
  const prefix=mode==='streaming'?'':`/${mode}`;
  await page.goto(`${prefix}/tests/serial-boundary/`);
  await page.locator('.power-switch').click();
  if(mode==='checkpoint'){
    const expected={ticks:0,tcycles:0,halted:1,m65282:127,m65295:232,'serial-count':0,'serial-length':16,'serial-log15':65};
    expect(await read(page,Object.keys(expected))).toEqual(expected);
    await expect(page.locator('.checkpoint-controls')).toBeVisible();
    const before=await read(page,[...Object.keys(expected),...logKeys]);
    let saved=0;
    while(true){
      const copy=await read(page,['copy-index','copy-remaining','bank-phase'],'.checkpoint-select');
      if(!copy['copy-remaining'])break;
      expect(saved++).toBeLessThan(132522);
      await page.locator(`.bank${1-copy['bank-phase']}.copy-${copy['copy-index']}`).click();
      await expect.poll(async()=>(await read(page,['copy-remaining'],'.checkpoint-select'))['copy-remaining']).toBe(copy['copy-remaining']-1);
      expect(await read(page,Object.keys(before))).toEqual(before);
      if(saved===1){await page.locator('.power-switch').click();await page.locator('.power-switch').click();}
    }
    await page.locator('.commit-control label').click();
  }
  await expect.poll(()=>read(page,Object.keys(final)),{timeout:45000}).toEqual(final);
  expect(Object.values(await read(page,logKeys))).toEqual([...Buffer.from('123456789ABCDEFA')]);
  await page.locator('.serial-monitor summary').click();
  await expect(page.locator('.serial-text span:visible')).toHaveCount(16);
  expect(await page.locator('.serial-hex .serial-byte15').evaluate(el=>getComputedStyle(el,'::after').content)).toContain('serial-hex');
  await page.setViewportSize({width:320,height:844});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  await page.screenshot({path:info.outputPath('serial-monitor.png'),fullPage:true});
  await page.waitForTimeout(200);
  expect(await read(page,Object.keys(final))).toEqual(final);
});
test('serial lab sends OK through HALT and polling',async({page})=>{
  test.setTimeout(900000);
  await page.goto('/automatic/');
  await page.getByRole('link',{name:'Serial',exact:true}).click();
  await page.locator('.power-switch').click();
  const expected={b:2,sp:65534,m65281:255,m65282:127,m65295:224,m49154:165,'serial-count':2,'serial-length':2,'serial-log0':79,'serial-log1':75,'serial-phase':0,'serial-bits':0,'serial-tx':75,halted:1,fault:0};
  // Frequent visibility polls force expensive active-pipeline layout on shared
  // runners. Leave time for native rendering and report actual state on failure.
  await expect.poll(()=>read(page,Object.keys(expected)),{timeout:150000,intervals:[5000]}).toEqual(expected);
  await expect(page.locator('.passed')).toBeVisible();
  await expect(page.locator('.serial-text span:visible')).toHaveCount(2);
  await page.locator('.power-switch').click();await page.locator('.power-switch').click();
  expect(await read(page,Object.keys(expected))).toEqual(expected);
  await Promise.all([page.waitForNavigation({waitUntil:'load'}), page.locator('.reset').click()]);
  expect(await read(page,['serial-count','serial-length','m65282'])).toEqual({'serial-count':0,'serial-length':0,m65282:126});
});
test('compatible serial lab truthfully stops partway through a byte',async({page})=>{
  await page.goto('/portable/serial/');await page.locator('.power-switch').click();
  const expected={ticks:14,tcycles:120,halted:1,fault:0,m65281:79,m65282:255,'serial-count':0,'serial-phase':468};
  expect(await read(page,Object.keys(expected))).toEqual(expected);
  await expect(page.locator('.timer-message')).toBeVisible();
  await expect(page.locator('.serial-note')).toContainText('multiple batches');
});
test('serial clocks a halted CPU with IE off and no retired instructions',async({page})=>{
  test.setTimeout(120000);
  await page.goto('/automatic/tests/serial-idle/');await page.locator('.power-switch').click();
  await page.waitForTimeout(3500); // No reads or inputs supply the clock.
  const expected={ticks:0,tcycles:0,clocked:1,halted:1,fault:0,m65281:255,m65282:127,m65295:232,'serial-count':1,'serial-length':1,'serial-log0':65};
  await expect.poll(()=>read(page,Object.keys(expected)),{timeout:90000}).toEqual(expected);
  await expect(page.locator('.startup-screen')).not.toBeVisible();
});
test('unconnected external clock never synthesizes a completion',async({page})=>{
  await page.goto('/automatic/tests/serial-external/');await page.locator('.power-switch').click();
  const expected={ticks:1,halted:1,fault:0,m65281:65,m65282:254,m65295:224,'serial-count':0,'serial-bits':0,'serial-phase':0};
  await expect.poll(()=>read(page,Object.keys(expected))).toEqual(expected);
  await page.waitForTimeout(300);
  expect(await read(page,Object.keys(expected))).toEqual(expected);
});

test('manual checkpoint retains a partial serial byte and sub-bit phase',async({page})=>{
  test.setTimeout(120000);
  await page.goto('/checkpoint/tests/serial-midbit/');await page.locator('.power-switch').click();
  const before={ticks:0,halted:1,m65281:255,m65282:255,m65295:224,'serial-phase':128,'serial-bits':7,'serial-tx':32,'serial-count':65535,'serial-log0':48};
  expect(await read(page,Object.keys(before))).toEqual(before);
  let saves=0;
  while(true){
    const copy=await read(page,['copy-index','copy-remaining','bank-phase'],'.checkpoint-select');
    if(!copy['copy-remaining'])break;
    expect(saves++).toBeLessThan(132522);
    await page.locator(`.bank${1-copy['bank-phase']}.copy-${copy['copy-index']}`).click();
    await expect.poll(async()=>(await read(page,['copy-remaining'],'.checkpoint-select'))['copy-remaining']).toBe(copy['copy-remaining']-1);
    expect(await read(page,Object.keys(before))).toEqual(before);
  }
  await page.locator('.commit-control label').click();
  expect(await read(page,Object.keys(final))).toEqual(final);
  expect(Object.values(await read(page,logKeys))).toEqual([...Buffer.from('123456789ABCDEFA')]);
});
