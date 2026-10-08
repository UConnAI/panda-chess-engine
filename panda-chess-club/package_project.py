"""Build the portable source project without local models or participant data."""
import argparse
import io
import json
import re
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parent
FILES = ['main.py', 'package_project.py', 'requirements.txt', 'README.md',
         'LICENSE.txt', '.gitignore', '.gitattributes', 'Start Panda Chess.cmd','package_manifest.json']
EXCLUDED = {'ui/lecture.html', 'ui/take-home.html'}
FOLDERS = ['engine', 'training', 'arena', 'ui', 'tests', 'lib', 'data']

def project_zip(root=ROOT):
    root = Path(root)
    paths = [root / name for name in FILES]
    # Only the intentional reference checkpoint; never members' runtime models.
    reference=root/'references/prepared.json'
    if reference.is_file():paths.append(reference)
    # An explicit source list prevents untracked personal files under data/lib
    # from leaking into downloads. Update this list when adding source files.
    for name in json.loads((root/'package_manifest.json').read_text(encoding='utf-8')):
        relative=Path(name)
        if relative.is_absolute() or '..' in relative.parts or relative.parts[0] not in FOLDERS:
            raise ValueError('Invalid package manifest entry.')
        if name not in EXCLUDED:paths.append(root/relative)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(paths):
            relative = path.relative_to(root).as_posix()
            if relative in EXCLUDED:continue
            if path.is_symlink():
                raise ValueError('Package inputs must be regular project files.')
            name = 'panda-chess-project/' + path.relative_to(root).as_posix()
            info = zipfile.ZipInfo(name, date_time=(2026, 10, 6, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            override = root / 'take-home' / ('PROJECT.md' if relative == 'README.md' else relative)
            payload = override.read_bytes() if override.is_file() else path.read_bytes()
            if relative == 'ui/app.js':
                text = payload.decode('utf-8').replace('All earlier chess demos stay separate.', '').replace('Games become our club’s story.', 'Saved games').replace('Club member', 'Player')
                text = re.sub(r'<section class="panel"><h2>The next layers</h2>.*?</section>', '', text, flags=re.S)
                payload = text.encode('utf-8')
            archive.writestr(info, payload)
    return buffer.getvalue()

def write_project(payload, target):
    """Extract the source allowlist; leave existing runtime records untouched."""
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        for name in archive.namelist():
            relative = Path(name).relative_to('panda-chess-project')
            destination = Path(target) / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(archive.read(name))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=ROOT / '.build' / 'Panda-Chess-Portfolio-Project.zip')
    parser.add_argument('--project-dir', type=Path, help='Also write the runnable take-home source into this separate folder.')
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    payload = project_zip()
    args.output.write_bytes(payload)
    if args.project_dir:
        target = args.project_dir.resolve()
        template = (ROOT / 'take-home').resolve()
        if target == ROOT.resolve() or ROOT.resolve().is_relative_to(target) or target == template or target.is_relative_to(template):
            parser.error('Export to .build/personal-project or a separate folder; keep source and templates intact.')
        write_project(payload, target)
        print(target)
    print(args.output.resolve())
