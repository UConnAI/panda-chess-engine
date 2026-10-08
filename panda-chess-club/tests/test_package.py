import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from package_project import project_zip

class PackageTests(unittest.TestCase):
    def test_clean_complete_reproducible_archive(self):
        payload = project_zip()
        self.assertEqual(payload, project_zip())
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            names = archive.namelist()
            prefix = 'panda-chess-project/'
            for name in ['main.py', 'README.md',
                         '.gitignore', '.gitattributes', 'package_project.py',
                         'engine/search.py', 'training/model.py', 'arena/tournament.py',
                         'ui/index.html', 'lib/chess/__init__.py', 'LICENSE.txt']:
                self.assertIn(prefix + name, names)
            for name in names:
                self.assertTrue(name.startswith(prefix))
                self.assertFalse(set(Path(name).parts) & {'models', 'games', 'project_data', 'arena_results', '.build', '__pycache__', '.git', '.venv'})
            for excluded in ['INSTRUCTOR.md','START_HERE.md','MY_PROJECT.md','EXPERIMENTS.csv','ui/lecture.html','ui/take-home.html']:
                self.assertNotIn(prefix+excluded,names)
            index=archive.read(prefix+'ui/index.html').decode()
            for route in ['/lecture','/take-home','/instructor','/start-here']:
                self.assertNotIn(route,index)
            self.assertNotIn('<footer',index)
            self.assertIn('data-personal',index)
            self.assertIn('My engine',index)
            self.assertIn(prefix+'ui/studio.js',names)
            self.assertIn(prefix+'engine/personal.py',names)
            self.assertNotIn('The next layers',archive.read(prefix+'ui/app.js').decode())
            source = archive.read(prefix + 'data/positions.jsonl')
            provenance = json.loads(archive.read(prefix + 'data/provenance.json'))
            self.assertEqual(hashlib.sha256(source).hexdigest(), provenance['sha256'])
            self.assertIsNone(archive.testzip())

    def test_export_is_independent_and_preserves_runtime(self):
        from package_project import write_project
        (ROOT / '.build').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / '.build') as temp:
            target = Path(temp)
            saved = target / 'project_data' / 'project.json'
            saved.parent.mkdir()
            saved.write_text('personal record')
            write_project(project_zip(), target)
            self.assertEqual(saved.read_text(), 'personal record')
            self.assertIn('# My Chess Engine', (target / 'README.md').read_text(encoding='utf-8'))
            self.assertIn('data-personal', (target / 'ui/index.html').read_text(encoding='utf-8'))
            self.assertTrue((target / 'engine/search.py').exists())
            self.assertFalse((target / 'take-home').exists())
            self.assertFalse((target / 'INSTRUCTOR.md').exists())

    def test_unlisted_runtime_and_secret_files_excluded(self):
        # A tiny fixture exercises the allowlist without modifying live app data.
        from package_project import FILES, FOLDERS
        (ROOT / '.build').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / '.build') as temp:
            root = Path(temp)
            for name in FILES:
                (root / name).write_text('fixture')
            (root/'package_manifest.json').write_text('[]')
            for folder in FOLDERS:
                (root / folder).mkdir()
            for name in ['.env', 'personal.json', 'weights.json']:
                (root / name).write_text('private')
            (root / 'data/.env').write_text('private')
            (root / 'data/personal.json').write_text('private')
            (root / 'lib/.env').write_text('private')
            (root / 'lib/personal.json').write_text('private')
            with zipfile.ZipFile(io.BytesIO(project_zip(root))) as archive:
                self.assertFalse(any('private' in archive.read(n).decode() for n in archive.namelist()))

if __name__ == '__main__':
    unittest.main()
