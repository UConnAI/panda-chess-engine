"""Hand-written baselines; these coefficients are not learned."""
from .board import chess, features
VALUES={1:1.,2:3.2,3:3.3,4:5.,5:9.}
def material(b):
    return sum(v*(len(b.pieces(p,True))-len(b.pieces(p,False))) for p,v in VALUES.items())

def positional(b):
    x=features(b)
    value=material(b)+.25*x[5]+.025*x[6]+.10*x[7]+.015*x[8]+.12*x[9]-.10*x[10]-.08*x[11]+.04*x[12]+.02*x[13]+.10*x[14]+.08*x[15]
    # A simple piece-square preference: minor pieces near the center.
    for color in (True,False):
        sign=1 if color else -1
        for p in (chess.KNIGHT,chess.BISHOP):
            for sq in b.pieces(p,color):
                value+=sign*.035*(7-abs(chess.square_file(sq)-3.5)-abs(chess.square_rank(sq)-3.5))
        for sq in b.pieces(chess.ROOK,color):
            file=chess.square_file(sq)
            if not any(chess.square_file(p)==file for c in (True,False) for p in b.pieces(chess.PAWN,c)):value+=sign*.15
    return value
