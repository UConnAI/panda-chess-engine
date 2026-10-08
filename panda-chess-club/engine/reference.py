"""End-of-session references: prepared Panda and an optional local UCI engine."""
import json,time,os,subprocess,hashlib,platform,zipfile,tarfile
from pathlib import Path
from .board import chess
import chess.engine
from training.model import Network

IDS=('reference-neural','reference-stockfish')
# Official release archives include the matching source and license.
STOCKFISH_BUNDLES={
    ('Windows','x86_64'):('stockfish-windows-x86-64.zip','40cc975817e7eee270b03f354810d20956df565420d320f6dd37d454dc81a139','stockfish/stockfish-windows-x86-64.exe'),
    ('Darwin','arm64'):('stockfish-macos-m1-apple-silicon.tar.gz','e52a9f915875a564ddc636e200232fb3b129693c4987ff64be1404dc62dd2ab1','stockfish/stockfish-macos-m1-apple-silicon'),
    ('Darwin','x86_64'):('stockfish-macos-x86-64.tar.gz','8275b1b9f4053cad2d343da80297c7f974e9c346583b65efe88665786214d782','stockfish/stockfish-macos-x86-64'),
}

def unpack_stockfish(folder,system=None,machine=None):
    """Select this computer's verified release and unpack only its executable."""
    system=system or platform.system();machine=(machine or platform.machine()).lower()
    if machine=='amd64':machine='x86_64'
    bundle=STOCKFISH_BUNDLES.get((system,machine))
    if bundle is None:return None
    name,digest,member=bundle
    folder=Path(folder);archive=folder/name
    if not archive.is_file():return None
    if hashlib.sha256(archive.read_bytes()).hexdigest()!=digest:
        raise ValueError('Bundled Stockfish archive checksum failed. Restore the official archive from the repository.')
    target=folder/('stockfish.exe' if system=='Windows' else 'stockfish');temporary=target.with_suffix('.tmp')
    if name.endswith('.zip'):
        with zipfile.ZipFile(archive) as release:payload=release.read(member)
    else:
        with tarfile.open(archive,'r:gz') as release:
            entry=release.getmember(member)
            if not entry.isfile():raise ValueError('Stockfish executable is not a regular file.')
            with release.extractfile(entry) as source:payload=source.read()
    temporary.write_bytes(payload)
    temporary.chmod(0o755);temporary.replace(target)
    return target

class References:
    def __init__(self,trainer,root):
        self.trainer=trainer;self.root=Path(root);self.unlocked=False;self.prepared=None;self.network=None
        path=self.root/'references/prepared.json'
        if path.exists():
            self.prepared=json.loads(path.read_text(encoding='utf-8'))
            if self.prepared['digest']!=trainer.digest:raise ValueError('Reference dataset checksum mismatch.')
            self.network=Network(self.prepared['parameters'])
        folder=self.root/'external'
        target=folder/('stockfish.exe' if os.name=='nt' else 'stockfish')
        self.binary=target if target.is_file() else unpack_stockfish(folder)
    def available(self):
        return ([IDS[0]] if self.network else [])+([IDS[1]] if self.binary else [])
    def status(self,arena):
        completed=any(r['finished'] for r in arena.history())
        eligible=bool(self.trainer.registry['models']) and completed
        result=dict(unlocked=self.unlocked,eligible=eligible,
                    requirements=dict(trained=bool(self.trainer.registry['models']),arena_completed=completed))
        if self.unlocked:
            result.update(available=self.available(),prepared={k:v for k,v in self.prepared.items() if k!='parameters'} if self.prepared else None,
                          stockfish_ready=self.binary is not None)
        return result
    def reveal(self,arena):
        if not self.status(arena)['eligible']:raise ValueError('Train a model and finish an arena trial before revealing references.')
        self.unlocked=True;return self.status(arena)
    def require(self,kind):
        if not self.unlocked:raise ValueError('Reveal the final references first.')
        if kind not in self.available():raise ValueError('Reference is not prepared on this computer. See reference setup in README.')
    def stockfish(self,board):
        self.require(IDS[1]);started=time.perf_counter()
        # Fixed limits are deliberately separate from the learning engine's controls.
        try:
            flags={'creationflags':subprocess.CREATE_NO_WINDOW} if os.name=='nt' else {}
            with chess.engine.SimpleEngine.popen_uci(str(self.binary),timeout=5,**flags) as engine:
                engine.configure({'Threads':1,'Hash':32})
                info=engine.analyse(board,chess.engine.Limit(time=.3),multipv=3)
                candidates=[]
                for row in info:
                    pv=row.get('pv',[])
                    if not pv:continue
                    cp=row['score'].white().score(mate_score=1000000)
                    candidates.append(dict(move=pv[0].uci(),san=board.san(pv[0]),score=cp/100,pv=[m.uci() for m in pv[:8]]))
                top=info[0] if info else {};best=candidates[0] if candidates else None
                return dict(move=best['move'] if best else None,san=best['san'] if best else None,
                            score=best['score'] if best else None,depth=top.get('depth',0),requested_depth=top.get('depth',0),
                            nodes=top.get('nodes',0),evaluated=None,cutoffs=None,moves_skipped=None,
                            seconds=round(time.perf_counter()-started,3),candidates=candidates,
                            pv=best['pv'] if best else [],budget_hit=False,engine=IDS[1],
                            external=True,engine_name=engine.id.get('name','Stockfish'))
        except (OSError,chess.engine.EngineError,TimeoutError) as e:
            raise ValueError('Local Stockfish could not run. Check the executable for your OS and CPU.') from e
