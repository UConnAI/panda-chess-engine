"""A small NumPy neural evaluator: 782 inputs -> 32 tanh units -> 1 tanh output."""
import os
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
import math
import numpy as np
from engine.board import chess

INPUTS=782
def encode(b):
    x=np.zeros(INPUTS,dtype=np.float64)
    for sq,p in b.piece_map().items():x[((0 if p.color else 6)+p.piece_type-1)*64+sq]=1
    x[768]=1 if b.turn else -1
    x[769:773]=[b.has_kingside_castling_rights(True),b.has_queenside_castling_rights(True),b.has_kingside_castling_rights(False),b.has_queenside_castling_rights(False)]
    if b.ep_square is not None:x[773+chess.square_file(b.ep_square)]=1
    x[781]=min(b.halfmove_clock,100)/100
    return x

class Network:
    def __init__(self,parameters=None):
        rng=np.random.default_rng(314)
        self.p={k:np.asarray(v,dtype=float) for k,v in parameters.items()} if parameters else dict(w=rng.normal(0,.08,(INPUTS,32)),b=np.zeros(32),v=rng.normal(0,.08,32),c=np.zeros(1))
        if {k:v.shape for k,v in self.p.items()}!={'w':(INPUTS,32),'b':(32,),'v':(32,),'c':(1,)} or not all(np.isfinite(v).all() for v in self.p.values()):raise ValueError('Invalid network parameters.')
    def forward(self,x):
        h=np.tanh(x@self.p['w']+self.p['b']);y=np.tanh(h@self.p['v']+self.p['c'][0]);return y,h
    def gradient(self,x,y):
        prediction,h=self.forward(x);d=2*(prediction-y)*(1-prediction**2)/len(x)
        hidden=d[:,None]*self.p['v'][None,:]*(1-h*h)
        return dict(w=x.T@hidden,b=hidden.sum(0),v=h.T@d,c=np.array([d.sum()]))
    def score(self,b):
        y,_=self.forward(encode(b));return float(4*np.arctanh(np.clip(y,-.999,.999)))
    def json(self):return {k:v.tolist() for k,v in self.p.items()}
