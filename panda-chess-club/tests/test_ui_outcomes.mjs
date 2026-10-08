import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {execFileSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import vm from 'node:vm';

const root=fileURLToPath(new URL('../',import.meta.url));
const source=readFileSync(new URL('../ui/app.js',import.meta.url),'utf8');
// Exercise the dialog formatter with the real board_state contract, not invented casing.
const positions=JSON.parse(execFileSync('python',['-c',`
import json
from engine.board import chess, board_state
boards=[chess.Board(fen) for fen in [
 '7k/5Q2/6K1/8/8/8/8/8 b - - 0 1',
 '7k/6Q1/6K1/8/8/8/8/8 b - - 0 1',
 '7k/8/6K1/8/8/8/8/8 b - - 0 1']]
print(json.dumps([dict(board_state(b),arena_reason=b.outcome().termination.name) for b in boards]))
`],{cwd:root,encoding:'utf8'}));

function notice(board,reason=board.termination){
 const results=[];
 const context=vm.createContext({resultFlash:(title,detail)=>results.push({title,detail})});
 vm.runInContext(source.slice(source.indexOf('function outcomeFlash('),source.indexOf('function gameResultFlash(')),context);
 context.outcomeFlash(board.result,reason,true,board.turn);
 return results;
}

test('play and arena stalemate reasons both show the full explanation',()=>{
 const board=positions[0];
 assert.equal(board.termination,'stalemate');
 for(const reason of [board.termination,board.arena_reason]){
  const [result]=notice(board,reason);
  assert.equal(result.title,'Stalemate — draw');
  assert.match(result.detail,/Black has no legal move/);
  assert.match(result.detail,/NOT in check/);
  assert.match(result.detail,/game is a draw/);
 }
});
test('actual checkmate and spaced draw reasons retain their explanations',()=>{
 assert.match(notice(positions[1])[0].title,/Checkmate — You win/);
 assert.match(notice(positions[1])[0].detail,/Black is in check/);
 assert.equal(positions[2].termination,'insufficient material');
 assert.match(notice(positions[2])[0].detail,/remaining pieces cannot produce checkmate/);
});
test('ongoing and capped games do not show game-ending dialogs',()=>{
 assert.deepEqual(notice({result:null,termination:null,turn:'White'}),[]);
 assert.deepEqual(notice({result:'*',termination:'unfinished: move cap',turn:'White'}),[]);
});

test('autoplay waits for timed result dismissal and manual steps request no timer',async()=>{
 let release,argumentsSeen;
 const next={run:{results:[{result:'1-0',reason:'CHECKMATE',moves:['e2e4']}]}};
 const context=vm.createContext({arena:{run:{results:[]}},running:true,api:async()=>next,renderArena:()=>{},outcomeFlash:(...args)=>{argumentsSeen=args;return new Promise(resolve=>{release=resolve;});}});
 vm.runInContext(source.slice(source.indexOf('async function arenaStep('),source.indexOf('function arenaScoreRows(')),context);
 let settled=false;const step=context.arenaStep(true).then(()=>{settled=true;});
 await new Promise(resolve=>setImmediate(resolve));
 assert.equal(argumentsSeen[4],2000);assert.equal(context.running,true);assert.equal(settled,false);
 release();await step;assert.equal(settled,true);
 context.running=false;context.arena={run:{results:[]}};
 context.outcomeFlash=(...args)=>{argumentsSeen=args;};
 await context.arenaStep();assert.equal(argumentsSeen[4],0);
});

test('final game uses autoplay dismissal even when running flag has changed',async()=>{
 let args;
 const final={run:{games:2,finished:true,results:[{}, {game:2,result:'0-1',reason:'CHECKMATE',moves:[]}]}};
 const context=vm.createContext({arena:{run:{results:[{}]}},running:false,api:async()=>final,renderArena:()=>{},outcomeFlash:(...values)=>{args=values;}});
 vm.runInContext(source.slice(source.indexOf('async function arenaStep('),source.indexOf('function arenaScoreRows(')),context);
 await context.arenaStep(true);
 assert.equal(args[4],2000);assert.equal(args[5],'Game 2/2 · Match complete');
 assert.equal(context.arena.run.results.length,2);
});
