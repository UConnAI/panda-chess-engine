'use strict';
const PYODIDE = 'https://cdn.jsdelivr.net/pyodide/v0.27.7/full/';
let py, ready, queue = Promise.resolve(), fish, fishReady, fishWait;
const progress = message => postMessage({progress:message});
const sync = populate => new Promise((resolve,reject)=>py.FS.syncfs(populate, error=>error?reject(error):resolve()));

async function initialize(){
 progress('Loading Python runtime…');
 importScripts(PYODIDE+'pyodide.js');
 py=await loadPyodide({indexURL:PYODIDE});
 progress('Loading NumPy…');await py.loadPackage('numpy');
 progress('Loading chess engine and training boards…');
 const response=await fetch('engine.zip');if(!response.ok)throw Error('Chess source download failed.');
 py.unpackArchive(new Uint8Array(await response.arrayBuffer()),'zip',{extractDir:'/app'});
 const storage='/panda-state/'+encodeURIComponent(new URL('.',self.location.href).pathname);
 py.FS.mkdirTree(storage);py.FS.mount(py.FS.filesystems.IDBFS,{},storage);
 try{await sync(true);}catch(error){throw Error('Browser storage is unavailable. Allow site storage or try another browser. '+error.message);}
 py.globals.set('_storage',storage);
 await py.runPythonAsync("import sys\nsys.path.insert(0, '/app')\nimport browser_api\nbrowser_api.initialize(storage=_storage)");
 progress('Ready · work saves in this browser');
}

function startFish(){
 if(fishReady)return fishReady;
 progress('Loading browser Stockfish…');
 fishReady=new Promise((resolve,reject)=>{
  fish=new Worker('vendor/stockfish-17.1-lite-single-03e3232.js');
  const timer=setTimeout(()=>reject(Error('Stockfish did not load. Check the network and retry.')),45000);
  fish.onerror=()=>{clearTimeout(timer);reject(Error('Browser Stockfish failed to load.'));fishWait?.reject(Error('Stockfish stopped.'));};
  fish.onmessage=event=>{
   const text=String(event.data);
   if(text==='uciok'){fish.postMessage('setoption name Hash value 32');fish.postMessage('setoption name MultiPV value 3');fish.postMessage('isready');}
   if(text==='readyok'){clearTimeout(timer);resolve();}
   if(fishWait&&text.startsWith('info ')&&text.includes(' pv ')){
    const parts=text.split(' '),get=key=>parts[parts.indexOf(key)+1];
    const scoreType=get('score'),raw=Number(parts[parts.indexOf('score')+2]);
    if(['cp','mate'].includes(scoreType)&&Number.isFinite(raw))fishWait.rows.set(Number(get('multipv')||1),{
     score:scoreType==='mate'?Math.sign(raw)*1000000:raw,depth:Number(get('depth')),nodes:Number(get('nodes')),pv:parts.slice(parts.indexOf('pv')+1)});
   }
   if(fishWait&&text.startsWith('bestmove ')){const wait=fishWait;fishWait=null;clearTimeout(wait.timer);wait.resolve([...wait.rows].sort((a,b)=>a[0]-b[0]).map(x=>x[1]));}
  };
  fish.postMessage('uci');
 }).catch(error=>{fish?.terminate();fish=null;fishReady=null;throw error;});
 return fishReady;
}
async function analyze(fen){
 await startFish();
 return new Promise((resolve,reject)=>{
  fishWait={resolve,reject,rows:new Map(),timer:setTimeout(()=>{fishWait=null;fish.terminate();fish=null;fishReady=null;reject(Error('Stockfish analysis timed out. Retry.'));},15000)};
  fish.postMessage('position fen '+fen);fish.postMessage('go movetime 300');
 });
}

async function handle({id,path,data}){
 try{
  ready??=initialize();await ready;
  py.globals.set('_path',path);py.globals.set('_json',JSON.stringify(data??null));
  const fen=py.runPython("browser_api.stockfish_fen(_path, __import__('json').loads(_json) or {})");
  if(fen){const start=performance.now(),rows=await analyze(fen);py.globals.set('_fen',fen);py.globals.set('_rows',JSON.stringify(rows));py.globals.set('_seconds',(performance.now()-start)/1000);py.runPython("browser_api.accept_stockfish(_fen, __import__('json').loads(_rows), _seconds)");}
  const result=JSON.parse(await py.runPythonAsync("__import__('json').dumps(browser_api.request(_path, __import__('json').loads(_json)), allow_nan=False)"));
  try{await sync(false);}catch(error){throw Error('Could not save this action in browser storage. Export your work or free site storage before continuing. '+error.message);}
  postMessage({id,result});
 }catch(error){postMessage({id,error:error.message||String(error)});}
}
onmessage=event=>{queue=queue.then(()=>handle(event.data));};
