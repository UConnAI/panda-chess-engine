"""Build legal, independent positions for a searched continuation."""
from .board import chess,replay,board_state

def preview_line(moves=None,line=None,fen=None,max_moves=32):
    if not isinstance(line,list) or len(line)>max_moves:raise ValueError(f'Preview line must contain at most {max_moves} moves.')
    if fen is not None:
        if not isinstance(fen,str) or len(fen)>200:raise ValueError('Invalid preview position.')
        b=chess.Board(fen)
        if not b.is_valid():raise ValueError('Invalid preview position.')
    else:b=replay([] if moves is None else moves)
    frames=[dict(board=board_state(b),move=None,san=None,side=None)]
    for text in line:
        if not isinstance(text,str):raise ValueError('Preview moves must be UCI strings.')
        move=chess.Move.from_uci(text)
        if move not in b.legal_moves:raise ValueError('Illegal move in searched continuation.')
        san=b.san(move);side='White' if b.turn else 'Black';b.push(move)
        frames.append(dict(board=board_state(b),move=text,san=san,side=side))
    return dict(frames=frames)
