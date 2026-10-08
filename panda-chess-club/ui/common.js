'use strict';
const $=id=>document.getElementById(id),fmt=n=>n===null?'—':Number(Number(n).toPrecision(4)).toString();
const pieceName={P:'White pawn',N:'White knight',B:'White bishop',R:'White rook',Q:'White queen',K:'White king',p:'Black pawn',n:'Black knight',b:'Black bishop',r:'Black rook',q:'Black queen',k:'Black king'};
async function api(path,data){const response=await fetch('/api/'+path,data===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});const result=await response.json();if(!response.ok)throw Error(result.error||'Request failed');return result;}
// Original vector silhouettes keep pieces crisp and consistent across devices.
const pieceShapes={
 P:'<circle cx="24" cy="12" r="6"/><path d="M20 19h8l-1 7 5 9H16l5-9z"/>',
 N:'<path d="M14 35c0-10 5-14 12-17l-7-1-5 4-3-5 9-9 1-5 5 5c10 3 11 16 8 28z"/><path d="m19 13 4-2" fill="none"/>',
 B:'<path d="M24 4c-3 5-9 8-9 15 0 5 4 7 7 8l-7 8h18l-7-8c3-1 7-3 7-8 0-7-6-10-9-15z"/><path d="m25 12-5 8" fill="none"/>',
 R:'<path d="M12 6h6v5h4V6h4v5h4V6h6v12l-6 4 2 13H16l2-13-6-4z"/><path d="M18 22h12" fill="none"/>',
 Q:'<path d="m12 13 6 7 6-10 6 10 6-7-5 17H17z"/><circle cx="11" cy="10" r="3"/><circle cx="24" cy="7" r="3"/><circle cx="37" cy="10" r="3"/><path d="M17 30h14l3 5H14z"/>',
 K:'<path d="M21 4h6v4h4v5h-4v4h-6v-4h-4V8h4z"/><path d="M24 20c-12-12-18 5-9 10l2 5h14l2-5c9-5 3-22-9-10z"/><path d="M17 30h14" fill="none"/>'
};
function piece(p){return p?`<svg class="piece" viewBox="0 0 48 48" aria-hidden="true">${pieceShapes[p.toUpperCase()]}<path d="M14 35h20l3 7H11z"/></svg>`:'';}
function castlingMoves(b){return b&&b.turn==='White'&&!b.result&&b.pieces.e1==='K'?b.legal_moves.filter(m=>m==='e1g1'||m==='e1c1'):[];}
function selectedMove(b,from,to){
 const castle=from==='e1'&&b.pieces.e1==='K'?{h1:'e1g1',a1:'e1c1'}[to]:null;
 if(castle&&castlingMoves(b).includes(castle))return castle;
 const legal=b.legal_moves.filter(m=>m.startsWith(from+to));
 return legal.find(m=>m.endsWith('q'))||legal[0]||null;
}
function boardMode(id,interactive=false){
 const el=$(id);
 el.classList.toggle('interactive',interactive);el.classList.toggle('readonly',!interactive);
 el.setAttribute('aria-label',interactive?'Playable chessboard. You play White.':'View-only chessboard');
 if(!$(id+'-mode')){const badge=document.createElement('p');badge.id=id+'-mode';badge.className='board-mode';badge.setAttribute('role','status');el.before(badge);}
 $(id+'-mode').textContent=interactive?'PLAY HERE · You play White':'VIEW ONLY · '+({ 'train-board':'Training example','arena-board':'Bots play this match',leaf:'Search continuation'}[id]||'Position preview');
}
function board(id,b,onSquare=null,selected=null){
 const el=$(id),interactive=!!onSquare;boardMode(id,interactive);
 el.innerHTML=Array.from({length:64},(_,i)=>{const sq='abcdefgh'[i%8]+(8-Math.floor(i/8)),p=b.pieces[sq]||'',legal=selected&&b.legal_moves.some(m=>m.startsWith(selected+sq)),tag=interactive?'button':'div';return `<${tag} class="square ${(i%8+Math.floor(i/8))%2?'dark':'light'} ${p===p.toUpperCase()?'white':'black'} ${sq===selected?'selected':''} ${legal?'legal':''}" data-square="${sq}" aria-label="${sq} ${pieceName[p]||'empty'}" ${interactive?'type="button"':'role="img"'}>${piece(p)}<small>${sq}</small></${tag}>`;}).join('');
 if(interactive)el.querySelectorAll('button').forEach(e=>e.onclick=()=>onSquare(e.dataset.square));
}
function metrics(rows){return `<div class="metrics">${rows.map(([label,value])=>`<div class="metric"><span>${label}</span><strong>${value??"—"}</strong></div>`).join('')}</div>`;}
function plot(history){const max=Math.max(.01,...history.flatMap(h=>[h.train_mse,h.validation_mse]));const points=k=>history.map((h,i)=>`${45+i*465/Math.max(1,history.length-1)},${180-h[k]/max*150}`).join(' ');return `<div class="legend"><span>● Training MSE</span><span>● Validation MSE</span></div><svg class="plot" viewBox="0 0 550 215" role="img" aria-label="Prediction error over actual training updates"><path d="M45 25V180H510" fill="none" stroke="#b6c8b8"/><text x="4" y="30">${fmt(max)}</text><text x="25" y="184">0</text><polyline points="${points('train_mse')}" class="train-line"/><polyline points="${points('validation_mse')}" class="val-line"/><text x="45" y="204">Start</text><text x="405" y="204">Update ${history.at(-1).epoch}</text></svg>`;}
