import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from engine.board import chess
from engine.preview import preview_line

class PreviewTests(unittest.TestCase):
    def test_alternating_frames_preserve_input_and_start_position(self):
        history=['e2e4'];line=['e7e5','g1f3','b8c6']
        frames=preview_line(history,line)['frames']
        self.assertEqual(history,['e2e4']);self.assertEqual(line,['e7e5','g1f3','b8c6'])
        self.assertEqual([f['side'] for f in frames],[None,'Black','White','Black'])
        self.assertEqual([f['san'] for f in frames],[None,'e5','Nf3','Nc6'])
        self.assertIn('p',frames[-1]['board']['pieces'].values())
        b=chess.Board();b.push_uci('e2e4')
        self.assertEqual(frames[0]['board']['fen'],b.fen())
        for move in line:b.push_uci(move)
        self.assertEqual(frames[-1]['board']['fen'],b.fen())
    def test_castling_en_passant_and_promotion_frames(self):
        cases=[('r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1',['e1g1'],{'g1':'K','f1':'R'}),
               ('4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1',['e5d6'],{'d6':'P'}),
               ('4k3/P7/8/8/8/8/8/4K3 w - - 0 1',['a7a8q'],{'a8':'Q'})]
        for fen,line,expected in cases:
            with self.subTest(fen=fen):
                pieces=preview_line(line=line,fen=fen)['frames'][-1]['board']['pieces']
                for square,piece in expected.items():self.assertEqual(pieces[square],piece)
    def test_illegal_or_unbounded_previews_rejected(self):
        for line in (None,'e2e4',['e2e5'],['e2e4']*33,[123]):
            with self.subTest(line=line):
                with self.assertRaises(ValueError):preview_line([],line)
        with self.assertRaises(ValueError):preview_line(line=[],fen='8/8/8/8/8/8/8/8 w - - 0 1')
        self.assertEqual(len(preview_line([],[])['frames']),1)

if __name__=='__main__':unittest.main()

class ArenaReplayTests(unittest.TestCase):
    def test_saved_replay_is_read_only_and_validates_record(self):
        import tempfile,json
        from arena.tournament import Arena
        (ROOT/'.build').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT/'.build') as folder:
            root=Path(folder);a=Arena(root,None)
            run=dict(id='run-0001',candidate='random',opponent='material',depth=1,budget=300,results=[dict(game=2,candidate_color='Black',score=None,moves=['g1f3','g8f6','f3g1','f6g8']*10)])
            path=a.dir/'run-0001.json';path.write_text(json.dumps(run));before=path.read_bytes()
            result=a.replay_game('run-0001',2)
            self.assertEqual(len(result['frames']),41)
            self.assertEqual((result['white'],result['black']),('material','random'))
            self.assertEqual(path.read_bytes(),before)
            for id in ['../models/registry','run-no','run-9999']:
                with self.assertRaises(ValueError):a.record(id)
            with self.assertRaises(ValueError):a.replay_game('run-0001',1)

    def test_delete_record_removes_only_match_files_and_reserves_ids(self):
        import tempfile,json
        from arena.tournament import Arena
        class TrainerStub:
            registry={'champion':'positional','models':[]}
        (ROOT/'.build').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT/'.build') as folder:
            a=Arena(folder,TrainerStub());a.start('random','material',2,1,300,40)
            original=a.run['id'];a.run['finished']=True;a.save()
            pgn=a.dir/(original+'-game-001.pgn');pgn.write_text('test game')
            unrelated=a.dir/'keep.txt';unrelated.write_text('keep')
            self.assertEqual(a.record_size(original),(a.dir/(original+'.json')).stat().st_size+pgn.stat().st_size)
            response=a.delete_record(original)
            self.assertFalse(response['active']);self.assertEqual(response['history'],[])
            self.assertTrue(unrelated.exists());self.assertFalse(pgn.exists())
            a.start('random','material',2,1,300,40)
            self.assertEqual(a.run['id'],'run-0002')
            with self.assertRaises(ValueError):a.delete_record('../keep')
