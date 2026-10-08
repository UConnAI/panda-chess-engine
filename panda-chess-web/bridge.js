'use strict';
(() => {
 const base=new URL('.',document.currentScript.src),pending=new Map();
 let worker,sequence=0,lockReady,releaseLock;
 function status(text){const node=document.getElementById('browser-status');if(node)node.textContent=text;}
 async function acquire(){
  if(!navigator.locks)throw Error('This browser needs Web Locks support. Use a current Chrome, Edge, Firefox or Safari browser.');
  lockReady??=new Promise((resolve,reject)=>{
   navigator.locks.request('panda-chess:'+base.pathname,{ifAvailable:true},async lock=>{
    if(!lock){reject(Error('This workshop is already open in another tab. Close it, then reload this page.'));return;}
    resolve();await new Promise(done=>releaseLock=done);
   }).catch(reject);
  });
  await lockReady;
 }
 async function request(path,data){
  await acquire();
  if(!worker){
   worker=new Worker(new URL('worker.js',base));
   worker.onmessage=({data:message})=>{
    if(message.progress){status(message.progress);return;}
    const item=pending.get(message.id);if(!item)return;
    pending.delete(message.id);message.error?item.reject(Error(message.error)):item.resolve(message.result);
    if(!pending.size)status(message.error?'Action failed · '+message.error:'Saved in this browser · export your work before clearing site data');
   };
   worker.onerror=()=>{for(const item of pending.values())item.reject(Error('Engine worker stopped. Reload to recover saved work.'));pending.clear();status('Engine stopped. Reload to recover saved work.');};
  }
  const id=++sequence;status('Computing on your device…');
  return new Promise((resolve,reject)=>{pending.set(id,{resolve,reject});worker.postMessage({id,path,data});});
 }
 function save(content,name,type){const url=URL.createObjectURL(new Blob([content],{type})),link=document.createElement('a');link.href=url;link.download=name;link.click();setTimeout(()=>URL.revokeObjectURL(url),30000);}
 document.addEventListener('click',async event=>{
  const link=event.target.closest('a');if(!link)return;
  const url=new URL(link.href,location.href);
  const match=url.pathname.match(/\/(download\/(?:my-project|project)\.zip|pgn\/[^/]+|project\/report\.md)$/);
  if(!match||url.origin!==location.origin)return;
  event.preventDefault();
  if(link.dataset.busy)return;link.dataset.busy='true';link.setAttribute('aria-busy','true');
  try{const path=decodeURIComponent(match[1]),result=await request(path);
   if(path.endsWith('.zip'))save(Uint8Array.from(atob(result),c=>c.charCodeAt(0)),path.includes('my-project')?'My-Panda-Chess-Project.zip':'Panda-Chess-Starter.zip','application/zip');
   else save(result,path.split('/').at(-1),'text/plain');
  }catch(error){status(error.message);alert(error.message);}finally{delete link.dataset.busy;link.removeAttribute('aria-busy');}
 });
 addEventListener('pagehide',()=>{worker?.terminate();releaseLock?.();});
 window.panda={request};
})();
