import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

const source=readFileSync(new URL('../bridge.js',import.meta.url),'utf8');
function setup(confirmResult=true){
 const handlers={},button={},status={},deleted=[],events=[];
 let deletion,worker;
 const context=vm.createContext({URL,Map,Promise,Error,Uint8Array,
  document:{currentScript:{src:'https://club.github.io/panda-chess-engine/bridge.js?v=123'},
   getElementById:id=>id==='delete-browser-data'?button:status,
   addEventListener:(name,fn)=>handlers[name]=fn},
  navigator:{locks:{request:(_name,_options,callback)=>{callback({});return Promise.resolve();}}},
  confirm:()=>confirmResult,indexedDB:{deleteDatabase:name=>{deleted.push(name);deletion={};queueMicrotask(()=>deletion.onsuccess());return deletion;}},
  location:{reload:()=>events.push('reload')},window:{},addEventListener:()=>{},
  Worker:class{constructor(){worker=this;}postMessage(message){this.message=message;}terminate(){events.push('terminate');}},
 });
 vm.runInContext(source,context);handlers.DOMContentLoaded();
 return {button,status,deleted,events,context,get worker(){return worker;}};
}
test('cancelling deletion leaves the database and page intact',async()=>{
 const app=setup(false);await app.button.onclick();
 assert.deepEqual(app.deleted,[]);assert.deepEqual(app.events,[]);assert.equal(app.button.disabled,false);
});
test('confirmed deletion targets only this deployment and reloads after success',async()=>{
 const app=setup();await app.button.onclick();
 assert.deepEqual(app.deleted,['/panda-state/%2Fpanda-chess-engine%2F']);
 assert.deepEqual(app.events,['reload']);
});
test('running requests prevent deletion and idle worker stops before database removal',async()=>{
 const app=setup();const request=app.context.window.panda.request('status');
 await new Promise(resolve=>setImmediate(resolve));
 assert.equal(app.button.disabled,true);await app.button.onclick();assert.deepEqual(app.deleted,[]);
 app.worker.onmessage({data:{id:app.worker.message.id,result:{models:[]}}});await request;
 assert.equal(app.button.disabled,false);await app.button.onclick();
 assert.deepEqual(app.events,['terminate','reload']);assert.equal(app.deleted.length,1);
});
