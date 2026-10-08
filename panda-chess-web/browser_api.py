"""Browser adapter around the desktop project's generated action dispatcher."""
import base64
import io
import json
from pathlib import Path
import time
import zipfile
import actions as a

ROOT = Path('/app')
STATE = Path('/state')

def initialize(root=ROOT, storage=STATE):
    global ROOT, STATE
    ROOT, STATE = Path(root), Path(storage)
    STATE.mkdir(parents=True, exist_ok=True)
    a.storage = STATE
    a.trainer = a.Trainer(STATE)
    a.trainer.personal = a.PersonalProject(STATE)
    a.arena = a.Arena(STATE, a.trainer)
    a.references = a.References(a.trainer, ROOT)
    a.references.binary = Path('browser-stockfish')
    a.references.stockfish = cached_stockfish
    a.trainer.references = a.references

_stockfish = {}
def cached_stockfish(board):
    a.references.require('reference-stockfish')
    if board.is_game_over(claim_draw=True):
        return dict(move=None,san=None,score=None,depth=0,requested_depth=0,nodes=0,
            evaluated=None,cutoffs=None,moves_skipped=None,seconds=0,candidates=[],pv=[],
            budget_hit=False,external=True,engine='reference-stockfish',engine_name='Stockfish 17.1 Lite · browser')
    if board.fen() not in _stockfish:
        raise ValueError('Browser Stockfish analysis is not ready. Retry the move.')
    return _stockfish[board.fen()]

def stockfish_fen(path, data):
    """Find the external analysis needed before executing a synchronous action."""
    if not a.references.unlocked:
        return None
    kind = data.get('kind', 'positional')
    if kind == 'champion':
        kind = a.trainer.registry['champion']
    if path in ('move', 'analyze') and kind == 'reference-stockfish':
        board = a.replay(data.get('moves', []))
    elif path == 'arena/step' and a.arena.run and not a.arena.run['finished']:
        run = a.arena.run
        board = a.replay(run['moves'])
        kind = run['candidate'] if board.turn == (run['index'] % 2 == 0) else run['opponent']
        if kind != 'reference-stockfish': return None
    elif path == 'references/compare':
        examples = {'queen':'4k3/8/8/8/3q4/8/3R4/4K3 w - - 0 1',
                    'trap':'4k3/3r4/8/8/p2Q4/8/8/6K1 w - - 0 1'}
        example = data.get('example', 'current')
        board = a.chess.Board(examples[example]) if example in examples else a.replay(data.get('moves', []) if example == 'current' else [])
    else:
        return None
    return None if board.is_game_over(claim_draw=True) else board.fen()

def accept_stockfish(fen, rows, seconds):
    board = a.chess.Board(fen)
    choices = []
    for row in rows:
        moves = []
        line = board.copy()
        for uci in row['pv'][:8]:
            move = a.chess.Move.from_uci(uci)
            if move not in line.legal_moves: break
            moves.append(uci)
            line.push(move)
        if not moves: continue
        score = row['score'] * (1 if board.turn else -1) / 100
        choices.append(dict(move=moves[0], san=board.san(a.chess.Move.from_uci(moves[0])), score=score, pv=moves))
    if not choices: raise ValueError('Stockfish returned no legal continuation.')
    top = choices[0]
    _stockfish.clear()
    _stockfish[fen] = dict(**top, candidates=choices, nodes=rows[0].get('nodes', 0),
        depth=rows[0].get('depth', 0), requested_depth=rows[0].get('depth', 0),
        evaluated=None, cutoffs=None, moves_skipped=None, seconds=seconds,
        budget_hit=False, external=True, engine='reference-stockfish',
        engine_name='Stockfish 17.1 Lite · browser · single thread')

def download(with_work=False):
    from package_project import project_zip
    payload = project_zip(ROOT)
    if not with_work: return base64.b64encode(payload).decode()
    buffer = io.BytesIO(payload)
    with zipfile.ZipFile(buffer, 'a', zipfile.ZIP_DEFLATED) as archive:
        # Only this student's app-owned records; never arbitrary browser files.
        for folder in ('models', 'project_data', 'games', 'arena_results'):
            for path in sorted((STATE / folder).rglob('*')):
                if path.is_file() and '.trash' not in path.parts and path.suffix in ('.json', '.pgn'):
                    payload = path.read_bytes()
                    if path == STATE/'models/registry.json':
                        registry = json.loads(payload)
                        registry['deleted_models'] = []
                        payload = json.dumps(registry,indent=2).encode()
                    archive.writestr('panda-chess-project/' + path.relative_to(STATE).as_posix(), payload)
        counter = STATE/'arena_results/.next-id'
        if counter.is_file(): archive.writestr('panda-chess-project/arena_results/.next-id',counter.read_bytes())
        report = a.trainer.personal.report(a.arena)
        archive.writestr('panda-chess-project/MY_RESULTS.md', report.encode())
    return base64.b64encode(buffer.getvalue()).decode()

def request(path, data=None):
    if path == 'download/project.zip': return download(False)
    if path == 'download/my-project.zip': return download(True)
    if path == 'project/report.md': return a.trainer.personal.report(a.arena)
    if path.startswith('pgn/'):
        name = path[4:]
        allowed = {p.name:p for folder in ('games','arena_results') for p in (STATE/folder).glob('*.pgn')}
        if name not in allowed: raise ValueError('Unknown saved game.')
        return allowed[name].read_text()
    if data is not None: return a.post(path, data)
    if path == 'status': return a.trainer.status()
    if path == 'project': return a.trainer.personal.status()
    if path == 'references': return a.references.status(a.arena)
    if path == 'arena': return a.arena.status()
    if path == 'games': return [p.name for p in sorted((STATE/'games').glob('*.pgn'))]
    raise ValueError('Unknown browser action.')
