// NODE_PATH must include Playwright. Run against a static preview URL with a subpath:
// node tests/browser-smoke.cjs http://127.0.0.1:4343/site/
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 const context=await browser.newContext({acceptDownloads:true});
 const page=await context.newPage(),errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 page.on('console',m=>{if(m.type()==='error')console.log('Browser console:',m.text());});
 const base=process.argv[2]||'http://127.0.0.1:4343/site/';
 const start=Date.now();await page.goto(base);
 await page.waitForFunction(()=>document.querySelectorAll('#board .square').length===64,{},{timeout:180000});
 console.log('Cold engine + board ready ms:',Date.now()-start);
 const call=(path,data)=>page.evaluate(async({path,data})=>window.panda.request(path,data),{path,data});
 const board=await call('board',{moves:[]});assert.equal(board.board.turn,'White');
 const random=await call('move',{moves:[],kind:'random'});assert.equal(random.board.turn,'Black');
 const neural=await call('train',{count:200,epochs:1,rate:.01});assert.equal(neural.models.length,1);
 await call('project/profile',{title:'Browser smoke engine',author:'Student',description:'Independent export'});
 await call('save-game',{moves:['e2e4'],kind:'random'});
 await call('arena/start',{candidate:'random',opponent:'material',games:2,depth:1,budget:300,cap:40});
 let arena;for(let i=0;i<90;i++){arena=await call('arena/step',{});if(arena.run.finished)break;}
 assert.equal(arena.run.finished,true);assert.equal(arena.run.results.length,2);
 await call('references/reveal',{});
 const fish=await call('analyze',{moves:[],kind:'reference-stockfish'});assert.ok(fish.search.move);assert.equal(fish.search.external,true);
 const compare=await call('references/compare',{example:'queen',moves:[]});assert.equal(compare.choices.length,3);
 await page.reload();await page.waitForFunction(()=>document.querySelectorAll('#board .square').length===64,{},{timeout:180000});
 assert.equal((await call('status')).models.length,1);
 assert.equal((await call('project')).title,'Browser smoke engine');
 assert.equal((await call('arena')).run.results.length,2);
 await page.goto(new URL('take-home.html',base).href);
 const out=path.resolve(__dirname,'../.build');
 for(const [route,name] of [['my-project','smoke-my-project.zip'],['project','smoke-starter.zip']]){
  const wait=page.waitForEvent('download',{timeout:180000});
  await page.locator(`a[href="download/${route}.zip"]`).click();
  const download=await wait;await download.saveAs(path.join(out,name));
  assert.ok(fs.statSync(path.join(out,name)).size>100000);
 }
 await page.goto(new URL('lecture.html#engine-illustrations',base).href);
 assert.ok(await page.locator('#engine-illustrations').count());
 await page.screenshot({path:path.join(out,'lecture-browser.png'),fullPage:false});
 assert.deepEqual(errors,[]);
 console.log('Browser checks passed: board, real training, arena, Stockfish, comparison, persistence, downloads, lecture.');
 await browser.close();
})().catch(error=>{console.error(error);process.exit(1);});
