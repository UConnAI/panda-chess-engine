'use strict';
let bulkManagers=[];
let references={unlocked:false,available:[]};
let hintEngine='positional',ownHint=null;
let state,tab='play',busy=false,running=false,moves=[],pos,selected=null,bot='positional',depth=2,budget=3000,pruning=true,ordering=true,arena=null;
const labels={random:'Random Chess Player Panda 🐼',material:'🟢 Material Goblin',positional:'🔵 Positional Scout',champion:'🏆 Club Champion','reference-neural':'🐼 Prepared Neural Panda','reference-stockfish':'🐟 Stockfish reference'};
function name(id){const custom=(state?.custom_bots||[]).find(b=>b.id===id);if(custom)return '🛠 '+custom.name.replace(/[&<>"']/g,c=>'&#'+c.charCodeAt(0)+';')+' · '+custom.id;return id==='champion'?'🏆 Current champion · '+(labels[state.champion]||'🧠 '+state.champion):labels[id]||'🧠 '+id;}
function sortedModels(){return [...state.models].sort((a,b)=>a.validation.mse-b.validation.mse||a.id.localeCompare(b.id));}
function errorValue(n){return Number(n).toFixed(6);}
function modelLabel(m){return `${m.id} · MSE ${errorValue(m.validation.mse)} · ${m.count} positions · ${m.epoch} epochs${m.id===sortedModels()[0]?.id?' · ★ lowest error':''}`;}
function options(value,includeChampion=true){return ['random','material','positional',...(includeChampion?['champion']:[]),...(state.custom_bots||[]).map(b=>b.id),...sortedModels().map(m=>m.id),...(references.unlocked?references.available:[])].map(id=>{const m=state.models.find(m=>m.id===id);return `<option value="${id}" ${value===id?'selected':''}>${m?modelLabel(m):name(id)}</option>`;}).join('');}
function lock(on){document.querySelectorAll('button,select,input').forEach(e=>{if(!e.closest('#result-flash'))e.disabled=on;});syncControls(on);syncContinuation();syncBulkManagers();if($('arena-explore')?.dataset.ended==='true')$('arena-explore').disabled=true;}
async function act(fn){if(busy)return;busy=true;lock(true);$('error').hidden=true;$('working').textContent='Working… actual engine computation';try{await fn();}catch(e){$('error').hidden=false;$('error').textContent=e.message;running=false;}finally{busy=false;lock(false);$('working').textContent='';}}
function resultFlash(title,detail='',autoDismiss=0){
 if(!autoDismiss)running=false;
 $('result-flash')?.remove();
 const previousFocus=document.activeElement;
 let timer,resolveClosed;const closed=new Promise(resolve=>{resolveClosed=resolve;});
 const flash=document.createElement('dialog');flash.id='result-flash';flash.className='result-flash';flash.setAttribute('aria-labelledby','result-title');flash.setAttribute('aria-describedby','result-detail');
 const card=document.createElement('div');card.className='result-flash-card';
 const icon=document.createElement('span');icon.className='result-flash-icon';icon.textContent='🐼';icon.setAttribute('aria-hidden','true');
 const heading=document.createElement('h2');heading.id='result-title';heading.textContent=title;
 const description=document.createElement('p');description.id='result-detail';description.textContent=detail;
 const dismiss=document.createElement('button');dismiss.className='result-dismiss';dismiss.textContent=autoDismiss?'Continue now · closes automatically in 2 seconds':'Dismiss — back to the board';dismiss.onclick=()=>flash.close();
 flash.addEventListener('cancel',event=>{event.preventDefault();flash.close();});
 flash.addEventListener('close',()=>{clearTimeout(timer);flash.remove();if(previousFocus?.isConnected&&!previousFocus.disabled)previousFocus.focus();resolveClosed();});
 card.append(icon,heading,description,dismiss);flash.append(card);document.body.append(flash);flash.showModal();dismiss.focus();
 if(autoDismiss)timer=setTimeout(()=>{if(flash.open)flash.close();},autoDismiss);
 return autoDismiss?closed:undefined;
}
function outcomeFlash(result,termination,human=false,side='The player to move',autoDismiss=0,context=''){
 if(!result||result==='*')return;
 // Play uses readable lowercase reasons; arena exports enum-style uppercase reasons.
 termination=String(termination||'').trim().toUpperCase().replace(/[ -]+/g,'_');
 const winner=result==='1-0'?(human?'You win!':'White wins!'):result==='0-1'?(human?'You lose — Panda wins':'Black wins!'):'Draw';
 const title=termination==='STALEMATE'?'Stalemate — draw':termination==='CHECKMATE'?'Checkmate — '+winner:winner;
 const explanations={
  STALEMATE:`${side} has no legal move, but their king is NOT in check. Neither the king nor any other piece can make a legal move. Chess calls this stalemate, so the game is a draw—even if the other player has more pieces. Checkmate is different: the king must be in check and unable to escape.`,
  CHECKMATE:`${side} is in check and has no legal move that removes the threat to the king. This is checkmate, so the other side wins.`,
  INSUFFICIENT_MATERIAL:'The remaining pieces cannot produce checkmate. The game is a draw.',
  THREEFOLD_REPETITION:'The same position has occurred three times with the same player to move and the same legal possibilities. This demo claims the available draw.',
  FIFTY_MOVES:'Fifty moves by each player have passed without a pawn move or capture. This demo claims the available draw.',
  FIVEFOLD_REPETITION:'The same position has occurred five times. Chess rules end the game as a draw.',
  SEVENTYFIVE_MOVES:'Seventy-five moves by each player have passed without a pawn move or capture. Chess rules end the game as a draw.'
 };
 return resultFlash(context?context+' · '+title:title,(explanations[termination]||String(termination||'Game finished').replaceAll('_',' ').toLowerCase())+(context?' Result saved to Arena history.':''),autoDismiss);
}
function gameResultFlash(){outcomeFlash(pos.result,pos.termination,true,pos.turn);}
function head(){ $('champion').textContent='Champion: '+name(state.champion)+' · unrated';document.querySelectorAll('[data-tab]').forEach(b=>{b.classList.toggle('active',b.dataset.tab===tab);b.setAttribute('aria-pressed',String(b.dataset.tab===tab));});}
async function showBase(t){tab=t;head();if(t==='play'){
$('stage').innerHTML=`<div class="layout"><section class="panel"><div class="controls"><label>Opponent<select id="bot" aria-label="Opponent">${options(bot)}</select></label><label>Depth<select id="depth" aria-label="Depth">${[1,2,3,4].map(n=>`<option ${n===depth?'selected':''}>${n}</option>`).join('')}</select></label><label>Node budget<select id="budget" aria-label="Node budget">${[300,1000,3000,10000,30000].map(n=>`<option ${n===budget?'selected':''}>${n}</option>`).join('')}</select></label></div><div id="board" class="board"></div><p id="turn" class="status" role="status"></p><div class="controls"><button id="new">New game</button><button id="undo">Undo turn</button><button id="move" class="primary">Engine turn →</button><button id="save">Save club game</button></div><p id="save-result" class="status"></p><p class="muted">You play White. Promotion defaults to queen. Scores favor White. No game trains the network automatically.</p></section><section class="panel"><h2>Watch the machine work.</h2><div class="controls"><label><input id="pruning" type="checkbox" ${pruning?'checked':''}> Alpha-beta pruning</label><label><input id="ordering" type="checkbox" ${ordering?'checked':''}> Move ordering</label><label>Your hint engine<select id="hint-engine" aria-label="Your hint engine">${options(hintEngine).replace(/<option value="random"[^>]*>.*?<\/option>/,'')}</select></label><button id="analyze" class="primary">Preview my best move</button><button id="analyze-reply">Preview opponent’s reply</button></div><div id="telemetry"><p class="empty">Pick a bot, analyze, then change one search setting.</p></div><div id="branch"></div><details><summary>Moves played</summary><p id="history"></p></details></section></div>`;
$('bot').onchange=()=>{bot=$('bot').value;resetInspection();};$('depth').onchange=()=>{depth=Number($('depth').value);resetInspection();};$('budget').onchange=()=>{budget=Number($('budget').value);resetInspection();};$('pruning').onchange=()=>{pruning=$('pruning').checked;resetInspection();};$('ordering').onchange=()=>{ordering=$('ordering').checked;resetInspection();};
$('new').onclick=()=>act(async()=>{moves=[];await refresh();});$('undo').onclick=()=>act(async()=>{moves.splice(Math.max(0,moves.length-(moves.length%2?1:2)));await refresh();});$('move').onclick=()=>act(engineMove);$('hint-engine').onchange=()=>{hintEngine=$('hint-engine').value;resetInspection();syncControls();};$('analyze').onclick=()=>act(previewMyMove);$('analyze-reply').onclick=()=>act(previewOpponentReply);$('save').onclick=()=>act(async()=>{const r=await api('save-game',{moves,kind:bot});$('save-result').innerHTML=`Saved <a href="/pgn/${r.file}" target="_blank">${r.file} ↗</a> · ${r.result} · not used for training`;});lock(true);await refresh();
}else if(t==='train'){
arena=await api('arena');
$('stage').innerHTML=`<div class="layout"><section class="panel wide"><h2>Train an actual neural evaluator.</h2><div class="flow"><span>12 piece-location planes<small>+ turn, castling, en passant, clock</small></span>→<span>32 hidden neurons</span>→<span>Bounded position score<small>not a win probability</small></span></div><p class="muted">${state.architecture}. Targets are saved engine scores transformed with tanh(cp / 400). All earlier chess demos stay separate.</p><div class="controls"><label>Positions<select id="count" aria-label="Training positions">${[200,800,1600,3199].map(v=>`<option ${v===(state.count||800)?'selected':''}>${v}</option>`).join('')}</select></label><label>Step size<select id="rate" aria-label="Learning rate">${[.001,.005,.01].map(v=>`<option ${v===(state.rate||.01)?'selected':''}>${v}</option>`).join('')}</select></label><label>Epochs<select id="epochs" aria-label="Epochs"><option>1</option><option selected>10</option><option>30</option></select></label><button id="fresh" class="primary">Train a fresh network</button><button id="continue">Continue saved network</button></div><p class="instruction">Each training action saves a new version. Previous versions remain available.</p></section><section class="panel"><h3>One example: prediction before and after</h3><div id="train-board" class="board"></div><div id="trace"></div></section><section class="panel"><h3>Training result — lower error is better</h3><div id="training-result"></div><h3>Saved model versions</h3><div id="models"></div><details><summary>Advanced: final held-out evaluation</summary><p class="muted">Use after model selection. Revealing it flags it as exposed. Validation has 400 positions; related positions may cross splits.</p><button id="test">Reveal test score</button><p id="test-result"></p></details></section></div>`;
for(const id of ['fresh','continue'])$(id).onclick=()=>act(async()=>{state=await api('train',{count:Number($('count').value),rate:Number($('rate').value),epochs:Number($('epochs').value),resume:id==='continue'});head();renderTraining();});$('test').onclick=()=>act(async()=>{const r=await api('test',{});$('test-result').textContent=`Normalized test MSE ${fmt(r.mse)} · now exposed`;});renderTraining();
}else if(t==='arena'){
arena=await api('arena');$('stage').innerHTML=`<div class="layout"><section class="panel wide"><h2>Challenger vs champion.</h2><div class="controls"><label>Challenger<select id="candidate" aria-label="Challenger">${options(state.ready?state.id:'material',false)}</select></label><label>Opponent<select id="opponent" aria-label="Arena opponent">${options('champion')}</select></label><label>Games<select id="games" aria-label="Arena games"><option>2</option><option>10</option><option>40</option></select></label><label>Depth<select id="arena-depth" aria-label="Arena depth"><option selected>1</option><option>2</option><option>3</option></select></label><label>Nodes / move<select id="arena-budget" aria-label="Arena node budget"><option>300</option><option selected>1000</option><option>3000</option></select></label><label>Extra ply cap<select id="cap" aria-label="Arena move cap"><option selected>40</option><option>100</option><option>200</option></select></label><button id="start" class="primary">Start a new arena</button></div><p class="muted">Paired openings, colors swapped, fixed saved model IDs, equal node caps. Random Chess Player Panda 🐼 uses no search. Equal nodes do not mean equal runtime.</p></section><section class="panel"><div class="controls"><button id="step">One turn →</button><button id="run" class="primary">Run / resume ▶</button><button id="pause">Pause</button></div><div id="arena-board" class="board"></div><p id="arena-status" role="status"></p></section><section class="panel"><div id="scoreboard"></div><button id="promote">Promote if eligible</button><p class="muted">Requires 40 completed games against the current champion, no capped games, and a paired 95% bootstrap score interval above 50%. The gate is a development check, not a human rating.</p><div id="results"></div></section><section class="panel wide"><h3>Permanent arena history</h3><p id="arena-storage" class="muted"></p><div id="arena-history"></div></section><section id="arena-replay" class="panel wide" hidden><h2 id="arena-replay-title"></h2><p id="arena-replay-players"></p><p id="arena-replay-note" class="muted"></p><button id="arena-explore" hidden>Explore one extra move</button><div id="arena-replay-player"></div></section></div>`;
$('start').onclick=()=>act(async()=>{arena=await api('arena/start',{candidate:$('candidate').value,opponent:$('opponent').value,games:Number($('games').value),depth:Number($('arena-depth').value),budget:Number($('arena-budget').value),cap:Number($('cap').value)});renderArena();});$('step').onclick=()=>act(()=>arenaStep(false));$('run').onclick=()=>act(async()=>{if(!arena.active)throw Error('Start an arena first.');running=true;while(running&&!arena.run.finished){await arenaStep(true);await new Promise(r=>setTimeout(r,30));}running=false;});$('pause').onclick=()=>{running=false;$('working').textContent='Pausing after this move…';syncControls(busy);};$('promote').onclick=()=>act(async()=>{arena=await api('arena/promote',{});state=await api('status');head();renderArena();});renderArena();
}lock(busy);}
function randomOpponent(){return (bot==='champion'?state.champion:bot)==='random';}
function resetInspection(){stopContinuation();ownHint=null;if($('telemetry'))$('telemetry').innerHTML=`<p class="empty">${randomOpponent()?'Preview your best move or Panda’s random reply.':'Preview your best move, then inspect the opponent’s reply.'}</p>`;if($('branch'))$('branch').innerHTML='';}
async function refresh(){pos=(await api('board',{moves})).board;selected=null;renderBoard();resetInspection();}
function renderBoard(){board('board',pos,sq=>act(()=>clickSquare(sq)),selected);$('turn').textContent=pos.result?`${pos.result} · ${pos.termination}`:`${pos.turn} to move${pos.check?' · CHECK':''}${pos.turn==='Black'?' · waiting for bot reply':''}`;$('history').textContent=moves.join(' · ')||'No moves.';lock(busy);}
async function playHumanMove(move){if(pos.result||pos.turn!=='White'||!pos.legal_moves.includes(move))throw Error('That move is not legal in this position.');moves.push(move);await refresh();if(!pos.result)await engineMove();else gameResultFlash();}
async function clickSquare(sq){if(pos.result||pos.turn!=='White')return;const move=selected?selectedMove(pos,selected,sq):null;if(move){await playHumanMove(move);}else{selected=pos.legal_moves.some(m=>m.startsWith(sq))?sq:null;renderBoard();}}
async function engineMove(){if(pos.result)return;const base=moves.slice(),r=await api('move',{moves,kind:bot,depth,budget,pruning,ordering});if(r.search.move)moves.push(r.search.move);pos=r.board;selected=null;renderBoard();await renderSearch(r.search,base,{title:'Opponent played · Black'});gameResultFlash();}
function explain(label,text,id,end=false){return `<span class="info-tip ${end?'tip-end':''}" tabindex="0" aria-describedby="${id}">${label} <span aria-hidden="true">ⓘ</span><span id="${id}" class="tip-text" role="tooltip">${text}</span></span>`;}
function candidateScore(n){return n===null?'—':Math.abs(n)>9000?(n>0?'Mate for White':'Mate for Black'):(n>0?'+':'')+fmt(n);}
async function computeOwnHint(){
 if(!pos||pos.result||pos.turn!=='White')throw Error('Your hint is available on White’s turn.');
 if(ownHint?.history===JSON.stringify(moves))return ownHint;
 const r=await api('analyze',{moves,kind:hintEngine,depth,budget,pruning,ordering});
 ownHint={history:JSON.stringify(moves),search:r.search};return ownHint;
}
async function previewMyMove(){const h=await computeOwnHint();await renderSearch(h.search,moves.slice(),{title:'Your best move · White',reveal:true});}
async function previewOpponentReply(){
 const base=moves.slice();let prefix=[],title='Opponent’s choice · Black';
 if(pos.turn==='White'){
  const h=await computeOwnHint();
  if(!h.search.move)return;
  prefix=[h.search.move];title=`Opponent’s reply · Black, after your suggested ${h.search.san}`;
 }
 const r=await api('analyze',{moves:base.concat(prefix),kind:bot,depth,budget,pruning,ordering});
 await renderSearch(r.search,base,{prefix,title,reveal:true});
}
async function renderSearch(r,base,context={}){
 stopContinuation();$('branch').innerHTML='';
 const prefix=context.prefix||[],role=context.title||'Searched move';
 const candidates=r.engine==='random'?[]:r.candidates;
 const intro=`<p class="preview-role">${role}</p><h3>${name(r.engine)} chooses ${r.san||'no legal move'}</h3>`;
 if(r.engine==='random'){
  $('telemetry').innerHTML=intro+'<p>Random Panda chooses a legal reply without ranking or scoring moves.</p>';
 }else{
  $('telemetry').innerHTML=intro+metrics([['Completed depth',r.external?r.depth:`${r.depth} / ${r.requested_depth}`],['Nodes visited',r.nodes],['Leaf evaluations',r.evaluated]])+metrics([['Cutoff events',r.cutoffs],['Immediate moves skipped',r.moves_skipped],['Seconds',r.seconds]])+
   `<p class="${r.budget_hit?'warning':'muted'}">${r.external?'Stockfish uses its own 0.3-second search. Unavailable counters are shown as —.':r.budget_hit?'Budget reached. Showing the last fully completed search.':'Requested search completed.'}</p><h3>Candidate moves — click one to inspect</h3><p class="muted">Inspect the chosen line below. Each step is one White or Black move; your game stays unchanged.</p><table class="candidate-table"><tr><th>${explain('Move','Legal choices for the side identified above. Click to preview this candidate.','move-help')}</th><th>${explain('Score','Estimated position after searched replies. Positive favors White; negative favors Black. These are evaluator estimates, not win percentages.','score-help')}</th><th>${explain('Continuation','Step through a possible searched line using Back, Forward, or Play line. Both sides alternate. The line stops at the search horizon.','line-help',true)}</th></tr>${candidates.map((c,i)=>`<tr><td><button data-branch="${i}">${c.san}</button></td><td>${candidateScore(c.score)}</td><td><button data-branch="${i}">Preview ${prefix.length+c.pv.length} half-moves →</button></td></tr>`).join('')}</table>`;
 }
 const inspect=(c,reveal=false)=>previewContinuation('branch',{moves:[...base]},prefix.concat(c.pv),`${role} · line starting ${c.san||'at this position'}`,null,false,reveal);
 document.querySelectorAll('[data-branch]').forEach(b=>b.onclick=()=>act(()=>inspect(candidates[Number(b.dataset.branch)],true)));
 await inspect(candidates[0]||r,!!context.reveal);
 lock(busy);
}

function renderTrainingBase(){if(!state.ready){$('trace').innerHTML='<p class="empty">Train your first network.</p>';$('training-result').innerHTML='No saved neural model yet.';$('models').innerHTML='';return;}const t=state.trace;board('train-board',t.board);$('trace').innerHTML=metrics([['Before action',fmt(t.before)],['After action',fmt(t.after)],['Target',fmt(t.target)]])+`<p class="muted">Teacher ${t.teacher_cp} centipawns → normalized target ${fmt(t.target)}. One inspected board does not determine the whole batch update.</p>`;$('training-result').innerHTML=plot(state.history)+'<p class="muted">Training error measures practice boards. Validation error checks 400 separate boards. Lower error means closer teacher predictions, not necessarily more wins.</p>'+metrics([['Saved version',state.id],['Epoch',state.epoch],['Validation MSE',fmt(state.validation.mse)]]);lock(busy);}
async function arenaStep(autoPlay=false){
 const previous=arena?.run?.results.length||0;
 arena=await api('arena/step',{});renderArena();
 if(arena.run.results.length>previous){
  const g=arena.run.results.at(-1);
  await outcomeFlash(g.result,g.reason,false,g.moves.length%2?'Black':'White',autoPlay?2000:0,`Game ${g.game}/${arena.run.games}${arena.run.finished?' · Match complete':''}`);
 }
}
function pgnHelp(){
 return '<details class="advanced pgn-help"><summary>What is a PGN file?</summary><p>PGN means Portable Game Notation: a small text file containing the players, moves and result. Download it to replay or analyze the game in a compatible chess app. It stores the game, not the neural model.</p><p><strong>1-0</strong> = White wins · <strong>0-1</strong> = Black wins · <strong>1/2-1/2</strong> = draw · <strong>*</strong> = unfinished. Saving a PGN does not train Panda.</p></details>';
}
function arenaScoreRows(run){
 const s=run.summary;
 return `<table class="arena-score-table"><caption>Results by player · colors swap between games</caption><thead><tr><th>Player</th><th>Wins</th><th>Draws</th><th>Losses</th></tr></thead><tbody><tr><th scope="row"><small>Challenger</small>${name(run.candidate)}</th><td>${s.wins}</td><td>${s.draws}</td><td>${s.losses}</td></tr><tr><th scope="row"><small>Opponent</small>${name(run.opponent)}</th><td>${s.losses}</td><td>${s.draws}</td><td>${s.wins}</td></tr></tbody></table><p class="arena-unfinished"><strong>${s.unfinished} unfinished ${s.unfinished===1?'game':'games'}</strong><span>Games stopped at the move limit are excluded from wins, draws and losses</span></p>`;
}
function arenaHistoryCard(run){
 const s=run.summary;
 return `<details class="arena-history-card"><summary><span><strong>${run.id}</strong> · ${name(run.candidate)} vs ${name(run.opponent)}</span><span class="arena-history-totals">Challenger: ${s.wins} wins · ${s.draws} draws · ${s.losses} losses · ${s.unfinished} unfinished ${s.unfinished===1?'game':'games'}</span><span class="arena-schedule">${run.finished?'Schedule complete':'Schedule in progress'}</span></summary>${arenaScoreRows(run)}<p class="muted">Saved files: ${modelFileSize(run.size_bytes||0)} · match record and PGN downloads</p><div class="controls"><button data-arena-record="${run.id}">Browse games & replay</button><button data-delete-arena="${run.id}" class="danger">Delete history permanently</button></div><div class="arena-record-games"></div></details>`;
}
async function openArenaReplay(id,game){
 const data=await api('arena/replay',{id,game});
 $('arena-replay').hidden=false;
 $('arena-replay-title').textContent=`${id} · Game ${game} replay`;
 $('arena-replay-players').textContent=`White: ${name(data.white)} · Black: ${name(data.black)}`;
 $('arena-replay-note').textContent='Recorded moves · replay does not change match results. Extra moves stop at a game ending or 600 total half-moves.';
 await previewContinuation('arena-replay-player',{},[],`Recorded game ${game}`,data);
 const replayCard=$('arena-replay');
 replayCard.tabIndex=-1;
 replayCard.setAttribute('aria-labelledby','arena-replay-title');
 replayCard.focus({preventScroll:true});
 replayCard.scrollIntoView({behavior:window.matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth',block:'start'});
 const more=$('arena-explore');more.hidden=data.game.score!==null;
 let extra=0;
 more.title='Continues from the latest end position using the original opponents. Their saved models must still exist; reference engines must be revealed. Changes are preview-only.';
 function updateExtraStatus(b){
  const capped=data.game.moves.length>=600;
  more.dataset.ended=String(!!b.result||capped);
  more.disabled=!!b.result||capped;
  if(b.result){const reason=b.termination==='threefold repetition'?'Draw by threefold repetition: the same position can occur for the third time, with the same player to move and the same legal rights. Claimable draws are accepted automatically.':`${b.result} · ${b.termination}`;$('arena-replay-note').textContent+=' Exploration ended: '+reason;}
  else if(capped)$('arena-replay-note').textContent+=' Exploration stopped at the 600-total-half-move safety limit.';
 }
 updateExtraStatus(data.frames.at(-1).board);
 more.onclick=()=>act(async()=>{
  const last=data.frames.at(-1),history=data.game.moves;
  const r=await api('move',{moves:history,kind:last.board.turn==='White'?data.white:data.black,depth:data.depth,budget:data.budget});
  if(!r.search.move){updateExtraStatus(r.board);return;}
  history.push(r.search.move);extra++;
  data.frames.push({board:r.board,move:r.search.move,san:r.search.san,side:last.board.turn});
  await previewContinuation('arena-replay-player',{},[],`Exploration · ${extra} extra half-move${extra===1?'':'s'}`,data,true);
  $('arena-replay-note').textContent=`Exploration only · ${extra} extra half-move${extra===1?'':'s'} after the recorded game. Original match results stay unchanged.`;
  updateExtraStatus(r.board);
 });
}
function confirmArenaDelete(id){
 const record=arena.history.find(r=>r.id===id);if(!record)return;
 const dialog=document.createElement('dialog');dialog.className='result-flash';
 dialog.setAttribute('aria-labelledby','arena-delete-title');
 dialog.innerHTML='<div class="result-flash-card"><h2 id="arena-delete-title"></h2><p></p><div class="controls"><button data-cancel>Cancel</button><button data-confirm class="danger">Delete permanently</button></div></div>';
 dialog.querySelector('h2').textContent=`Permanently delete ${id}?`;
 dialog.querySelector('p').textContent=`Erase this match record and all its PGN files (${modelFileSize(record.size_bytes)}, ${record.size_bytes.toLocaleString()} bytes)? This bypasses your system’s trash and cannot be restored through the app. Models and other matches are kept. If this is the current match, it will be cleared.`;
 dialog.querySelector('[data-cancel]').onclick=()=>dialog.close();
 dialog.querySelector('[data-confirm]').onclick=()=>{dialog.close();act(async()=>{running=false;stopContinuation();arena=await api('arena/delete',{id});await show('arena');});};
 dialog.onclose=()=>dialog.remove();document.body.append(dialog);dialog.showModal();dialog.querySelector('[data-cancel]').focus();
}
function bindArenaHistory(){
 document.querySelectorAll('[data-delete-arena]').forEach(button=>button.onclick=()=>confirmArenaDelete(button.dataset.deleteArena));
 document.querySelectorAll('[data-arena-record]').forEach(button=>button.onclick=()=>act(async()=>{
  const r=await api('arena/record',{id:button.dataset.arenaRecord});
  const host=button.closest('.arena-history-card').querySelector('.arena-record-games');host.replaceChildren();
  for(const g of r.results){
   const row=document.createElement('div');row.className='arena-record-game-row';
   const replay=document.createElement('button');replay.textContent=`Replay game ${g.game} · ${g.score===null?'Unfinished':g.result}`;
   replay.onclick=()=>act(()=>openArenaReplay(r.id,g.game));
   const download=document.createElement('a');download.href=`/pgn/${r.id}-game-${String(g.game).padStart(3,'0')}.pgn`;download.target='_blank';download.textContent='PGN ↗';
   row.append(replay,download);host.append(row);
  }
  if(!r.results.length)host.textContent='No recorded games yet.';
 }));
 document.querySelectorAll('[data-arena-replay]').forEach(button=>button.onclick=()=>act(()=>openArenaReplay(arena.run.id,Number(button.dataset.arenaReplay))));
}
function renderArenaBase(){
 if(arena.active){
  const r=arena.run,s=arena.summary;board('arena-board',arena.board);
  $('arena-status').textContent=`${r.id} · ${r.finished?'Schedule complete':`Game ${r.index+1}/${r.games}, ply ${r.moves.length}`}`;
  $('scoreboard').innerHTML=`<h2>Match scorecard</h2><p class="muted">${r.results.length} / ${r.games} games recorded to history${r.finished?' · Schedule complete':''}</p>`+arenaScoreRows({...r,summary:s});
  $('results').innerHTML=pgnHelp()+'<details class="arena-game-list"><summary>Game results & replay ('+r.results.length+')</summary>'+r.results.map(g=>{
   const white=g.candidate_color==='White'?r.candidate:r.opponent,black=g.candidate_color==='Black'?r.candidate:r.opponent;
   const result=g.score===null?'Unfinished · move limit':g.score===.5?'Draw':`${name(g.score===1?r.candidate:r.opponent)} won`;
   return `<article class="arena-game-result"><button data-arena-replay="${g.game}">Replay game ${g.game}</button> <a href="/pgn/${r.id}-game-${String(g.game).padStart(3,'0')}.pgn" target="_blank">Game ${g.game} · Download PGN ↗</a><p><strong>White:</strong> ${name(white)}<br><strong>Black:</strong> ${name(black)}</p><strong>${result}</strong><p class="muted">${g.score===null?'No winner or draw recorded.':g.reason.replaceAll('_',' ').toLowerCase()}</p></article>`;
  }).join('')+'</details>';
 }else{
  $('arena-status').textContent='Start an arena.';$('scoreboard').textContent='Results appear after games finish.';
 }
 $('arena-history').innerHTML=[...arena.history].reverse().map(arenaHistoryCard).join('')||'No previous runs.';
 $('arena-storage').textContent=`${arena.history.length} saved matches · ${modelFileSize(arena.history.reduce((total,r)=>total+(r.size_bytes||0),0))} total on disk`;
 bulkDeleteManager($('arena-history'),arena.history,'arena');
 bindArenaHistory();
 lock(busy);
}

document.querySelectorAll('[data-tab]').forEach(b=>b.onclick=()=>act(()=>show(b.dataset.tab)));act(async()=>{state=await api('status');await show(document.body.dataset.personal?'studio':'play');});


// Short contextual guidance is shared with the standalone application.
function help(id,title,text){
 const box=document.createElement('div');box.id=id;box.className='action-guide';
 box.innerHTML=`<strong>${title}</strong><p>${text}</p>`;return box;
}
function advanced(title,elements,explanation){
 const details=document.createElement('details');details.className='advanced';
 details.innerHTML=`<summary>${title}</summary><p class="muted">${explanation}</p>`;
 const controls=document.createElement('div');controls.className='controls';details.append(controls);
 elements.forEach(e=>{if(e)controls.append(e);});return details;
}
function hint(id,text){const e=$(id);if(!e)return;const small=document.createElement('small');small.className='field-help';small.textContent=text;e.closest('label').append(small);}
function reason(id,blocked,message,on){const e=$(id);if(e){e.disabled=on||blocked;e.title=blocked?message:'';e.setAttribute('aria-disabled',String(e.disabled));}}
function modelDeleteReason(id){
 if(id===state.champion)return 'This is the current champion. Promote another model before deleting it.';
 if(arena?.active&&!arena.run.finished&&[arena.run.candidate,arena.run.opponent].includes(id))return 'This model is used by an unfinished arena match. Finish it or prepare a different match first.';
 return '';
}
function updateOpponentPortrait(){
 if(!$('opponent-seat'))return;
 const kind=bot==='champion'?state.champion:bot;
 const portraits={random:'🐼',material:'👺',positional:'🧭','reference-neural':'🐼','reference-stockfish':'🐟'};
 $('opponent-portrait').textContent=bot==='champion'?'👑':portraits[kind]||(kind.startsWith('custom-')?'🛠':'🤖');
 $('opponent-name').textContent=name(bot);
 $('opponent-role').textContent='Opponent · Black'+(bot==='champion'?' · '+name(kind):'');
 $('opponent-seat').dataset.kind=bot==='champion'?'champion':portraits[kind]?kind:kind.startsWith('custom-')?'custom':'neural';
 $('champion-help').hidden=bot!=='champion';
 $('champion-help').textContent=`Champion is a title. It currently uses ${name(kind)}. Choosing that bot directly gives the same opponent. A saved neural bot can take the title after passing the arena promotion test.`;
 const model=state.models.find(m=>m.id===kind);
 $('neural-help').hidden=!model;
 if(model)$('neural-help-text').textContent=`${model.id}: validation MSE ${errorValue(model.validation.mse)} (lower means closer teacher predictions, not stronger chess). ${model.count} practice positions, ${model.epoch} training passes (${model.epoch} weight updates in this demo). It learns to predict saved teacher scores, then search uses those predictions to choose a move. It can still miss free pieces or prefer bad trades. Playing you does not update it. More training may help; arena games are needed to check whether it actually plays better.`;
}
function syncControls(on=busy){
 if(tab==='references'){reason('reveal-references',!references.eligible,'Train a model and finish an arena trial first.',on);return;}
 if(tab==='play'){
  updateOpponentPortrait();
  reason('undo',!moves.length,'Make a move first.',on);reason('save',!moves.length,'Make a move before saving.',on);
  reason('move',!pos||!!pos.result||pos.turn!=='Black','The bot replies automatically after your move.',on);
  reason('analyze',!pos||!!pos.result||pos.turn!=='White','Your hint is available on White’s turn.',on);reason('analyze-reply',!pos||!!pos.result,'Start a new game to preview a reply.',on);
  if($('play-next'))$('play-next').textContent=pos?.result?'Game finished. Start a new game or save this one.':pos?.turn==='Black'?'Black is to move. Use Resume bot reply if a reply was interrupted.':selected?'Now click a highlighted destination. The bot will reply automatically.':'Your turn: click a White piece, then a highlighted square. The bot replies automatically.';
  const random=randomOpponent();
  if($('analyze'))$('analyze').textContent='Preview my best move';
  if($('analyze-reply'))$('analyze-reply').textContent=random?'Preview Panda’s random reply':'Preview opponent’s reply';
  if($('analyze-guide'))$('analyze-guide').querySelector('p').textContent=`Your hint uses ${name(hintEngine)} for White. Reply preview uses ${name(bot)} for Black after your suggested move. Both are preview-only.`;
  for(const id of ['depth','budget','pruning','ordering'])reason(id,false,'',on);
  const playable=!!pos&&!pos.result&&pos.turn==='White'&&!on;
  if($('board')){$('board').classList.toggle('waiting',!playable);$('board').querySelectorAll('button').forEach(e=>e.disabled=!playable);}
  if($('board-mode'))$('board-mode').textContent=pos?.result?'GAME FINISHED · Start a new game':on?'PLEASE WAIT · Computing the move':pos?.turn==='Black'?'BOT’S TURN · Board temporarily locked':'PLAY HERE · Your turn as White';
  if($('castle-controls')){
   const legalCastles=castlingMoves(pos);$('castle-controls').hidden=!legalCastles.length;
   reason('castle-short',!legalCastles.includes('e1g1'),'Kingside castling is not legal in this position.',on);
   reason('castle-long',!legalCastles.includes('e1c1'),'Queenside castling is not legal in this position.',on);
   $('castle-short').hidden=!legalCastles.includes('e1g1');$('castle-long').hidden=!legalCastles.includes('e1c1');
   if(selected==='e1'&&legalCastles.length&&$('play-next'))$('play-next').textContent='Castling is available: click g1 or c1, click the matching rook, or use a Castle button. The rook moves automatically.';
  }
 }
 if(tab==='train'&&$('count')){
  for(const id of ['try-model','test-match'])reason(id,!state.ready,'Train a model first.',on);
  const same=state.ready&&Number($('count').value)===state.count&&Number($('rate').value)===state.rate;
  const capped=state.ready&&state.epoch+Number($('epochs').value)>300;
  const why=!state.ready?'Train a first model before continuing.':!same?'To continue, restore the loaded model’s example count and learning rate. Or start a new model with these settings.':capped?'This would exceed the 300-epoch limit. Start a new model instead.':`Continue ${state.id} from ${state.epoch} to ${state.epoch+Number($('epochs').value)} epochs; save a new version.`;
  reason('continue',!same||capped,why,on);const deleteReason=modelDeleteReason($('model')?.value);reason('delete-model',!!deleteReason,deleteReason,on);reason('test',!state.ready,'Train or load a model first.',on);
  if($('continue-help'))$('continue-help').textContent=why;
  $('continue').textContent=state.ready?`Train ${Number($('epochs').value)} more epochs`:'Continue training';
  $('continue').classList.toggle('primary',!!same&&!capped);$('fresh').classList.toggle('primary',!state.ready);
  if($('train-next'))$('train-next').textContent=state.ready?`${state.id} is saved (${state.epoch} epochs). Continue it, or try it in a game or match.`:'Start with the recommended settings. Train first, then inspect the result below.';
 }
 if(tab==='arena'&&$('candidate')){
  const resolve=id=>id==='champion'?state.champion:id;
  const same=resolve($('candidate').value)===resolve($('opponent').value);
  const active=arena?.active&&!arena.run.finished;
  reason('start',same,'Choose two different opponents.',on);
  reason('run',!active,'Prepare a match first, or start a new match after this one finishes.',on);
  reason('step',!active,'Prepare a match first.',on);
  if($('pause'))$('pause').disabled=!running;
  const canPromote=arena?.active&&arena.summary.promotable&&arena.run.candidate.startsWith('neural-')&&arena.run.opponent===state.champion;
  reason('promote',!canPromote,'Requires a qualifying 40-game match against the current champion.',on);
  if($('arena-next'))$('arena-next').textContent=same?'Choose two different opponents before preparing a match.':running?'Match running. Pause stops after the current move.':active?'Match ready. Press Play match automatically, or inspect one move at a time.':arena?.active?'Match finished. Review wins, losses and unfinished games below; prepare another when ready.':'Choose the model to test, then Prepare a 2-game match. The default is a short trial, not a strength rating.';
  $('start').textContent=`Prepare a ${$('games').value}-game match`;
 }
}
async function show(t){stopContinuation();if(t==='studio'&&typeof showPersonalStudio==='function'){tab=t;head();await showPersonalStudio();return;}if(t==='references'){await showReferences();return;}await showBase(t);decorate();lock(busy);}
function decorate(){
 if(tab==='play'){
  const panel=$('board').closest('.panel');panel.prepend(help('play-guide','Play as White','Click a piece and a highlighted destination. No separate start button is needed.'));
  const seat=document.createElement('div');seat.id='opponent-seat';seat.className='opponent-seat';
  seat.innerHTML='<span id="opponent-portrait" class="opponent-portrait" aria-hidden="true"></span><div><small id="opponent-role"></small><strong id="opponent-name"></strong></div>';
  $('board-mode').before(seat);
  const championHelp=document.createElement('p');championHelp.id='champion-help';championHelp.className='muted champion-help';seat.after(championHelp);
  const neuralHelp=document.createElement('details');neuralHelp.id='neural-help';neuralHelp.className='neural-help';neuralHelp.innerHTML='<summary>About this learning bot — why it can blunder</summary><p id="neural-help-text"></p>';championHelp.after(neuralHelp);
  const castleControls=document.createElement('div');castleControls.id='castle-controls';castleControls.className='castle-controls';castleControls.hidden=true;
  castleControls.innerHTML='<strong>Castling is available</strong><div class="controls"><button id="castle-short">Castle short · O-O</button><button id="castle-long">Castle long · O-O-O</button></div><small>The king moves two squares; the rook moves beside it automatically.</small>';
  $('board').after(castleControls);
  $('castle-short').onclick=()=>act(()=>playHumanMove('e1g1'));$('castle-long').onclick=()=>act(()=>playHumanMove('e1c1'));
  const castleHelp=document.createElement('details');castleHelp.className='castling-help';castleHelp.innerHTML='<summary>How does castling work?</summary><p>Castling moves your king and one rook in the same turn. For White: short castling moves the king e1 → g1 and rook h1 → f1; long castling moves the king e1 → c1 and rook a1 → d1.</p><p>The king and that rook must never have moved, the squares between them must be empty, and the king cannot be in check, pass through an attacked square, or finish in check. Castle buttons appear only when legal. You can also select the king and click its destination or the matching rook.</p>';castleControls.after(castleHelp);
  const next=document.createElement('p');next.id='play-next';next.className='next-action';$('board').before(next);
  const settings=advanced('Search settings — optional',[$('depth').closest('label'),$('budget').closest('label'),$('pruning').closest('label'),$('ordering').closest('label')],'Default: 2 half-moves ahead, up to 3,000 positions. These settings apply to Panda hints and replies. Stockfish uses its own 0.3-second search; Random Panda uses no search.');
  $('analyze').parentElement.after(settings);
  hint('depth','How many half-moves to look ahead. The budget may stop it sooner.');hint('budget','Maximum positions searched per move. More can take longer.');
  $('pruning').closest('label').append(Object.assign(document.createElement('small'),{className:'field-help',textContent:'Skip branches that cannot improve the result (alpha-beta).'}));
  $('ordering').closest('label').append(Object.assign(document.createElement('small'),{className:'field-help',textContent:'Try captures and promotions earlier to help pruning.'}));
  $('move').textContent='Resume bot reply';$('move').classList.remove('primary');$('undo').textContent='Undo last turn';$('save').textContent='Save game (PGN)';$('save-result').insertAdjacentHTML('afterend',pgnHelp());$('analyze').textContent='Preview my best move';
  $('analyze').before(help('analyze-guide','Inspect without playing','Preview searches the current board without making a move or training the model. Scores favor White; negative values favor Black.'));
  $('bot').addEventListener('change',()=>syncControls());
 }else if(tab==='train'){
  boardMode('train-board');
  const panel=$('fresh').closest('.panel');panel.querySelector('h2').textContent='Train a model';
  panel.prepend(help('training-guide','Start here: train for 10 epochs','The model learns to predict saved engine scores. Training changes its weights; it does not play games.'));
  const next=document.createElement('p');next.id='train-next';next.className='next-action';panel.querySelector('h2').after(next);
  const flow=panel.querySelector('.flow'),architecture=flow.nextElementSibling;
  const info=advanced('Model details',[flow,architecture],'Board and game state enter the network; one evaluation score comes out.');panel.append(info);
  const settings=advanced('Training settings — optional',[$('count').closest('label'),$('rate').closest('label'),$('epochs').closest('label')],'Recommended first run: 800 examples, learning rate 0.01, 10 epochs. Change one setting at a time.');panel.append(settings);
  hint('count','Examples used for weight updates. Validation is separate.');hint('rate','Size of each weight update. Larger is not always better.');hint('epochs','Additional passes through the selected training examples.');
  const recommended=document.createElement('button');recommended.textContent='Use recommended settings';recommended.onclick=()=>{$('count').value='800';$('rate').value='0.01';$('epochs').value='10';syncControls();};settings.append(recommended);
  $('fresh').textContent='Train a new model';
  const freshHelp=document.createElement('p');freshHelp.className='muted';freshHelp.textContent='New model starts from seeded weights. Continue builds on the loaded version. Both save a separate copy; earlier versions stay available.';panel.querySelector('.controls').after(freshHelp);
  const why=document.createElement('p');why.id='continue-help';why.className='next-action';freshHelp.after(why);
  ['count','rate','epochs'].forEach(id=>$(id).addEventListener('change',()=>syncControls()));
  const links=document.createElement('div');links.className='controls';links.innerHTML='<button id="try-model">Play against this model →</button><button id="test-match">Test it in a match →</button>';panel.append(links);
  $('try-model').onclick=()=>act(async()=>{bot=state.id;await show('play');});$('test-match').onclick=()=>act(()=>show('arena'));
  syncTrainingLinks();
 }else if(tab==='arena'){
  boardMode('arena-board');
  const panel=$('start').closest('.panel');panel.querySelector('h2').textContent='Test two opponents';
  panel.prepend(help('match-guide','Prepare → Play → Review','A match tests fixed opponents. It does not train their weights. Start with 2 games; each opponent plays both colors.'));
  const next=document.createElement('p');next.id='arena-next';next.className='next-action';panel.querySelector('h2').after(next);
  const settings=advanced('Match settings — optional',[$('games').closest('label'),$('arena-depth').closest('label'),$('arena-budget').closest('label'),$('cap').closest('label')],'Quick trial: 2 games, depth 1, 1,000 nodes per move, 40 extra half-moves. Games reaching the cap are unfinished, not draws.');panel.append(settings);
  hint('games','A larger paired match gives more evidence, but takes longer.');hint('arena-depth','Half-moves ahead for both searching opponents.');hint('arena-budget','Same node limit for Panda opponents. Stockfish uses its own fixed 0.3-second search; comparisons with it are not equal-compute tests.');hint('cap','Stop long games after this many additional half-moves.');
  $('run').textContent='Play match automatically';$('step').textContent='Play one move';$('pause').textContent='Pause match';
  const promotionHelp=$('promote').nextElementSibling;
  const promotion=advanced('Advanced: replace the champion',[$('promote'),promotionHelp],'Only a saved neural model that passes the completed 40-game champion gate is eligible. A short demo match will not qualify.');
  $('scoreboard').after(promotion);
  ['candidate','opponent','games'].forEach(id=>$(id).addEventListener('change',()=>syncControls()));
 }
 syncControls();
}
function modelFileSize(bytes){return bytes>=1048576?`${(bytes/1048576).toFixed(2)} MiB`:`${(bytes/1024).toFixed(1)} KiB`;}
function confirmModelDelete(id,permanent=false){
 const dialog=document.createElement('dialog');dialog.id='model-delete-dialog';dialog.className='result-flash';dialog.setAttribute('aria-labelledby','delete-title');dialog.setAttribute('aria-describedby','delete-description');
 dialog.innerHTML='<div class="result-flash-card"><span class="result-flash-icon" aria-hidden="true">🗑️</span><h2 id="delete-title"></h2><p id="delete-description">Remove this model from the saved models and opponent lists? It will move to local trash and can be restored. Saved games stay available.</p><div class="controls"><button id="cancel-delete">Cancel</button><button id="confirm-delete" class="danger">Delete model</button></div></div>';
 const model=[...state.models,...(state.deleted_models||[])].find(m=>m.id===id);
 dialog.querySelector('h2').textContent=`${permanent?'Permanently delete':'Delete'} ${id}?`;
 if(permanent){
  dialog.querySelector('#delete-description').textContent=`Erase this model file (${modelFileSize(model.size_bytes)}, ${model.size_bytes.toLocaleString()} bytes) permanently? It bypasses your system’s trash and cannot be restored through the app. Saved games stay available.`;
  dialog.querySelector('#confirm-delete').textContent='Delete permanently';
 }
 const previousFocus=document.activeElement;
 dialog.addEventListener('close',()=>{dialog.remove();if(previousFocus?.isConnected&&!previousFocus.disabled)previousFocus.focus();});
 dialog.querySelector('#cancel-delete').onclick=()=>dialog.close();
 dialog.querySelector('#confirm-delete').onclick=()=>{dialog.close();act(async()=>{state=await api(permanent?'permanently-delete-model':'delete-model',{id});if(bot===id)bot=state.ready?state.id:'positional';if(hintEngine===id)hintEngine='positional';ownHint=null;await show('train');});};
 document.body.append(dialog);dialog.showModal();dialog.querySelector('#cancel-delete').focus();
}
function renderModelManager(){
 const models=sortedModels(),deleted=state.deleted_models||[];
 $('models').innerHTML=models.length?`<label>Choose a saved model<select id="model" aria-label="Saved model">${models.map(m=>`<option value="${m.id}" ${state.id===m.id?'selected':''}>${modelLabel(m)}</option>`).join('')}</select></label><p class="muted">★ marks the lowest validation MSE among saved models. This is prediction error, not a percentage or a chess-strength rating.</p><div id="model-details"></div><div class="controls"><button id="load">Use this saved version</button><button id="choose-best">Select lowest error</button><button id="delete-model" class="danger">Delete selected model</button></div><p id="delete-help" class="muted"></p>`:'<p>No saved neural models. Train a new model to begin.</p>';
 if(models.length){
  $('model').onchange=renderModelDetails;
  $('choose-best').onclick=()=>{$('model').value=models[0].id;renderModelDetails();};
  $('load').onclick=()=>act(async()=>{state=await api('load',{id:$('model').value});await show('train');});
  $('delete-model').onclick=()=>confirmModelDelete($('model').value);
  renderModelDetails();
 }
 bulkDeleteManager($('models'),models,'models');
 if(deleted.length){
  const restore=document.createElement('details');restore.className='advanced';restore.innerHTML=`<summary>Deleted models (${deleted.length}) — restore or erase</summary><p class="muted">Deleted models are kept in local trash. They are hidden from opponents and saved-model choices. Restore keeps the file; permanent deletion frees its space.</p><label>Deleted model<select id="deleted-model" aria-label="Deleted model">${[...deleted].reverse().map(m=>`<option value="${m.id}">${m.id} · ${modelFileSize(m.size_bytes)} · MSE ${errorValue(m.validation.mse)} · ${m.epoch} epochs</option>`).join('')}</select></label><div class="controls"><button id="restore-model">Restore selected model</button><button id="purge-model" class="danger">Delete permanently</button></div>`;$('models').append(restore);
  bulkDeleteManager(restore,deleted,'trash');
  $('purge-model').onclick=()=>confirmModelDelete($('deleted-model').value,true);
  $('restore-model').onclick=()=>act(async()=>{state=await api('restore-model',{id:$('deleted-model').value});await show('train');});
 }
}
function renderModelDetails(){
 const m=state.models.find(m=>m.id===$('model')?.value);if(!m)return;
 $('model-details').innerHTML=metrics([['File size',modelFileSize(m.size_bytes)],['Validation MSE',errorValue(m.validation.mse)],['Validation MAE',errorValue(m.validation.mae)],['Practice positions',m.count],['Training epochs',m.epoch],['Learning rate',m.rate]])+`<p class="muted">Evaluated on ${m.validation.n} validation positions. ${m.id===state.id?'This version is currently loaded.':'Use this saved version to load it for continued training.'}</p>`;
 const why=modelDeleteReason(m.id);
 reason('delete-model',!!why,why,busy);
 $('delete-help').textContent=why||'Delete removes this version from the lists. Restore is available below. Models in an unfinished arena match are protected.';
}
function syncTrainingLinks(){for(const id of ['try-model','test-match'])reason(id,!state.ready,'Train a model first.',busy);}
function renderTraining(){renderTrainingBase();renderModelManager();syncControls();syncTrainingLinks();}
function arenaSeats(run){
 // Finished runs advance index past the last game; the board still shows that game.
 const game=Math.min(run.index,run.games-1),candidateWhite=game%2===0;
 return ['Black','White'].map(color=>{
  const challenger=(color==='White')===candidateWhite;
  return {color,id:challenger?run.candidate:run.opponent,role:challenger?'Challenger':'Opponent'};
 });
}
function renderArenaSeats(){
 const portraits={random:'🐼',material:'👺',positional:'🧭','reference-neural':'🐼','reference-stockfish':'🐟'};
 for(const color of ['Black','White']){
  const id='arena-seat-'+color.toLowerCase();
  if(!$(id)){
   const seat=document.createElement('div');seat.id=id;seat.className='arena-seat';seat.dataset.color=color;
   seat.innerHTML='<span class="arena-color" aria-hidden="true"></span><span class="arena-avatar" aria-hidden="true"></span><div class="arena-player"><small></small><strong></strong></div><span class="arena-turn"></span>';
   if(color==='Black')($('arena-board-mode')||$('arena-board')).before(seat);else $('arena-board').after(seat);
  }
  $(id).hidden=!arena?.active;
 }
 if(!arena?.active)return;
 for(const player of arenaSeats(arena.run)){
  const seat=$('arena-seat-'+player.color.toLowerCase());
  const turn=!arena.run.finished&&arena.board.turn===player.color;
  seat.classList.toggle('to-move',turn);
  seat.querySelector('.arena-color').textContent=player.color==='White'?'♔':'♚';
  seat.querySelector('.arena-avatar').textContent=portraits[player.id]||(player.id.startsWith('custom-')?'🛠':'🧠');
  seat.querySelector('small').textContent=`${player.color.toUpperCase()} · ${player.role}`;
  seat.querySelector('strong').textContent=name(player.id);
  seat.querySelector('.arena-turn').textContent=turn?'To move':arena.run.finished?'Finished':'';
 }
}
function renderArena(){$('arena-engine-limits')?.remove();renderArenaBase();renderArenaSeats();if(arena?.active&&[arena.run.candidate,arena.run.opponent].includes('reference-stockfish')){$('arena-status').insertAdjacentHTML('afterend','<p id="arena-engine-limits" class="warning">Stockfish uses its own 0.3-second search; the depth and node limits apply to Panda only. This match is not an equal-compute benchmark.</p>');}syncControls();}

// Multi-selection uses the same guarded deletion endpoints as individual actions.
function syncBulkManagers(){
 bulkManagers=bulkManagers.filter(manager=>manager.host.isConnected);
 bulkManagers.forEach(manager=>manager.sync());
}
function bulkDeleteManager(parent,records,kind){
 if(!records.length)return;
 const host=document.createElement('details');host.className='advanced bulk-delete';
 host.innerHTML='<summary></summary><div class="controls"><button data-select-all>Select all available</button><button data-clear>Clear selection</button></div><div class="bulk-items scroll"></div><p class="muted" aria-live="polite"></p><button class="danger" data-delete-selected></button>';
 host.querySelector('summary').textContent=kind==='arena'?'Select multiple histories':kind==='trash'?'Select multiple deleted models':'Select multiple saved models';
 const choices=records.map(record=>{
  const label=document.createElement('label');label.className='bulk-item';
  const input=document.createElement('input');input.type='checkbox';input.value=record.id;input.setAttribute('aria-label','Select '+record.id);
  const text=document.createElement('span');
  text.textContent=record.id+' · '+modelFileSize(record.size_bytes||0)+(kind==='arena'?' · '+name(record.candidate)+' vs '+name(record.opponent):' · validation MSE '+errorValue(record.validation.mse));
  label.append(input,text);host.querySelector('.bulk-items').append(label);
  input.onchange=sync;return {record,input,label};
 });
 const action=host.querySelector('[data-delete-selected]');
 function selected(){return choices.filter(c=>c.input.checked).map(c=>c.record);}
 function sync(){
  for(const c of choices){const why=kind==='models'?modelDeleteReason(c.record.id):'';if(why)c.input.checked=false;c.input.disabled=busy||!!why;c.label.title=why;}
  const rows=selected(),bytes=rows.reduce((sum,r)=>sum+(r.size_bytes||0),0);
  host.querySelector('p').textContent=rows.length+' selected · '+modelFileSize(bytes)+(kind==='models'?' · moves to Deleted models; restore remains available':' · permanent deletion cannot be undone');
  action.textContent=(kind==='models'?'Delete selected':'Delete selected permanently')+' ('+rows.length+')';
  action.disabled=busy||!rows.length;
  host.querySelector('[data-select-all]').disabled=busy||choices.every(c=>c.input.disabled);
  host.querySelector('[data-clear]').disabled=busy||!rows.length;
 }
 host.querySelector('[data-select-all]').onclick=()=>{choices.forEach(c=>{if(!c.input.disabled)c.input.checked=true;});sync();};
 host.querySelector('[data-clear]').onclick=()=>{choices.forEach(c=>c.input.checked=false);sync();};
 action.onclick=()=>confirmBulkDelete(selected(),kind);
 parent.append(host);bulkManagers.push({host,sync});sync();
}
function confirmBulkDelete(records,kind){
 if(!records.length)return;
 const bytes=records.reduce((sum,r)=>sum+(r.size_bytes||0),0);
 const dialog=document.createElement('dialog');dialog.className='result-flash';dialog.setAttribute('aria-labelledby','bulk-delete-title');
 dialog.innerHTML='<div class="result-flash-card"><h2 id="bulk-delete-title"></h2><p></p><ul class="scroll"></ul><div class="controls"><button data-cancel>Cancel</button><button data-confirm class="danger">Confirm deletion</button></div></div>';
 dialog.querySelector('h2').textContent='Delete '+records.length+' selected '+(kind==='arena'?'histories':'models')+'?';
 dialog.querySelector('p').textContent=modelFileSize(bytes)+' selected. '+(kind==='models'?'These models will move to Deleted models and can be restored.':'This permanently erases the selected files'+(kind==='arena'?' and their PGNs':'')+' and cannot be undone.');
 for(const r of records){const item=document.createElement('li');item.textContent=r.id;dialog.querySelector('ul').append(item);}
 dialog.querySelector('[data-cancel]').onclick=()=>dialog.close();dialog.onclose=()=>dialog.remove();
 dialog.querySelector('[data-confirm]').onclick=()=>{dialog.close();act(async()=>{
  let completed=0,failure;
  for(const r of records){
   try{
    if(kind==='arena')arena=await api('arena/delete',{id:r.id});
    else{state=await api(kind==='trash'?'permanently-delete-model':'delete-model',{id:r.id});if(bot===r.id)bot=state.ready?state.id:'positional';if(hintEngine===r.id)hintEngine='positional';ownHint=null;}
    completed++;
   }catch(error){failure=error;break;}
  }
  await show(kind==='arena'?'arena':'train');
  if(failure)throw Error(completed+' of '+records.length+' deleted. Remaining items were kept: '+failure.message);
 });};
 document.body.append(dialog);dialog.showModal();dialog.querySelector('[data-cancel]').focus();
}
