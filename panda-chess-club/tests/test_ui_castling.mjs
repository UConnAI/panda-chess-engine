import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {execFileSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import vm from 'node:vm';

const source=readFileSync(new URL('../ui/common.js',import.meta.url),'utf8');
const context=vm.createContext({});
vm.runInContext(source.slice(source.indexOf('function castlingMoves('),source.indexOf('function boardMode(')),context);
const boards=JSON.parse(execFileSync('python',['-c',`
import json
from engine.board import chess,board_state
fens=['r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1',chess.STARTING_FEN,
 'r3k2r/8/8/8/8/8/4r3/R3K2R w KQkq - 0 1',
 'r3kr1r/8/8/8/8/8/8/R3K2R w KQkq - 0 1',
 'r3k2r/8/8/8/8/8/8/R3K2R w - - 0 1']
print(json.dumps([board_state(chess.Board(fen)) for fen in fens]))
`],{cwd:fileURLToPath(new URL('../',import.meta.url)),encoding:'utf8'}));

test('king destination and king-to-rook clicks resolve to legal castling',()=>{
 const b=boards[0];
 assert.deepEqual(Array.from(context.castlingMoves(b)).sort(),['e1c1','e1g1']);
 for(const target of ['g1','h1'])assert.equal(context.selectedMove(b,'e1',target),'e1g1');
 for(const target of ['c1','a1'])assert.equal(context.selectedMove(b,'e1',target),'e1c1');
});
test('blocked, attacked, and lost-rights positions do not permit short castling',()=>{
 for(const b of boards.slice(1)){
  assert.ok(!context.castlingMoves(b).includes('e1g1'));
  assert.equal(context.selectedMove(b,'e1','h1'),null);
 }
});
