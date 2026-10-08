"""Open the personal project without tracking a second copy of the engine."""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from package_project import project_zip, write_project

if __name__ == '__main__':
    target = ROOT / '.build' / 'personal-project'
    # Keep personal source changes and saved games on subsequent launches.
    if not (target / 'main.py').exists():
        write_project(project_zip(), target)
    print(f'Personal project source: {target}', flush=True)
    raise SystemExit(subprocess.call(
        [sys.executable, str(target / 'main.py'), '--port', '4342', *sys.argv[1:]], cwd=target))
