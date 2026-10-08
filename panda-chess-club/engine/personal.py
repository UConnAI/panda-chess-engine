"""Personal engine recipes and reproducible small experiments; no neural training here."""
import json, math
from pathlib import Path
from .board import chess, features, board_state
from .evaluation import material, positional
from .search import search

DEFAULTS=dict(material=1.,center=.1,activity=.015,shield=.12,pawns=.1)
LIMITS=dict(material=(0,2),center=(0,1),activity=(0,.2),shield=(0,1),pawns=(0,.5))
POSITIONS=dict(opening='rnbqkbnr/pppp1ppp/8/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R b KQkq - 1 2',
               capture='4k3/8/8/8/3q4/8/3R4/4K3 w - - 0 1',
               trap='4k3/3r4/8/8/p2Q4/8/8/6K1 w - - 0 1')
def weights(value):
    if not isinstance(value,dict) or set(value)!=set(DEFAULTS):raise ValueError('Supply all five evaluation weights.')
    for key,(lo,hi) in LIMITS.items():
        n=value[key]
        if type(n) not in (float,int) or not math.isfinite(n) or not lo<=n<=hi:raise ValueError('Weight outside allowed range: '+key)
    return {k:float(value[k]) for k in DEFAULTS}
def terms(board,w):
    x=features(board)
    return dict(material=material(board)*w['material'],center=x[7]*w['center'],activity=x[8]*w['activity'],shield=x[9]*w['shield'],pawns=-(x[10]+x[11])*w['pawns'])
def evaluate(board,w):return sum(terms(board,w).values())
def short(value,limit):
    if not isinstance(value,str) or len(value)>limit:raise ValueError('Text is too long or invalid.')
    return value.strip()
class PersonalProject:
    def __init__(self,root):
        self.folder=Path(root)/'project_data';self.path=self.folder/'project.json'
        self.data=json.loads(self.path.read_text(encoding='utf-8')) if self.path.exists() else dict(title='My Chess Engine',author='',description='',bots=[],experiments=[])
    def save(self):
        self.folder.mkdir(exist_ok=True);temp=self.path.with_suffix('.tmp');temp.write_text(json.dumps(self.data,indent=2),encoding='utf-8');temp.replace(self.path)
    def status(self):return dict(**self.data,defaults=DEFAULTS,positions=POSITIONS)
    def profile(self,a):
        self.data.update(title=short(a.get('title',''),80) or 'My Chess Engine',author=short(a.get('author',''),80),description=short(a.get('description',''),1000));self.save();return self.status()
    def create(self,a):
        w=weights(a.get('weights'));name=short(a.get('name',''),60)
        if not name:raise ValueError('Give your engine a name.')
        record=dict(id=f"custom-{len(self.data['bots'])+1:04d}",name=name,weights=w,hypothesis=short(a.get('hypothesis',''),1000))
        self.data['bots'].append(record);self.save();return self.status()
    def get(self,id):
        found=next((b for b in self.data['bots'] if b['id']==id),None)
        if found is None:raise ValueError('Unknown custom engine.')
        return found
    def inspect(self,a):
        w=weights(a.get('weights'));position=a.get('position','opening')
        if position not in POSITIONS:raise ValueError('Unknown experiment position.')
        b=chess.Board(POSITIONS[position]);r=search(b,lambda b:evaluate(b,w),2,1000)
        return dict(board=board_state(b),terms=terms(b,w),score=evaluate(b,w),baseline=positional(b),search=r)
    def experiment(self,a):
        bot=self.get(a.get('id'));rows=[]
        for key,fen in POSITIONS.items():
            b=chess.Board(fen);custom=search(b,lambda b:evaluate(b,bot['weights']),2,1000);base=search(b,positional,2,1000)
            rows.append(dict(position=key,fen=fen,custom_move=custom['san'],baseline_move=base['san'],custom_score=custom['score'],baseline_score=base['score'],custom_depth=custom['depth'],baseline_depth=base['depth']))
        self.data['experiments'].append(dict(engine=bot['id'],notes=short(a.get('notes',''),2000),depth=2,budget=1000,rows=rows));self.save();return self.status()
    def report(self,arena):
        d=self.data;lines=['# '+d['title'],'','Author: '+(d['author'] or '(not entered)'),' ',d['description'],'','## My implementation','Custom hand-written evaluation recipes plugged into alpha-beta search. These weights are manually tuned, not learned neural weights.','']
        for b in d['bots']:lines+=['### '+b['name']+' ('+b['id']+')',b['hypothesis'],'', 'Weights: '+json.dumps(b['weights']), '']
        lines+=['## Position experiments','Same three positions, requested depth 2, budget 1,000 nodes per move. Scores use different evaluators and are not comparable measures of playing strength.','']
        for e in d['experiments']:
            lines+=['### '+e['engine'],e['notes'],'','| Position | My move | Baseline move | Completed depths (mine / baseline) |','| --- | --- | --- | --- |']
            for r in e['rows']:lines.append(f"| {r['position']} | {r['custom_move']} | {r['baseline_move']} | {r['custom_depth']} / {r['baseline_depth']} |")
            lines.append('')
        lines+=['## Recorded Arena evidence','']
        for r in arena.history():
            s=r['summary'];lines.append(f"- {r['id']}: {r['candidate']} vs {r['opponent']}; challenger W/D/L {s['wins']}/{s['draws']}/{s['losses']}; unfinished {s['unfinished']}; schedule complete: {r['finished']}.")
        lines+=['','## Attribution and limits','Built on the Panda Chess starter project (GPL-3.0-or-later), including python-chess and public teacher data. Describe your own changes separately from inherited code. Keep license notices. Short trials and lower prediction error do not establish a human chess rating.','']
        return '\n'.join(lines)
