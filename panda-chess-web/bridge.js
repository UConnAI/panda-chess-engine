'use strict';
(() => {
 const base=new URL('.',document.currentScript.src),pending=new Map();
 let worker,sequence=0,lockReady,releaseLock,deleting=false;
 function storageControls(){for(const id of ['delete-browser-data','choose-browser-data']){const button=document.getElementById(id);if(button)button.disabled=deleting||pending.size>0;}}
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
 async function chooseBrowserData(){
  const host=document.getElementById('browser-data-categories');
  try{
   const rows=await request('browser/storage');host.replaceChildren();
   const choices=rows.map(row=>{
    const label=document.createElement('label');label.style.cssText='display:flex;gap:10px;align-items:center;margin:12px 0';
    const input=document.createElement('input');input.type='checkbox';input.value=row.id;
    const text=document.createElement('span');text.textContent=row.label+' · '+row.files+' files · '+(row.bytes/1024).toFixed(1)+' KiB';
    label.append(input,text);host.append(label);return {row,input};
   });
   const note=document.createElement('p');note.className='muted';note.textContent='Deleting models resets a neural champion and ends the active match. Kept histories remain replayable, but deleted bots cannot play extra moves. Download your project first.';host.append(note);
   const action=document.createElement('button');action.className='danger';action.disabled=true;host.append(action);
   const selected=()=>choices.filter(c=>c.input.checked).map(c=>c.row);
   const update=()=>{const rows=selected();action.disabled=!rows.length||pending.size>0;action.textContent='Delete selected categories ('+rows.length+') · '+(rows.reduce((sum,r)=>sum+r.bytes,0)/1024).toFixed(1)+' KiB';};
   choices.forEach(c=>c.input.onchange=update);update();
   action.onclick=async()=>{
    const rows=selected();if(!rows.length||pending.size)return;
    if(!confirm('Permanently delete these categories from this browser?\n\n'+rows.map(r=>r.label).join('\n')+'\n\nThis cannot be undone. Models reset the neural champion and end the active match. Unselected categories and downloaded ZIPs are kept.'))return;
    choices.forEach(c=>c.input.disabled=true);action.disabled=true;
    try{await request('browser/delete-categories',{categories:rows.map(r=>r.id)});location.reload();}
    catch(error){status('Deletion failed · '+error.message);choices.forEach(c=>c.input.disabled=false);update();}
   };
  }catch(error){status('Could not inspect browser data · '+error.message);}
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
  const choose=document.getElementById('choose-browser-data');if(choose)choose.onclick=chooseBrowserData;
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
