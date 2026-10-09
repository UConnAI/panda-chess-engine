import base64
import importlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / '.build/site'

class WebTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(dir=ROOT/'.build')
        cls.app = Path(cls.temp.name)/'app'
        with zipfile.ZipFile(SITE/'engine.zip') as archive: archive.extractall(cls.app)
        sys.path.insert(0,str(cls.app))
        cls.api=importlib.import_module('browser_api')

    @classmethod
    def tearDownClass(cls): cls.temp.cleanup()

    def setUp(self):
        self.storage=Path(self.temp.name)/self.id().split('.')[-1]
        self.api.initialize(self.app,self.storage)

    def test_shared_dispatch_training_export_and_reload(self):
        self.api.request('project/profile',dict(title='My browser engine',author='Student',description='Experiment'))
        trained=self.api.request('train',dict(count=200,epochs=1,rate=.01))
        self.assertEqual(len(trained['models']),1)
        move=self.api.request('move',dict(moves=[],kind='random'))
        self.assertEqual(move['board']['turn'],'Black')
        self.api.request('save-game',dict(moves=['e2e4'],kind='random'))
        payload=base64.b64decode(self.api.request('download/my-project.zip'))
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            names=archive.namelist()
            self.assertIn('panda-chess-project/models/neural-0001.json',names)
            self.assertIn('panda-chess-project/project_data/project.json',names)
            self.assertIn('panda-chess-project/MY_RESULTS.md',names)
            self.assertIn('panda-chess-project/games/club-0001.pgn',names)
            self.assertNotIn('panda-chess-project/INSTRUCTOR.md',names)
            self.assertIsNone(archive.testzip())
        clean=base64.b64decode(self.api.request('download/project.zip'))
        with zipfile.ZipFile(io.BytesIO(clean)) as archive:
            self.assertFalse(any('/models/' in n or '/project_data/' in n for n in archive.namelist()))
        self.api.initialize(self.app,self.storage)
        self.assertEqual(self.api.request('status')['id'],trained['id'])
        self.assertEqual(self.api.request('project')['title'],'My browser engine')

    def test_category_deletion_keeps_unselected_work_and_reserved_model_ids(self):
        trained=self.api.request('train',dict(count=200,epochs=1,rate=.01))
        self.api.request('project/profile',dict(title='Keep my profile',author='Student',description=''))
        self.api.request('save-game',dict(moves=['e2e4'],kind='random'))
        rows=self.api.request('browser/storage')
        self.assertEqual({r['id'] for r in rows},{'models','arena','games','settings'})
        self.assertTrue(next(r for r in rows if r['id']=='models')['bytes']>0)
        with self.assertRaises(ValueError):self.api.request('browser/delete-categories',dict(categories=['models','../games']))
        self.assertEqual(len(self.api.request('status')['models']),1)
        self.api.request('browser/delete-categories',dict(categories=['models']))
        self.assertEqual(self.api.request('status')['models'],[])
        self.assertEqual(self.api.request('project')['title'],'Keep my profile')
        self.assertEqual(len(self.api.request('games')),1)
        later=self.api.request('train',dict(count=200,epochs=1,rate=.01))
        self.assertNotEqual(trained['id'],later['id'])
        self.api.request('browser/delete-categories',dict(categories=['games','settings']))
        self.assertEqual(self.api.request('games'),[])
        self.assertEqual(self.api.request('project')['title'],'My Chess Engine')
        self.assertEqual(len(self.api.request('status')['models']),1)

    def test_arena_category_keeps_player_games_and_neural_models(self):
        self.api.request('train',dict(count=200,epochs=1,rate=.01))
        self.api.request('save-game',dict(moves=['e2e4'],kind='random'))
        self.api.request('arena/start',dict(candidate='random',opponent='material',games=2,depth=1,budget=300,cap=40))
        self.api.request('arena/step',{})
        self.assertTrue(self.api.request('arena')['history'])
        self.api.request('browser/delete-categories',dict(categories=['arena']))
        self.assertEqual(self.api.request('arena')['history'],[])
        self.assertEqual(len(self.api.request('games')),1)
        self.assertEqual(len(self.api.request('status')['models']),1)

    def test_static_pages_are_relative_and_private_material_excluded(self):
        for name in ('index.html','lecture.html','take-home.html'):
            text=(SITE/name).read_text(encoding='utf-8')
            self.assertNotIn('href="/',text)
            self.assertNotIn('src="/',text)
            self.assertIn('bridge.js',text)
        with zipfile.ZipFile(SITE/'engine.zip') as archive:
            self.assertNotIn('INSTRUCTOR.md',archive.namelist())
            self.assertFalse(any(n.startswith(('models/','games/','project_data/','external/')) for n in archive.namelist()))

    def test_stockfish_translation_uses_white_perspective_and_legal_line(self):
        fen=self.api.a.chess.Board().fen()
        self.api.accept_stockfish(fen,[dict(score=25,pv=['e2e4','e7e5'],depth=10,nodes=100)],.3)
        self.api.a.references.unlocked=True
        result=self.api.request('move',dict(moves=[],kind='reference-stockfish'))
        self.assertEqual(result['search']['score'],.25)
        self.assertEqual(result['search']['move'],'e2e4')
        black=self.api.a.replay(['e2e4']).fen()
        self.api.accept_stockfish(black,[dict(score=30,pv=['e7e5'],depth=10,nodes=100)],.3)
        self.assertEqual(self.api.cached_stockfish(self.api.a.chess.Board(black))['score'],-.3)
        terminal=self.api.request('analyze',dict(moves=['f2f3','e7e5','g2g4','d8h4'],kind='reference-stockfish'))
        self.assertIsNone(terminal['search']['move'])

    def test_export_removes_deleted_checkpoint_records_but_preserves_ids(self):
        model=self.api.request('train',dict(count=200,epochs=1,rate=.01))['id']
        self.api.request('delete-model',dict(id=model))
        self.assertEqual(len(self.api.request('status')['deleted_models']),1)
        blob=base64.b64decode(self.api.request('download/my-project.zip'))
        with zipfile.ZipFile(io.BytesIO(blob)) as archive:
            registry=json.loads(archive.read('panda-chess-project/models/registry.json'))
            self.assertEqual(registry['deleted_models'],[])
            self.assertEqual(registry['next_model_number'],2)
            self.assertFalse(any('/.trash/' in n for n in archive.namelist()))

if __name__=='__main__': unittest.main()
