'use strict';
(() => {
 const base=new URL('.',document.currentScript.src),pending=new Map();
 let worker,sequence=0,lockReady,releaseLock,deleting=false;
 function storageControls(){const button=document.getElementById('delete-browser-data');if(button)button.disabled=deleting||pending.size>0;}
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
  if(deleting)throw Error('Browser data deletion is in progress.');
  await acquire();
  if(deleting)throw Error('Browser data deletion is in progress.');
  if(!worker){
   worker=new Worker(new URL('worker.js',base));
   worker.onmessage=({data:message})=>{
    if(message.progress){status(message.progress);return;}
    const item=pending.get(message.id);if(!item)return;
    pending.delete(message.id);storageControls();message.error?item.reject(Error(message.error)):item.resolve(message.result);
    if(!pending.size)status(message.error?'Action failed · '+message.error:'Saved in this browser · export your work before clearing site data');
   };
   worker.onerror=()=>{for(const item of pending.values())item.reject(Error('Engine worker stopped. Reload to recover saved work.'));pending.clear();storageControls();status('Engine stopped. Reload to recover saved work.');};
  }
  const id=++sequence;status('Computing on your device…');
  return new Promise((resolve,reject)=>{pending.set(id,{resolve,reject});storageControls();worker.postMessage({id,path,data});});
 }
 async function deleteBrowserData(){
  if(deleting||pending.size){status('Wait for the current action to finish before deleting browser data.');return;}
  if(!confirm('Permanently delete all Panda Chess models, games, arena history and project settings saved by this site in this browser? This cannot be undone. Download your project first if you want to keep it.'))return;
  deleting=true;storageControls();
  try{
   await acquire();
   worker?.terminate();worker=null;
   status('Deleting this chess site’s saved browser data…');
   const name='/panda-state/'+encodeURIComponent(base.pathname);
   await new Promise((resolve,reject)=>{
    const deletion=indexedDB.deleteDatabase(name);
    deletion.onsuccess=resolve;
    deletion.onerror=()=>reject(deletion.error||Error('Browser data could not be deleted.'));
    deletion.onblocked=()=>status('Close other tabs using this chess site to finish deleting its browser data.');
   });
   location.reload();
  }catch(error){deleting=false;storageControls();status('Deletion failed · '+error.message);}
 }
 document.addEventListener('DOMContentLoaded',()=>{
  const button=document.getElementById('delete-browser-data');
  if(button)button.onclick=deleteBrowserData;
  storageControls();
 });
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
