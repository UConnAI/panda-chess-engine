'use strict';
// One isolated preview at a time. Timers never change the playable game.
let continuation=null,continuationGeneration=0;
function stopContinuation(){
 continuationGeneration++;
 if(continuation?.timer)clearInterval(continuation.timer);
 continuation=null;
}
function syncContinuation(){if(continuation?.host.isConnected)continuation.sync();}
function revealContinuation(host){
 if(!host?.isConnected)return;
 const heading=host.querySelector('h3');
 if(heading){heading.tabIndex=-1;heading.focus({preventScroll:true});}
 host.scrollIntoView({behavior:window.matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth',block:'start'});
}
async function previewContinuation(hostId,source,line,title,prepared=null,startAtEnd=false,reveal=false){
 stopContinuation();const generation=continuationGeneration;
 const host=$(hostId);if(!host)return;
 host.innerHTML='<p class="muted">Loading searched continuation…</p>';
 const data=prepared||await api('preview-line',{...source,line:[...line]});
 if(generation!==continuationGeneration||!host.isConnected)return;
 host.innerHTML='<div class="continuation"><h3></h3><p class="muted">Preview only · Step through alternating White and Black moves. Your game stays unchanged.</p><div class="continuation-board board"></div><p class="continuation-status status" role="status" aria-live="polite"></p><div class="controls continuation-controls"><button data-preview="start">↤ Start</button><button data-preview="back">← Back</button><button data-preview="play" class="primary">▶ Play line</button><button data-preview="next">Forward →</button><button data-preview="end">End ↦</button></div><div class="continuation-moves" aria-label="Preview moves"></div></div>';
 host.querySelector('h3').textContent=title;
 const boardNode=host.querySelector('.continuation-board');boardNode.id=hostId+'-board';
 const controls=Object.fromEntries([...host.querySelectorAll('[data-preview]')].map(e=>[e.dataset.preview,e]));
 const current={host,frames:data.frames,index:startAtEnd?data.frames.length-1:0,timer:null,sync};continuation=current;
 const moveButtons=data.frames.slice(1).map((f,i)=>{
  const b=document.createElement('button');b.textContent=`${i+1}. ${f.side} ${f.san}`;
  b.onclick=()=>{pause();current.index=i+1;draw();};host.querySelector('.continuation-moves').append(b);return b;
 });
 function pause(){if(current.timer)clearInterval(current.timer);current.timer=null;}
 function sync(){
  const last=current.frames.length-1;
  controls.start.disabled=controls.back.disabled=busy||current.index===0;
  controls.end.disabled=controls.next.disabled=busy||current.index===last;
  controls.play.disabled=busy||last===0;
  controls.play.textContent=current.timer?'❚❚ Pause':'▶ Play line';
  moveButtons.forEach((b,i)=>{b.disabled=busy;b.classList.toggle('active',i+1===current.index);b.setAttribute('aria-current',String(i+1===current.index));});
 }
 function draw(){
  if(!host.isConnected){stopContinuation();return;}
  const f=current.frames[current.index];board(boardNode.id,f.board);
  if(f.move)for(const square of [f.move.slice(0,2),f.move.slice(2,4)])boardNode.querySelector(`[data-square="${square}"]`)?.classList.add('preview-moved');
  const status=host.querySelector('.continuation-status');
  status.textContent=current.index===0?`Start · ${f.board.turn} to move · ${current.frames.length-1} ${prepared?'recorded':'searched'} half-moves`:`Step ${current.index} / ${current.frames.length-1} · ${f.side}: ${f.san} (${f.move}) · ${f.board.turn} to move${f.board.check?' · check':''}`;
  if(f.board.result)status.textContent+=` · ${f.board.result} · ${f.board.termination}${f.board.termination==='threefold repetition'?' (claimable draw accepted automatically)':''}`;
  sync();
 }
 function step(offset){pause();current.index=Math.max(0,Math.min(current.frames.length-1,current.index+offset));draw();}
 controls.start.onclick=()=>{pause();current.index=0;draw();};controls.back.onclick=()=>step(-1);
 controls.next.onclick=()=>step(1);controls.end.onclick=()=>{pause();current.index=current.frames.length-1;draw();};
 controls.play.onclick=()=>{
  if(current.timer){pause();sync();return;}
  if(current.index===current.frames.length-1)current.index=0;
  current.timer=setInterval(()=>{if(busy){pause();sync();return;}current.index++;if(current.index>=current.frames.length-1){current.index=current.frames.length-1;pause();}draw();},850);
  draw();
 };
 draw();
 if(reveal)revealContinuation(host);
}
