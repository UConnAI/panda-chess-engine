import json,sys,tempfile,unittest,hashlib,io,tarfile
from unittest.mock import patch
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from engine.board import chess
from training.train import Trainer
from training.model import Network
from training.prepare_reference import prepare
from engine.reference import References,unpack_stockfish,STOCKFISH_BUNDLES
from engine.bot import decide
from arena.tournament import Arena

class ReferenceTests(unittest.TestCase):
    def test_bundled_archive_rejects_modified_content_before_extraction(self):
        (ROOT/'.build').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT/'.build') as folder:
            path=Path(folder)/'stockfish-windows-x86-64.zip'
            path.write_bytes(b'not the official release')
            with self.assertRaisesRegex(ValueError,'checksum failed'):unpack_stockfish(folder,'Windows','x86_64')
            self.assertFalse((Path(folder)/'stockfish.exe').exists())

    def test_mac_architecture_selection_and_executable_permissions(self):
        (ROOT/'.build').mkdir(exist_ok=True)
        for machine in ('arm64','x86_64'):
            with self.subTest(machine=machine),tempfile.TemporaryDirectory(dir=ROOT/'.build') as folder:
                name,_,member=STOCKFISH_BUNDLES[('Darwin',machine)]
                path=Path(folder)/name;payload=b'mac executable fixture'
                with tarfile.open(path,'w:gz') as release:
                    entry=tarfile.TarInfo(member);entry.size=len(payload)
                    release.addfile(entry,io.BytesIO(payload))
                bundle=(name,hashlib.sha256(path.read_bytes()).hexdigest(),member)
                with patch.dict(STOCKFISH_BUNDLES,{('Darwin',machine):bundle}):
                    target=unpack_stockfish(folder,'Darwin',machine)
                self.assertEqual(target.name,'stockfish');self.assertEqual(target.read_bytes(),payload)
                self.assertFalse((Path(folder)/'stockfish.exe').exists())
                if sys.platform!='win32':self.assertEqual(target.stat().st_mode & 0o777,0o755)
                self.assertIsNone(unpack_stockfish(folder,'Linux',machine))

    def test_reveal_gates_play_and_keeps_reference_out_of_member_registry(self):
        (ROOT/'.build').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT/'.build') as folder:
            root=Path(folder);trainer=Trainer(root);arena=Arena(root,trainer)
            (root/'references').mkdir()
            (root/'references/prepared.json').write_text(json.dumps(dict(digest=trainer.digest,parameters=Network().json())))
            refs=References(trainer,root);trainer.references=refs
            self.assertEqual(set(refs.status(arena)),{'unlocked','eligible','requirements'})
            with self.assertRaises(ValueError):refs.reveal(arena)
            with self.assertRaises(ValueError):decide(chess.Board(),'reference-neural',trainer,1,300)
            trainer.train(200,1,.01)
            with self.assertRaises(ValueError):refs.reveal(arena)
            arena.start('material','random',2,1,300,40)
            for _ in range(80):
                if arena.run['finished']:break
                arena.step()
            self.assertTrue(refs.reveal(arena)['unlocked'])
            result=decide(chess.Board(),'reference-neural',trainer,1,300)
            self.assertIn(chess.Move.from_uci(result['move']),chess.Board().legal_moves)
            self.assertEqual(len(trainer.registry['models']),1)
            with self.assertRaises(ValueError):decide(chess.Board(),'reference-stockfish',trainer)
            arena.start('reference-neural','random',2,1,300,40)
            arena.step();self.assertEqual(arena.run['telemetry']['engine'],'reference-neural')
            self.assertFalse(References(trainer,root).unlocked)
    def test_preparation_preserves_architecture_and_selects_using_validation(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'.build') as folder:
            path=Path(folder)/'prepared.json'
            report=prepare(path,max_epochs=5,patience=2)
            saved=json.loads(path.read_text());net=Network(saved['parameters'])
            self.assertEqual(net.p['w'].shape,(782,32))
            self.assertEqual(report['seed'],314)
            self.assertLessEqual(saved['epoch'],saved['epochs_run'])
            self.assertEqual(saved['validation']['n'],400);self.assertEqual(saved['test']['n'],401)
            self.assertLess(saved['validation']['mse'],saved['initial_validation']['mse'])
            self.assertIn('test split measured once',saved['selection'])

if __name__=='__main__':unittest.main()
