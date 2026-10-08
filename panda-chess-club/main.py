import os
os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['OMP_NUM_THREADS']='1'
import argparse,json,mimetypes,threading,webbrowser
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import urlparse
from engine.board import chess,replay,board_state
import chess.pgn
from engine.personal import PersonalProject
from engine.bot import decide
from engine.reference import References
from engine.preview import preview_line
from training.train import Trainer
from arena.tournament import Arena
from package_project import project_zip

ROOT=Path(__file__).resolve().parent
def make_server(port=4340,storage=None):
    storage=Path(storage) if storage else ROOT
    trainer=Trainer(storage);trainer.personal=PersonalProject(storage);arena=Arena(storage,trainer);lock=threading.Lock()
    references=References(trainer,ROOT);trainer.references=references
    def post(route,a):
        if route=='project/profile':return trainer.personal.profile(a)
        if route=='project/bot':return trainer.personal.create(a)
        if route=='project/inspect':return trainer.personal.inspect(a)
        if route=='project/experiment':return trainer.personal.experiment(a)
        if route=='preview-line':return preview_line(a.get('moves'),a.get('line'),a.get('fen'))
        if route=='references/reveal':return references.reveal(arena)
        if route=='references/compare':
            if not references.unlocked:raise ValueError('Reveal the final references first.')
            if not trainer.net:raise ValueError('Load a model to compare.')
            import numpy as np
            examples={'queen':'4k3/8/8/8/3q4/8/3R4/4K3 w - - 0 1',
                      'trap':'4k3/3r4/8/8/p2Q4/8/8/6K1 w - - 0 1'}
            example=a.get('example','current')
            if example not in ('current','start',*examples):raise ValueError('Unknown comparison position.')
            b=chess.Board(examples[example]) if example in examples else replay(a.get('moves',[]) if example=='current' else [])
            result=dict(student=trainer.metrics('validation'),student_id=trainer.current['id'],choices=[],board=board_state(b))
            for kind in [trainer.current['id']]+references.available():
                choice=decide(b,kind,trainer,2,3000);leaf=b.copy()
                for move in choice['pv']:leaf.push_uci(move)
                choice['leaf']=board_state(leaf);result['choices'].append(choice)
            if references.network:
                rows=trainer.rows['validation'];prediction,_=references.network.forward(np.array([r['x'] for r in rows]));y=np.array([r['y'] for r in rows])
                result['reference']=dict(mse=float(np.mean((prediction-y)**2)),mae=float(np.mean(np.abs(prediction-y))))
            return result
        if route=='train':return trainer.train(a.get('count',800),a.get('epochs',10),a.get('rate',.01),a.get('resume',False))
        if route=='load':return trainer.load(a.get('id'))
        if route=='delete-model':
            protected=(arena.run['candidate'],arena.run['opponent']) if arena.run and not arena.run['finished'] else ()
            return trainer.delete_model(a.get('id'),protected)
        if route=='restore-model':return trainer.restore_model(a.get('id'))
        if route=='permanently-delete-model':return trainer.permanently_delete_model(a.get('id'))
        if route=='test':return trainer.test()
        if route in ('board','move','analyze'):
            b=replay(a.get('moves',[]))
            if route=='board':return dict(board=board_state(b))
            result=decide(b,a.get('kind','positional'),trainer,a.get('depth',3),a.get('budget',3000),a.get('pruning',True),a.get('ordering',True))
            if route=='move' and result['move']:b.push_uci(result['move'])
            return dict(board=board_state(b),search=result)
        if route=='arena/start':return arena.start(a.get('candidate'),a.get('opponent','champion'),a.get('games',2),a.get('depth',2),a.get('budget',1000),a.get('cap',100))
        if route=='arena/delete':return arena.delete_record(a.get('id'))
        if route=='arena/record':return arena.record(a.get('id'))
        if route=='arena/replay':return arena.replay_game(a.get('id'),a.get('game'))
        if route=='arena/step':return arena.step()
        if route=='arena/promote':return arena.promote()
        if route=='save-game':
            b=replay(a.get('moves',[]));outcome=b.outcome(claim_draw=True);folder=storage/'games';folder.mkdir(exist_ok=True)
            name=f"club-{len(list(folder.glob('club-*.pgn')))+1:04d}.pgn";g=chess.pgn.Game();g.headers['Event']='Club human vs AI';g.headers['White']='Club member';g.headers['Black']=str(a.get('kind','unknown'))[:80];g.headers['Result']=outcome.result() if outcome else '*';node=g
            for move in b.move_stack:node=node.add_variation(move)
            (folder/name).write_text(str(g)+'\n');return dict(file=name,result=g.headers['Result'],note='Saved for later analysis; not automatically used for training.')
        raise KeyError('Unknown action.')
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*_):pass
        def allowed(self):
            hosts={f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}'}
            return self.headers.get('Host') in hosts and self.headers.get('Origin') in (None,*['http://'+h for h in hosts])
        def send(self,code,value,mime='application/json; charset=utf-8',download=None):
            body=value if isinstance(value,bytes) else json.dumps(value,allow_nan=False).encode();self.send_response(code)
            for k,v in {'Content-Type':mime,'Content-Length':str(len(body)),'Cache-Control':'no-store','X-Content-Type-Options':'nosniff','Content-Security-Policy':"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'"}.items():self.send_header(k,v)
            if download:self.send_header('Content-Disposition', 'attachment; filename="'+download+'"')
            self.end_headers();self.wfile.write(body)
        def do_GET(self):
            if not self.allowed():return self.send(403,{'error':'Local access only.'})
            route=urlparse(self.path).path
            if route=='/download/project.zip':return self.send(200,project_zip(),'application/zip','Panda-Chess-Portfolio-Project.zip')
            if route=='/api/project':return self.send(200,trainer.personal.status())
            if route=='/project/report.md':return self.send(200,trainer.personal.report(arena).encode('utf-8'),'text/markdown; charset=utf-8','My-Chess-Project.md')
            if route=='/api/status':
                with lock:return self.send(200,trainer.status())
            if route=='/api/references':
                with lock:return self.send(200,references.status(arena))
            if route=='/api/arena':
                with lock:return self.send(200,arena.status())
            if route=='/api/games':return self.send(200,[p.name for p in sorted((storage/'games').glob('*.pgn'))])
            if route.startswith('/pgn/'):
                name=route.removeprefix('/pgn/');allowed={p.name:p for folder in ['games','arena_results'] for p in (storage/folder).glob('*.pgn')}
                if name in allowed:return self.send(200,allowed[name].read_bytes(),'text/plain; charset=utf-8')
                return self.send(404,{'error':'Unknown game.'})
            files={'/take-home':'ui/take-home.html','/':'ui/index.html','/lecture':'ui/lecture.html','/app.js':'ui/app.js','/references.js':'ui/references.js','/common.js':'ui/common.js','/style.css':'ui/style.css','/provenance':'data/provenance.json'}
            files['/studio.js']='ui/studio.js'
            files['/continuation.js']='ui/continuation.js'
            files={route:path for route,path in files.items() if (ROOT/path).is_file()}
            if route not in files:return self.send(404,{'error':'Not found.'})
            p=ROOT/files[route];return self.send(200,p.read_bytes(),('text/plain' if route in ('/instructor','/start-here') else mimetypes.guess_type(str(p))[0])+'; charset=utf-8')
        def do_POST(self):
            if not self.allowed():return self.send(403,{'error':'Local access only.'})
            if self.headers.get('Content-Type','').split(';')[0]!='application/json':return self.send(415,{'error':'JSON required.'})
            try:
                n=int(self.headers.get('Content-Length','0'))
                if not 0<n<=32768:raise ValueError('Invalid request size.')
                a=json.loads(self.rfile.read(n))
                if not isinstance(a,dict):raise ValueError('Expected an object.')
                with lock:r=post(urlparse(self.path).path.removeprefix('/api/'),a)
                self.send(200,r)
            except (ValueError,TypeError,KeyError,OverflowError) as e:self.send(400,{'error':str(e)})
    class Server(ThreadingHTTPServer):allow_reuse_address=False
    server=Server(('127.0.0.1',port),Handler);server.daemon_threads=True;return server

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=4340);p.add_argument('--no-browser',action='store_true');a=p.parse_args();s=make_server(a.port);url=f'http://127.0.0.1:{s.server_port}'
    print('Panda Chess Club: '+url,flush=True)
    if not a.no_browser:webbrowser.open(url)
    try:s.serve_forever()
    except KeyboardInterrupt:pass
    finally:s.server_close()
