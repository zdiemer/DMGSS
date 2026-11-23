const {test,expect}=require('@playwright/test');
const read=page=>page.locator('.machine').evaluate(el=>{const s=getComputedStyle(el);return Object.fromEntries(['pc','ticks','a','c','h','l','f','sp','m65408','m65424','m65425','m65426','m65532','m65533','m65534','m49154','halted','fault'].map(k=>[k,Number(s.getPropertyValue('--'+k))]))});
for(const mode of ['portable','automatic','checkpoint','streaming'])test(`High RAM checks restart and executable RAM operations in ${mode}`,async({page},info)=>{
  test.skip(mode==='streaming'&&info.project.name==='webkit-mobile','Streaming requires Chromium');
  const prefix=mode==='streaming'?'':`/${mode}`;
  await page.goto(`${prefix}/`);
  await page.getByRole('link',{name:'High RAM',exact:true}).click();
  await expect(page).toHaveURL(new RegExp(`${prefix}/high/$`));
  await page.locator('.power-switch').click();
  await expect.poll(async()=>(await read(page)).halted,{timeout:20000}).toBe(1);
  const result=await read(page);
  expect(result).toEqual({pc:411,ticks:59,a:165,c:254,h:255,l:146,f:192,sp:65534,m65408:8,m65424:62,m65425:42,m65426:201,m65532:254,m65533:255,m65534:8,m49154:165,halted:1,fault:0});
  await expect(page.locator('.passed')).toBeVisible();
  await page.setViewportSize({width:320,height:844});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  expect(await page.locator('.cartridges').evaluate(el=>el.scrollWidth<=el.clientWidth)).toBe(true);
  await expect(page.locator('.cartridges [aria-current="page"]')).toHaveText('High RAM');
  await page.screenshot({path:info.outputPath('high-ram.png'),fullPage:true});
});
