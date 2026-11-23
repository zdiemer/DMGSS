const {test,expect}=require('@playwright/test');
const {execFileSync}=require('node:child_process');
const datasets=JSON.parse(execFileSync('python3',['tools/conformance.py','--expectations'],{maxBuffer:16*1024*1024}));
// Bound each test's work as memory grows; every pinned vector is still checked.
const batchSize=2048;
for(const mode of ['math','native'])for(const [source,vectors] of Object.entries(datasets))for(let start=0;start<vectors.length;start+=batchSize){
  const end=Math.min(start+batchSize,vectors.length);
  test(`${mode} CPU matches independent ${source} vectors ${start}–${end-1}`,async({page},info)=>{
    test.skip(mode==='native'&&info.project.name==='webkit-mobile','Native CSS if() is a Chromium engine requirement');
    test.setTimeout(180000);
    const keys=Object.keys(vectors[0].final);
    for(let offset=start;offset<end;offset+=128){
      await page.goto(`/tests/conformance/${mode}/${source}-${offset/128}.html`);
      expect(await page.locator('script').count()).toBe(0);
      const actual=await page.locator('.result').evaluateAll((elements,keys)=>elements.map(el=>{
        const css=getComputedStyle(el);
        return Object.fromEntries(keys.map(k=>[k,Number(css.getPropertyValue('--'+k))]));
      }),keys);
      const batch=vectors.slice(offset,Math.min(offset+128,end));
      expect(actual.length).toBe(batch.length);
      for(let i=0;i<batch.length;i++)expect(actual[i],batch[i].name).toEqual(batch[i].final);
    }
  });
}
