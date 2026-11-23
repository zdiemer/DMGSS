const {test,expect}=require('@playwright/test');
const {execFileSync}=require('node:child_process');
const datasets=JSON.parse(execFileSync('python3',['tools/conformance.py','--expectations'],{maxBuffer:16*1024*1024}));
for(const mode of ['math','native'])for(const [source,vectors] of Object.entries(datasets)){
  test(`${mode} CPU matches ${vectors.length} independent ${source} vectors`,async({page},info)=>{
    test.skip(mode==='native'&&info.project.name==='webkit-mobile','Native CSS if() is a Chromium engine requirement');
    test.setTimeout(180000);
    const keys=Object.keys(vectors[0].final);
    for(let offset=0;offset<vectors.length;offset+=128){
      await page.goto(`/tests/conformance/${mode}/${source}-${offset/128}.html`);
      expect(await page.locator('script').count()).toBe(0);
      const actual=await page.locator('.result').evaluateAll((elements,keys)=>elements.map(el=>{
        const css=getComputedStyle(el);
        return Object.fromEntries(keys.map(k=>[k,Number(css.getPropertyValue('--'+k))]));
      }),keys);
      const batch=vectors.slice(offset,offset+128);
      expect(actual.length).toBe(batch.length);
      for(let i=0;i<batch.length;i++)expect(actual[i],batch[i].name).toEqual(batch[i].final);
    }
  });
}
