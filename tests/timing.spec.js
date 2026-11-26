const {test,expect}=require('@playwright/test');
const read=(page,keys,selector='.machine')=>page.locator(selector).evaluate((el,keys)=>{
  const s=getComputedStyle(el);
  return Object.fromEntries(keys.map(k=>[k,Number(s.getPropertyValue('--'+k))]));
},keys);

for(const mode of ['portable','automatic','checkpoint','streaming'])test(`cycle inspector counts diagnostic work in ${mode}`,async({page},info)=>{
  test.skip(mode==='streaming'&&info.project.name==='webkit-mobile','Streaming requires Chromium');
  const path=mode==='streaming'?'/':mode==='portable'?'/portable/':`/${mode}/diagnostic/`;
  await page.goto(path);
  expect(await page.locator('script').count()).toBe(0);
  expect(await read(page,['tcycles'])).toEqual({tcycles:0});
  await page.locator('.power-switch').click();
  await expect.poll(()=>read(page,['ticks','tcycles','halted','fault']),{timeout:25000})
    .toEqual({ticks:24,tcycles:196,halted:1,fault:0});
  await page.getByText('Machine inspector',{exact:true}).click();
  await expect(page.locator('.timing-note')).toBeVisible();
  expect(await page.locator('.register-tcycles').evaluate(el=>getComputedStyle(el,'::after').counterReset)).toBe('value 196');
  await page.setViewportSize({width:320,height:844});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  await page.screenshot({path:info.outputPath('cycle-inspector.png'),fullPage:true});
  await page.waitForTimeout(250);
  expect(await read(page,['tcycles'])).toEqual({tcycles:196});
  await page.locator('.reset').click();
  expect(await read(page,['tcycles'])).toEqual({tcycles:0});
});

for(const mode of ['checkpoint','automatic'])test(`cycle accounting crosses a ${mode} bank and wraps`,async({page})=>{
  test.setTimeout(120000);
  await page.goto(`/${mode}/tests/timing/`);
  expect(await read(page,['tcycles'])).toEqual({tcycles:65520});
  await page.locator('.power-switch').click();
  if(mode==='checkpoint'){
    expect(await read(page,['ticks','tcycles','pc'])).toEqual({ticks:128,tcycles:512,pc:387});
    let saves=0;
    while(true){
      const copy=await read(page,['copy-index','copy-remaining','bank-phase'],'.checkpoint-select');
      if(!copy['copy-remaining'])break;
      expect(saves++).toBeLessThan(3568);
      await page.locator(`.bank${1-copy['bank-phase']}.copy-${copy['copy-index']} label`).click();
      // Incomplete copies must not leak cycle bits into the active result.
      expect(await read(page,['ticks','tcycles'])).toEqual({ticks:128,tcycles:512});
    }
    await page.locator('.commit-control label').click();
  }
  // LD HL=12; 126 NOPs=504; BIT [HL]=12; LD [HL],d8=12;
  // RLC [HL]=16; taken JR NZ=12; HALT entry=4: 572 T-cycles.
  await expect.poll(()=>read(page,['ticks','tcycles','pc','halted','fault','m49152']),{timeout:25000})
    .toEqual({ticks:132,tcycles:556,pc:394,halted:1,fault:0,m49152:3});
  await page.locator('.reset').click();
  expect(await read(page,['ticks','tcycles'])).toEqual({ticks:0,tcycles:65520});
});
