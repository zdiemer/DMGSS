const {test,expect}=require('@playwright/test');
const read=page=>page.locator('.machine').evaluate(el=>{const s=getComputedStyle(el);return Object.fromEntries(['pc','ticks','a','f','sp','m49152','m49154','halted','fault'].map(k=>[k,Number(s.getPropertyValue('--'+k))]))});
for(const mode of ['portable','automatic','checkpoint','streaming'])test(`ALU lab checks decimal, carry, bitwise and rotate operations in ${mode}`,async({page},info)=>{
  test.skip(mode==='streaming'&&info.project.name==='webkit-mobile','Streaming requires Chromium');
  const prefix=mode==='streaming'?'':`/${mode}`;
  await page.goto(`${prefix}/`);
  await page.getByRole('link',{name:'ALU lab',exact:true}).click();
  await expect(page).toHaveURL(new RegExp(`${prefix}/alu/$`));
  await page.locator('.power-switch').click();
  await expect.poll(async()=>(await read(page)).halted,{timeout:20000}).toBe(1);
  const result=await read(page);
  expect(result).toEqual({pc:340,ticks:43,a:165,f:192,sp:49216,m49152:16,m49154:165,halted:1,fault:0});
  await expect(page.locator('.passed')).toBeVisible();
  await page.setViewportSize({width:320,height:844});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  expect(await page.locator('.cartridges').evaluate(el=>el.scrollWidth<=el.clientWidth)).toBe(true);
  await expect(page.locator('.cartridges [aria-current="page"]')).toHaveText('ALU lab');
  await page.screenshot({path:info.outputPath('alu-lab.png'),fullPage:true});
});
