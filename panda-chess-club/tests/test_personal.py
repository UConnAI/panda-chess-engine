import json,tempfile,unittest,threading,urllib.request
from main import make_server
from pathlib import Path
from engine.personal import PersonalProject,DEFAULTS,evaluate,weights
from engine.board import chess,replay
from engine.bot import decide
from training.train import Trainer
from arena.tournament import Arena
ROOT=Path(__file__).resolve().parents[1]
class PersonalTests(unittest.TestCase):
 def setUp(self):
  (ROOT/'.build').mkdir(exist_ok=True);self.tmp=tempfile.TemporaryDirectory(dir=ROOT/'.build');self.root=Path(self.tmp.name);self.project=PersonalProject(self.root)
 def tearDown(self):self.tmp.cleanup()
 def test_weights_reject_nonfinite_or_out_of_range(self):
  for bad in [dict(DEFAULTS,material=float('nan')),dict(DEFAULTS,center=2),dict(DEFAULTS,shield=True),{}]:
   with self.assertRaises(ValueError):weights(bad)
 def test_version_snapshot_persistence_and_symmetry(self):
  self.project.create(dict(name='Shelter',weights=DEFAULTS,hypothesis='Protect the king'))
  self.project.create(dict(name='Active',weights=dict(DEFAULTS,activity=.1)))
  loaded=PersonalProject(self.root);self.assertEqual(loaded.get('custom-0001')['weights'],DEFAULTS);self.assertEqual(len(loaded.data['bots']),2)
  b=replay(['e2e4','c7c5','g1f3']);self.assertAlmostEqual(evaluate(b,DEFAULTS),-evaluate(b.mirror(),DEFAULTS))
  self.project.profile(dict(title='My Engine',author='A',description='Experiment'))
  self.assertEqual(PersonalProject(self.root).data['title'],'My Engine')
 def test_custom_engine_uses_recipe_and_runs_in_arena(self):
  t=Trainer(self.root);t.personal=self.project
  self.project.create(dict(name='My Bot',weights=DEFAULTS))
  b=chess.Board();r=decide(b,'custom-0001',t,1,300);self.assertIn(chess.Move.from_uci(r['move']),b.legal_moves)
  a=Arena(self.root,t);a.start('custom-0001','random',2,1,300,40);a.step();self.assertEqual(a.run['candidate'],'custom-0001')
  self.assertEqual(t.status()['custom_bots'][0]['name'],'My Bot')
 def test_experiment_and_report_retain_actual_results(self):
  self.project.create(dict(name='My Bot',weights=DEFAULTS,hypothesis='More shelter'))
  r=self.project.inspect(dict(position='trap',weights=DEFAULTS));self.assertAlmostEqual(r['score'],sum(r['terms'].values()))
  self.project.experiment(dict(id='custom-0001',notes='Compare replies'))
  t=Trainer(self.root);t.personal=self.project;a=Arena(self.root,t)
  report=self.project.report(a);self.assertIn('Compare replies',report);self.assertIn('My Bot',report);self.assertEqual(len(self.project.data['experiments'][0]['rows']),3)
  for r in self.project.data['experiments'][0]['rows']:self.assertTrue(r['custom_move']);self.assertTrue(r['baseline_move'])
 def test_http_profile_recipe_inspection_and_report(self):
  server=make_server(0,self.root);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();base='http://127.0.0.1:'+str(server.server_port)
  def post(route,value):
   req=urllib.request.Request(base+'/api/'+route,data=json.dumps(value).encode(),headers={'Content-Type':'application/json'})
   return json.load(urllib.request.urlopen(req))
  try:
   post('project/profile',dict(title='My HTTP engine',author='Test',description='Own recipe'))
   post('project/bot',dict(name='Shelter',weights=DEFAULTS))
   r=post('project/inspect',dict(position='capture',weights=DEFAULTS));self.assertTrue(r['search']['move'])
   r=post('move',dict(kind='custom-0001',moves=[],depth=1,budget=300));self.assertTrue(r['search']['move'])
   status=json.load(urllib.request.urlopen(base+'/api/status'));self.assertEqual(status['custom_bots'][0]['name'],'Shelter')
   report=urllib.request.urlopen(base+'/project/report.md').read().decode();self.assertIn('My HTTP engine',report);self.assertIn('custom-0001',report)
  finally:server.shutdown();server.server_close();thread.join()
if __name__=='__main__':unittest.main()
