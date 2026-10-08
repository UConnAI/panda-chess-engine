import random
from .board import chess
from .evaluation import material,positional
from .search import search
from .personal import evaluate

def decide(board,kind,trainer,depth=3,budget=3000,pruning=True,ordering=True):
    if kind=='champion':kind=trainer.registry['champion']
    if kind in ('reference-neural','reference-stockfish'):
        refs=getattr(trainer,'references',None)
        if refs is None:raise ValueError('References are not configured.')
        refs.require(kind)
        if kind=='reference-stockfish':return refs.stockfish(board)
        result=search(board,refs.network.score,depth,budget,pruning,ordering);result['engine']=kind;return result
    if kind=='random':
        moves=sorted(board.legal_moves,key=lambda m:m.uci()) if not board.is_game_over(claim_draw=True) else []
        rng=random.Random(314)
        for _ in range(board.ply()):rng.random()
        move=rng.choice(moves) if moves else None
        return dict(move=move.uci() if move else None,san=board.san(move) if move else None,score=None,depth=0,requested_depth=0,nodes=0,evaluated=0,cutoffs=0,moves_skipped=0,seconds=0,candidates=[],pv=[move.uci()] if move else [],budget_hit=False,engine=kind)
    if kind.startswith('custom-'):
        w=trainer.personal.get(kind)['weights'];evaluator=lambda b:evaluate(b,w)
    elif kind=='material':evaluator=material
    elif kind=='positional':evaluator=positional
    else:evaluator=trainer.get_network(kind).score
    result=search(board,evaluator,depth,budget,pruning,ordering);result['engine']=kind;return result
