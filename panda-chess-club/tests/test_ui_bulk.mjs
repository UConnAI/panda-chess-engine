import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
const source=readFileSync(new URL('../ui/app.js',import.meta.url),'utf8');
test('bulk managers are ready during the first application lock',()=>{
 let calls=0;
 const error={},working={};
 const context=vm.createContext({document:{querySelectorAll:()=>[],body:{dataset:{}}},
  $:id=>id==='error'?error:id==='working'?working:null,
  api:()=>{calls++;return new Promise(()=>{});},syncContinuation:()=>{}});
 vm.runInContext(source,context);
 assert.equal(calls,1,'initial status request must run without a bulk-manager initialization error');
});
