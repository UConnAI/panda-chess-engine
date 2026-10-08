import datetime,json,random
from pathlib import Path
from engine.board import chess,replay,board_state
import chess.pgn
from engine.bot import decide
from .elo import summarize

def openings(pairs):
    rng=random.Random(314);starts=[];seen=set()
    bases=[['e2e4','e7e5'],['d2d4','d7d5'],['e2e4','c7c5'],['d2d4','g8f6'],['c2c4','e7e5'],['g1f3','d7d5']]
    while len(starts)<pairs:
        moves=list(bases[len(starts)%len(bases)]);b=replay(moves)
        for _ in range(2):m=rng.choice(sorted(b.legal_moves,key=lambda m:m.uci()));moves.append(m.uci());b.push(m)
        if b.fen().split(' ')[0] not in seen:seen.add(b.fen().split(' ')[0]);starts.append(moves)
    return starts

class Arena:
    def __init__(self,root,trainer):
        self.root=Path(root);self.dir=self.root/'arena_results';self.dir.mkdir(exist_ok=True);self.trainer=trainer;self.run=None
        files=sorted(self.dir.glob('run-*.json'))
        if files:self.run=json.loads(files[-1].read_text())
    def save(self):
        p=self.dir/(self.run['id']+'.json');tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(self.run,indent=2));tmp.replace(p)
    def start(self,candidate,opponent,games=2,depth=2,budget=1000,cap=100):
        if type(games)is not int or games not in (2,10,40):raise ValueError('Choose 2, 10 or 40 games.')
        if type(depth)is not int or depth not in (1,2,3):raise ValueError('Arena depth must be 1–3.')
        if type(budget)is not int or budget not in (300,1000,3000):raise ValueError('Unknown arena budget.')
        if type(cap)is not int or cap not in (40,100,200):raise ValueError('Unknown move cap.')
        champion=self.trainer.registry['champion'];candidate=champion if candidate=='champion' else candidate;opponent=champion if opponent=='champion' else opponent
        valid=['random','material','positional']+[r['id'] for r in self.trainer.registry['models']]
        personal=getattr(self.trainer,'personal',None)
        if personal:valid += [b['id'] for b in personal.data['bots']]
        refs=getattr(self.trainer,'references',None)
        if refs and refs.unlocked:valid+=refs.available()
        if candidate not in valid or opponent not in valid or candidate==opponent:raise ValueError('Select two different saved engines.')
        starts=openings(games//2)
        next_id=max(int((self.dir/'.next-id').read_text()) if (self.dir/'.next-id').exists() else 1,1+max([int(p.stem.split('-')[1]) for p in self.dir.glob('run-*.json')]+[0]))
        (self.dir/'.next-id').write_text(str(next_id+1))
        self.run=dict(id=f"run-{next_id:04d}",candidate=candidate,opponent=opponent,champion_at_start=champion,games=games,depth=depth,budget=budget,cap=cap,openings=starts,index=0,moves=starts[0][:],results=[],finished=False,telemetry=None)
        self.save();return self.status()
    def step(self):
        r=self.run
        if not r:raise ValueError('Start an arena first.')
        if r['finished']:return self.status()
        b=replay(r['moves']);candidate_white=r['index']%2==0
        engine=r['candidate'] if b.turn==candidate_white else r['opponent']
        result=decide(b,engine,self.trainer,r['depth'],r['budget']);r['telemetry']=result
        if result['move']:r['moves'].append(result['move']);b.push_uci(result['move'])
        outcome=b.outcome(claim_draw=True)
        if outcome or len(r['moves'])-len(r['openings'][r['index']//2])>=r['cap']:
            score=None if not outcome else (.5 if outcome.winner is None else float(outcome.winner==candidate_white))
            game=dict(game=r['index']+1,score=score,result=outcome.result() if outcome else '*',reason=outcome.termination.name if outcome else 'unfinished: move cap',candidate_color='White' if candidate_white else 'Black',moves=r['moves'][:])
            r['results'].append(game);self.export_game(game)
            r['index']+=1
            if r['index']==r['games']:r['finished']=True
            else:r['moves']=r['openings'][r['index']//2][:]
        self.save();return self.status()
    def export_game(self,result):
        g=chess.pgn.Game();g.headers['Event']='Panda Club Arena';g.headers['White']=self.run['candidate'] if result['candidate_color']=='White' else self.run['opponent'];g.headers['Black']=self.run['opponent'] if result['candidate_color']=='White' else self.run['candidate'];g.headers['Result']=result['result'];g.headers['Termination']=result['reason'];g.headers['Round']=str(result['game']);node=g
        for m in result['moves']:node=node.add_variation(chess.Move.from_uci(m))
        path=self.dir/f"{self.run['id']}-game-{result['game']:03d}.pgn";path.write_text(str(g)+'\n')
    def status(self):
        if not self.run:return dict(active=False,history=self.history())
        return dict(active=True,run=self.run,summary=summarize(self.run),board=board_state(replay(self.run['moves'])),history=self.history())
    def history(self):
        return [dict(id=r['id'],candidate=r['candidate'],opponent=r['opponent'],finished=r['finished'],summary=summarize(r),size_bytes=self.record_size(r['id'])) for r in [json.loads(p.read_text()) for p in sorted(self.dir.glob('run-*.json'))]]
    def record(self,id):
        import re
        if not isinstance(id,str) or not re.fullmatch(r'run-[0-9]{4,}',id):raise ValueError('Unknown arena record.')
        path=self.dir/(id+'.json')
        if not path.is_file():raise ValueError('Unknown arena record.')
        return json.loads(path.read_text())
    def record_files(self,id):
        self.record(id)
        return [self.dir/(id+'.json'),*self.dir.glob(id+'-game-[0-9][0-9][0-9].pgn')]
    def record_size(self,id):
        return sum(p.stat().st_size for p in self.record_files(id))
    def delete_record(self,id):
        files=self.record_files(id)
        # Retain the high-water mark so deletion cannot reuse a match identity.
        counter=self.dir/'.next-id'
        maximum=1+max([int(p.stem.split('-')[1]) for p in self.dir.glob('run-*.json')]+[0])
        counter.write_text(str(max(maximum,int(counter.read_text()) if counter.exists() else 1)))
        for path in files[1:]:path.unlink()
        files[0].unlink()
        if self.run and self.run['id']==id:self.run=None
        return self.status()
    def replay_game(self,id,game):
        from engine.preview import preview_line
        r=self.record(id)
        if type(game)is not int:raise ValueError('Choose a recorded game.')
        g=next((g for g in r['results'] if g['game']==game),None)
        if g is None:raise ValueError('Unknown recorded game.')
        white=r['candidate'] if g['candidate_color']=='White' else r['opponent']
        black=r['opponent'] if g['candidate_color']=='White' else r['candidate']
        return dict(**preview_line(line=g['moves'],max_moves=600),white=white,black=black,game=g,depth=r['depth'],budget=r['budget'])
    def promote(self):
        if not self.run or not summarize(self.run)['promotable'] or self.run['opponent']!=self.trainer.registry['champion']:raise ValueError('Promotion requires a completed 40-game match against the current champion, no caps, and the paired score interval entirely above 50%.')
        if not self.run['candidate'].startswith('neural-'):raise ValueError('Only a saved neural challenger can be promoted here.')
        self.trainer.registry['champion']=self.run['candidate'];self.trainer.save_registry();return self.status()
