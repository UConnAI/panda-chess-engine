import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

const source=readFileSync(new URL('../ui/app.js',import.meta.url),'utf8');
const context=vm.createContext({});
context.name=id=>id;
context.modelFileSize=bytes=>bytes+' bytes';
vm.runInContext(source.slice(source.indexOf('function arenaScoreRows('),source.indexOf('function renderArenaBase(')),context);
vm.runInContext(source.slice(source.indexOf('function arenaSeats('),source.indexOf('function renderArenaSeats(')),context);
test('arena seats follow alternating game colors and retain final game colors',()=>{
 const run={candidate:'random',opponent:'positional',games:2,index:0,finished:false};
 const seats=()=>JSON.parse(JSON.stringify(context.arenaSeats(run)));
 assert.deepEqual(seats(),[{color:'Black',id:'positional',role:'Opponent'},{color:'White',id:'random',role:'Challenger'}]);
 run.index=1;
 assert.deepEqual(seats(),[{color:'Black',id:'random',role:'Challenger'},{color:'White',id:'positional',role:'Opponent'}]);
 run.index=2;run.finished=true;
 assert.equal(seats()[0].id,'random');
 run.games=40;run.index=40;
 assert.equal(seats()[0].id,'random');
});
test('scorecards identify each player and separate capped games from schedule status',()=>{
 const run={id:'run-0001',candidate:'neural-0001',opponent:'material',finished:true,summary:{wins:3,draws:2,losses:1,unfinished:4}};
 const html=context.arenaHistoryCard(run);
 assert.match(html,/Challenger<\/small>neural-0001<\/th><td>3<\/td><td>2<\/td><td>1<\/td>/);
 assert.match(html,/Opponent<\/small>material<\/th><td>1<\/td><td>2<\/td><td>3<\/td>/);
 assert.match(html,/Schedule complete/);
 assert.match(html,/4 unfinished games/);
 assert.match(html,/excluded from wins, draws and losses/);
 run.finished=false;
 assert.match(context.arenaHistoryCard(run),/Schedule in progress/);
});

vm.runInContext(source.slice(source.indexOf('function pgnHelp('),source.indexOf('function arenaScoreRows(')),context);
test('PGN help explains the game file and Arena UI contains no Elo section',()=>{
 assert.match(context.pgnHelp(),/Portable Game Notation/);
 assert.ok(!source.includes('function arenaRating('));
 assert.ok(!source.includes('Relative Elo'));
});
