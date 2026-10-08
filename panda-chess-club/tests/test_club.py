import os
os.environ['OPENBLAS_NUM_THREADS']='1'
import sys,json,tempfile,unittest,threading,urllib.request,urllib.error
from unittest.mock import patch
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
from engine.board import chess,replay
import chess.pgn
from engine.evaluation import material,positional
from engine.search import search
from engine.bot import decide
from training.model import Network,encode
from training.train import Trainer
from arena.tournament import Arena,openings
from arena.elo import summarize
from main import make_server

class ClubTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        (ROOT/'.build').mkdir(exist_ok=True);cls.tmp=tempfile.TemporaryDirectory(dir=ROOT/'.build');cls.root=Path(cls.tmp.name);cls.trainer=Trainer(cls.root)
    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()
    def test_rules_special_moves_and_draws(self):
        b=chess.Board('r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1');self.assertIn(chess.Move.from_uci('e1g1'),b.legal_moves)
        b=replay(['e2e4','a7a6','e4e5','d7d5']);self.assertTrue(b.is_en_passant(chess.Move.from_uci('e5d6')))
        b=chess.Board('7k/P7/8/8/8/8/8/7K w - - 0 1');self.assertIn(chess.Move.from_uci('a7a8n'),b.legal_moves)
        b=chess.Board()
        for move in ['g1f3','g8f6','f3g1','f6g8']*2:b.push_uci(move)
        self.assertTrue(b.can_claim_threefold_repetition())
        self.assertTrue(chess.Board('7k/8/8/8/8/8/8/KR6 w - - 100 60').can_claim_fifty_moves())
        self.assertTrue(chess.Board('7k/8/8/8/8/8/8/K7 w - - 0 1').is_insufficient_material())
        self.assertTrue(chess.Board('7k/5Q2/6K1/8/8/8/8/8 b - - 0 1').is_stalemate())
    def test_castling_moves_both_pieces_and_respects_safety(self):
        for color,move,king,rook in [(True,'e1g1','g1','f1'),(True,'e1c1','c1','d1'),(False,'e8g8','g8','f8'),(False,'e8c8','c8','d8')]:
            b=chess.Board('r3k2r/8/8/8/8/8/8/R3K2R '+('w' if color else 'b')+' KQkq - 0 1')
            self.assertIn(chess.Move.from_uci(move),b.legal_moves)
            b.push_uci(move)
            self.assertEqual(b.piece_at(chess.parse_square(king)),chess.Piece(chess.KING,color))
            self.assertEqual(b.piece_at(chess.parse_square(rook)),chess.Piece(chess.ROOK,color))
        for fen in ['r3k2r/8/8/8/8/8/4r3/R3K2R w KQkq - 0 1','r3kr1r/8/8/8/8/8/8/R3K2R w KQkq - 0 1','r3k2r/8/8/8/8/8/8/R3KB1R w KQkq - 0 1','r3k2r/8/8/8/8/8/8/R3K2R w - - 0 1']:
            self.assertNotIn(chess.Move.from_uci('e1g1'),chess.Board(fen).legal_moves)
    def test_classical_color_symmetry(self):
        b=replay(['e2e4','c7c5','g1f3'])
        for f in (material,positional):self.assertAlmostEqual(f(b),-f(b.mirror()))
    def test_search_mate_tactics_and_restoration(self):
        b=chess.Board('7k/5Q2/6K1/8/8/8/8/8 w - - 0 1');fen=b.fen();r=search(b,material,2,3000);self.assertEqual(b.fen(),fen);b.push_uci(r['move']);self.assertTrue(b.is_checkmate())
        b=chess.Board('4k3/3r4/8/8/p2Q4/8/8/6K1 w - - 0 1');self.assertEqual(search(b,material,1,3000)['san'],'Qxd7+');self.assertEqual(search(b,material,2,3000)['san'],'Qxa4')
    def test_pruning_equal_result_and_measured_savings(self):
        b=chess.Board('4k3/3r4/8/8/p2Q4/8/8/6K1 w - - 0 1')
        a=search(b,material,3,30000,False,False);c=search(b,material,3,30000,True,False)
        self.assertEqual((a['depth'],c['depth']),(3,3));self.assertEqual(a['score'],c['score']);self.assertEqual(a['move'],c['move']);self.assertLess(c['nodes'],a['nodes']);self.assertGreater(c['cutoffs'],0)
    def test_budget_returns_legal_previous_iteration(self):
        b=chess.Board();fen=b.fen();r=search(b,positional,4,100)
        self.assertTrue(r['budget_hit']);self.assertLess(r['depth'],4);self.assertLessEqual(r['nodes'],100);self.assertIn(chess.Move.from_uci(r['move']),b.legal_moves);self.assertEqual(fen,b.fen())
    def test_seeded_random_is_legal_and_reproducible(self):
        b=chess.Board();a=decide(b,'random',self.trainer);c=decide(b,'random',self.trainer);self.assertEqual(a,c);self.assertIn(chess.Move.from_uci(a['move']),b.legal_moves)
    def test_encoding_preserves_game_state(self):
        b=chess.Board();x=encode(b);self.assertEqual(len(x),782);self.assertEqual(sum(x[:768]),32)
        b.turn=False;self.assertNotEqual(encode(b)[768],x[768]);b.castling_rights=0;self.assertEqual(sum(encode(b)[769:773]),0)
    def test_neural_gradient_finite_difference(self):
        n=Network();x=np.array([encode(chess.Board()),encode(replay(['e2e4']))]);y=np.array([.2,-.3]);g=n.gradient(x,y)
        for key,index in [('w',(12,4)),('b',3),('v',5),('c',0)]:
            old=n.p[key][index];eps=1e-6;n.p[key][index]=old+eps;plus=np.mean((n.forward(x)[0]-y)**2);n.p[key][index]=old-eps;minus=np.mean((n.forward(x)[0]-y)**2);n.p[key][index]=old
            self.assertAlmostEqual(g[key][index],(plus-minus)/(2*eps),places=6)
    def test_training_resume_immutable_and_validation_not_training(self):
        t=self.trainer;s=t.train(200,10,.01);p=t.dir/(s['id']+'.json');original=p.read_bytes();t.train(200,10,.01,True);t.train(200,10,.01,True);expected=t.net.json();self.assertEqual(p.read_bytes(),original)
        s=t.train(200,30,.01);self.assertEqual(expected,t.net.json());self.assertLess(s['history'][-1]['train_mse'],s['history'][0]['train_mse'])
        v=[r['y'] for r in t.rows['validation']];test=[r['y'] for r in t.rows['test']]
        try:
            for r in t.rows['validation']+t.rows['test']:r['y']=.99
            t.train(200,30,.01);self.assertEqual(expected,t.net.json())
        finally:
            for r,y in zip(t.rows['validation'],v):r['y']=y
            for r,y in zip(t.rows['test'],test):r['y']=y
        self.assertTrue(np.isfinite(t.get_network(s['id']).score(chess.Board())))
    def test_splits_and_teacher_provenance(self):
        groups=[{r['fen'].split()[0] for r in self.trainer.rows[k]} for k in ('train','validation','test')]
        for i in range(3):
            for j in range(i):self.assertFalse(groups[i]&groups[j])
        self.assertEqual(self.trainer.digest,self.trainer.provenance['sha256'])
    def test_model_delete_restore_protection_and_unique_ids(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'.build') as folder:
            t=Trainer(folder);first=t.train(200,1,.01)['id'];second=t.train(200,1,.01)['id']
            original=(t.dir/(first+'.json')).read_bytes()
            t.delete_model(first)
            self.assertEqual(t.current['id'],second)
            self.assertFalse((t.dir/(first+'.json')).exists())
            self.assertEqual((t.dir/'.trash'/(first+'.json')).read_bytes(),original)
            with self.assertRaises(ValueError):t.get_network(first)
            t.restore_model(first);self.assertEqual((t.dir/(first+'.json')).read_bytes(),original)
            t.registry['champion']=first
            with self.assertRaises(ValueError):t.delete_model(first)
            t.registry['champion']='positional'
            with self.assertRaises(ValueError):t.delete_model(first,[first])
            with self.assertRaises(ValueError):t.delete_model('../registry')
            t.delete_model(second);self.assertEqual(t.current['id'],first)
            third=t.train(200,1,.01)['id'];self.assertNotIn(third,(first,second))
            t.delete_model(third);t.delete_model(first);self.assertFalse(t.status()['ready'])
            self.assertIsNone(t.net)
            t.restore_model(second);self.assertEqual(t.current['id'],second)
            reloaded=Trainer(folder);self.assertEqual(reloaded.current['id'],second)
            self.assertNotIn(third,[r['id'] for r in reloaded.registry['models']])
            fourth=reloaded.train(200,1,.01)['id'];self.assertGreater(int(fourth.split('-')[1]),int(third.split('-')[1]))
    def test_permanent_delete_sizes_failure_and_reserved_ids(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'.build') as folder:
            t=Trainer(folder);first=t.train(200,1,.01)['id']
            size=(t.dir/(first+'.json')).stat().st_size
            self.assertEqual(t.status()['models'][0]['size_bytes'],size)
            with self.assertRaises(ValueError):t.permanently_delete_model(first)
            t.delete_model(first)
            self.assertEqual(t.status()['deleted_models'][0]['size_bytes'],size)
            with patch.object(Path,'unlink',side_effect=PermissionError('Locked file')):
                with self.assertRaises(PermissionError):t.permanently_delete_model(first)
            self.assertEqual(Trainer(folder).status()['deleted_models'][0]['id'],first)
            t.registry.pop('next_model_number',None)
            t.permanently_delete_model(first)
            self.assertFalse((t.dir/'.trash'/(first+'.json')).exists())
            self.assertEqual(Trainer(folder).status()['deleted_models'],[])
            for id in (first,'../registry'):
                with self.assertRaises(ValueError):t.permanently_delete_model(id)
            with self.assertRaises(ValueError):t.restore_model(first)
            self.assertNotEqual(Trainer(folder).train(200,1,.01)['id'],first)
    def test_relative_elo_and_censoring_gate(self):
        r=dict(results=[dict(score=1),dict(score=0)],finished=True,games=2,opponent='x',champion_at_start='x')
        s=summarize(r);self.assertEqual(s['relative_elo'],0);self.assertFalse(s['promotable'])
        r['results'][1]['score']=None;s=summarize(r);self.assertIsNone(s['relative_elo']);self.assertFalse(s['promotable'])
        r['results']=[dict(score=1) for _ in range(40)];r['games']=40;self.assertTrue(summarize(r)['promotable'])
    def test_relative_elo_finite_sweeps_and_unresolved_bounds(self):
        r=dict(results=[dict(score=x) for x in [1,1,1,0]],finished=True,games=4,opponent='x',champion_at_start='x')
        self.assertAlmostEqual(summarize(r)['relative_elo'],190.84850188786498)
        r['results']=[dict(score=1) for _ in range(4)]
        self.assertIsNone(summarize(r)['relative_elo'])
        r['results']=[dict(score=1),dict(score=None)];r['games']=2
        s=summarize(r);self.assertEqual(s['score_bounds'],[.5,1]);self.assertEqual(s['elo_bounds'],[0,None]);self.assertEqual(s['unresolved'],1)
        self.assertIsNone(s['relative_elo']);self.assertFalse(s['promotable'])
        r['results']=[];r['finished']=False
        self.assertEqual(summarize(r)['score_bounds'],[0,1])
    def test_arena_pair_terminates_persists_and_exports(self):
        a=Arena(self.root,self.trainer);a.start('material','random',2,1,300,40)
        for _ in range(80):
            if a.run['finished']:break
            a.step()
        self.assertTrue(a.run['finished']);self.assertEqual([r['candidate_color'] for r in a.run['results']],['White','Black'])
        self.assertEqual(Arena(self.root,self.trainer).run,a.run)
        for p in a.dir.glob('*.pgn'):
            with p.open() as f:g=chess.pgn.read_game(f)
            self.assertFalse(g.errors)
        with self.assertRaises(ValueError):a.promote()
        starts=openings(20);self.assertEqual(starts,openings(20));self.assertEqual(len({replay(m).board_fen() for m in starts}),20)
    def test_http_and_club_game_export(self):
        folder=self.root/'http';folder.mkdir();server=make_server(0,folder);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();base=f'http://127.0.0.1:{server.server_port}'
        def post(route,obj,origin=None):
            headers={'Content-Type':'application/json'}
            if origin:headers['Origin']=origin
            return json.load(urllib.request.urlopen(urllib.request.Request(base+'/api/'+route,data=json.dumps(obj).encode(),headers=headers)))
        try:
            self.assertFalse(json.load(urllib.request.urlopen(base+'/api/references'))['unlocked'])
            with self.assertRaises(urllib.error.HTTPError):post('references/reveal',{})
            frames=post('preview-line',dict(moves=[],line=['e2e4','e7e5']))['frames']
            self.assertEqual([f['side'] for f in frames],[None,'White','Black'])
            self.assertEqual(post('board',dict(moves=[]))['board']['fen'],frames[0]['board']['fen'])
            with self.assertRaises(urllib.error.HTTPError):post('preview-line',dict(moves=[],line=['e2e5']))
            index=urllib.request.urlopen(base).read().decode();self.assertIn('MY CHESS ENGINE' if 'data-personal' in index else 'PANDA CHESS CLUB',index);r=post('move',dict(moves=['e2e4'],kind='material',depth=2,budget=300));self.assertIn(chess.Move.from_uci(r['search']['move']),replay(['e2e4']).legal_moves)
            download=urllib.request.urlopen(base+'/download/project.zip')
            self.assertEqual(download.headers.get_content_type(),'application/zip');self.assertIn('attachment',download.headers['Content-Disposition']);self.assertTrue(download.read().startswith(b'PK'))
            if (ROOT/'ui/take-home.html').exists():
                self.assertIn('Download',urllib.request.urlopen(base+'/take-home').read().decode())
            else:
                for route in ('/take-home','/lecture','/instructor','/start-here'):
                    with self.assertRaises(urllib.error.HTTPError) as error:urllib.request.urlopen(base+route)
                    self.assertEqual(error.exception.code,404)
            saved=post('save-game',dict(moves=['e2e4'],kind='material'));self.assertEqual(saved['result'],'*');self.assertIn('[Result "*"]',urllib.request.urlopen(base+'/pgn/'+saved['file']).read().decode())
            first=post('train',dict(count=200,epochs=1,rate=.01))['id']
            second=post('train',dict(count=200,epochs=1,rate=.01))['id']
            post('arena/start',dict(candidate=first,opponent='random',games=2,depth=1,budget=300,cap=40))
            with self.assertRaises(urllib.error.HTTPError) as error:post('delete-model',dict(id=first))
            self.assertEqual(error.exception.code,400)
            post('arena/start',dict(candidate='material',opponent='random',games=2,depth=1,budget=300,cap=40))
            deleted=post('delete-model',dict(id=first));self.assertEqual(deleted['id'],second)
            self.assertNotIn(first,[m['id'] for m in deleted['models']])
            restored=post('restore-model',dict(id=first));self.assertIn(first,[m['id'] for m in restored['models']])
            post('delete-model',dict(id=first))
            purged=post('permanently-delete-model',dict(id=first));self.assertEqual(purged['deleted_models'],[])
            self.assertFalse((folder/'models'/'.trash'/(first+'.json')).exists())
            for _ in range(80):
                match=post('arena/step',{})
                if match['run']['finished']:break
            self.assertTrue(post('references/reveal',{})['unlocked'])
            comparison=post('references/compare',dict(example='queen'))
            self.assertEqual(comparison['student_id'],second)
            self.assertTrue(comparison['choices'])
            self.assertEqual(comparison['board']['pieces']['d4'],'q')
            for choice in comparison['choices']:
                self.assertIn(choice['move'],comparison['board']['legal_moves'])
            with self.assertRaises(urllib.error.HTTPError):post('move',{},'https://example.com')
        finally:server.shutdown();server.server_close();thread.join()

if __name__=='__main__':unittest.main()
