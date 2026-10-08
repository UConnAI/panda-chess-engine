"""Measured minimax, optional alpha-beta, ordering, and iterative deepening."""
import time
from .board import chess,terminal_score
from .evaluation import VALUES

class BudgetReached(Exception):pass

def search(board,evaluate,depth=3,budget=3000,pruning=True,ordering=True):
    if type(depth) is not int or not 1<=depth<=4:raise ValueError('Depth must be 1–4.')
    if type(budget) is not int or not 100<=budget<=30000:raise ValueError('Node budget must be 100–30000.')
    if type(pruning) is not bool or type(ordering) is not bool:raise ValueError('Search switches must be boolean.')
    started=time.perf_counter();stats=dict(nodes=0,evaluated=0,cutoffs=0,moves_skipped=0)
    def ordered(b):
        moves=list(b.legal_moves)
        def key(m):
            victim=b.piece_type_at(m.to_square) or (1 if b.is_en_passant(m) else 0)
            return (-int(bool(m.promotion)),-int(b.is_capture(m)),-(VALUES.get(victim,0)*10-VALUES.get(b.piece_type_at(m.from_square),0)),m.uci())
        return sorted(moves,key=key if ordering else lambda m:m.uci())
    def visit(b,left,alpha,beta,ply):
        if stats['nodes']>=budget:raise BudgetReached()
        stats['nodes']+=1
        terminal=terminal_score(b,ply)
        if terminal is not None:return terminal,[]
        if left==0:
            stats['evaluated']+=1
            return max(-20,min(20,float(evaluate(b)))),[]
        maximum=b.turn;best=float('-inf') if maximum else float('inf');pv=[]
        choices=ordered(b)
        for i,m in enumerate(choices):
            b.push(m)
            try:value,line=visit(b,left-1,alpha,beta,ply+1)
            finally:b.pop()
            if (value>best if maximum else value<best):best,pv=value,[m.uci()]+line
            if maximum:alpha=max(alpha,best)
            else:beta=min(beta,best)
            if pruning and beta<=alpha:
                stats['cutoffs']+=1;stats['moves_skipped']+=len(choices)-i-1;break
        return best,pv
    if board.is_game_over(claim_draw=True):return dict(move=None,san=None,score=terminal_score(board),depth=0,requested_depth=depth,candidates=[],pv=[],budget_hit=False,seconds=0,**stats)
    completed=[];finished=0;hit=False
    for d in range(1,depth+1):
        candidates=[]
        try:
            for move in ordered(board):
                san=board.san(move);board.push(move)
                try:score,pv=visit(board,d-1,float('-inf'),float('inf'),1)
                finally:board.pop()
                candidates.append(dict(move=move.uci(),san=san,score=score,pv=[move.uci()]+pv))
        except BudgetReached:hit=True;break
        completed=sorted(candidates,key=lambda r:r['score'],reverse=board.turn);finished=d
    if not completed:
        # Legal fallback, explicitly no completed iteration or invented evaluation.
        m=ordered(board)[0];completed=[dict(move=m.uci(),san=board.san(m),score=None,pv=[m.uci()])]
    best=completed[0]
    return dict(**best,depth=finished,requested_depth=depth,candidates=completed[:5],budget_hit=hit,
                seconds=round(time.perf_counter()-started,4),**stats)
