"""Build a static Pages site from the maintained desktop project. No runtime server."""
import argparse
import ast
import hashlib
import io
import json
from pathlib import Path
import re
import shutil
import sys
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent / 'panda-chess-club'
FISH = 'stockfish-17.1-lite-single-03e3232'
COMMIT = '602fd7e1a571a2be71f242942db90483731f2a1f'

def fetch(url, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        with urllib.request.urlopen(url, timeout=120) as response:
            path.write_bytes(response.read())
    return path.read_bytes()

def build(output=None, offline=False):
    output = Path(output or ROOT / '.build/site').resolve()
    if not output.is_relative_to(ROOT / '.build'):
        raise ValueError('Build output must stay inside panda-chess-web/.build.')
    output.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(SOURCE))
    import package_project
    # The reference is reproducibly prepared at build time, never a participant checkpoint.
    reference = ROOT / '.build/prepared.json'
    if not reference.exists():
        from training.prepare_reference import prepare
        prepare(reference)
    manifest = json.loads((SOURCE/'package_manifest.json').read_text(encoding='utf-8'))
    files = set(package_project.FILES + manifest + ['take-home/PROJECT.md', 'take-home/ui/index.html'])
    with zipfile.ZipFile(output/'engine.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
        for relative in sorted(files):
            archive.writestr(relative, (SOURCE/relative).read_bytes())
        archive.writestr('references/prepared.json', reference.read_bytes())
        archive.writestr('browser_api.py', (ROOT/'browser_api.py').read_bytes())
        tree = ast.parse((SOURCE/'main.py').read_text(encoding='utf-8'))
        server = next(node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name=='make_server')
        post = next(node for node in server.body if isinstance(node,ast.FunctionDef) and node.name=='post')
        imports = '''from engine.board import chess,replay,board_state
import chess.pgn
from engine.personal import PersonalProject
from engine.bot import decide
from engine.reference import References
from engine.preview import preview_line
from training.train import Trainer
from arena.tournament import Arena
'''
        archive.writestr('actions.py', imports + '\n' + ast.unparse(post))
    ui_files=sorted((SOURCE/'ui').iterdir())
    ui_version=hashlib.sha256(b''.join(p.read_bytes() for p in ui_files if p.suffix in ('.js','.css'))+(ROOT/'bridge.js').read_bytes()).hexdigest()[:12]
    for path in ui_files:
        if path.suffix not in ('.html','.js','.css'):continue
        text = path.read_text(encoding='utf-8')
        if path.suffix=='.html':
            text=re.sub(r'(href|src)="/([^"#]*)"', lambda m: m[1]+'="'+({'':'./','lecture':'lecture.html','take-home':'take-home.html'}.get(m[2],m[2]))+'"',text)
            text=text.replace('</head>','<script src="bridge.js" defer></script></head>')
            # Bridge must be defined before common/app execute.
            text=text.replace('<script src="bridge.js" defer></script>','',1).replace('<head>','<head><script src="bridge.js" defer></script>',1)
            text=text.replace('<main>','<main><p id="browser-status" role="status" class="status">Browser edition · no installation · one active workshop tab</p>',1)
        if path.name=='common.js':
            text=re.sub(r'async function api\(path,data\)\{.*?return result;\}', 'async function api(path,data){return window.panda.request(path,data);}',text,count=1)
        if path.name=='references.js':
            text=text.replace('Restarting the server resets the reveal.','Reloading the page resets the reveal; your models and games remain saved.')
            text=text.replace('Local engine ready','Browser engine ready').replace('Process startup adds time.','Stockfish 17.1 Lite, loaded on first use. Loading adds time; this is a different release from the lecture’s Stockfish 18 architecture illustration.')
        if path.name=='take-home.html':
            text=text.replace('<a class="primary linkbutton" href="download/project.zip"', '<a class="primary linkbutton" href="download/my-project.zip"').replace('Download the full project ZIP ↓','Download my project + saved work ↓')
            text=text.replace('Saved models and participant games are not included.','Your saved models, custom recipes, project identity, games and arena records from this browser are included. Deleted models are excluded. Keep this ZIP before clearing browser data.')
            text=text.replace('</div><p class="muted">Python','<a class="linkbutton" href="download/project.zip" download="Panda-Chess-Starter.zip">Clean starter ZIP ↓</a></div><p class="muted">Python',1)
        if path.suffix=='.html':
            text=re.sub(r'(src|href)="([A-Za-z0-9_-]+\.(?:js|css))"',lambda m:f'{m[1]}="{m[2]}?v={ui_version}"',text)
        (output/path.name).write_text(text,encoding='utf-8',newline='\n')
    for name in ('bridge.js','worker.js'):
        shutil.copyfile(ROOT/name, output/name)
    shutil.copyfile(SOURCE/'LICENSE.txt',output/'LICENSE.txt')
    (output/'.nojekyll').write_text('')
    (output/'provenance').write_bytes((SOURCE/'data/provenance.json').read_bytes())
    # Assets are pinned and cached locally; only the selected single-thread engine is shipped.
    cache = ROOT/'.build/vendor'
    assets = {
        FISH+'.js': 'https://unpkg.com/stockfish@17.1.0/src/'+FISH+'.js',
        FISH+'.wasm':'https://unpkg.com/stockfish@17.1.0/src/'+FISH+'.wasm',
        'Copying.txt':f'https://raw.githubusercontent.com/nmrugg/stockfish.js/{COMMIT}/Copying.txt',
        'stockfish-source.zip':f'https://codeload.github.com/nmrugg/stockfish.js/zip/{COMMIT}',
    }
    pins_path=ROOT/'vendor-lock.json'
    pins=json.loads(pins_path.read_text()) if pins_path.exists() else {}
    records={}
    for name,url in assets.items():
        path=cache/name
        if offline and not path.exists():raise ValueError('Offline asset missing: '+name)
        payload=fetch(url,path)
        digest=hashlib.sha256(payload).hexdigest()
        if name in pins and digest!=pins[name]['sha256']:raise ValueError('Vendor checksum mismatch: '+name)
        records[name]=dict(url=url,sha256=digest,bytes=len(payload))
        (output/'vendor').mkdir(exist_ok=True)
        if name=='stockfish-source.zip':
            # The upstream archive also contains every compiled engine variant (~148 MB).
            # Supply all original source/build scripts without those redundant binaries.
            buffer=io.BytesIO()
            with zipfile.ZipFile(io.BytesIO(payload)) as upstream, zipfile.ZipFile(buffer,'w',zipfile.ZIP_DEFLATED) as source:
                for entry in upstream.infolist():
                    if not re.search(r'/src/stockfish-17\.1.*\.(js|wasm)$',entry.filename):
                        source.writestr(entry.filename,upstream.read(entry.filename))
            payload=buffer.getvalue()
        (output/'vendor'/name).write_bytes(payload)
    if not pins_path.exists():pins_path.write_text(json.dumps(records,indent=2)+'\n')
    (output/'vendor/README.txt').write_text(f'Stockfish.js 17.1.0, source commit {COMMIT}. GPLv3.\nCorresponding source: stockfish-source.zip. All upstream source/build scripts are retained; redundant precompiled variants are omitted. Build instructions are inside the source archive.\nPyodide 0.27.7 and NumPy load from the Pyodide CDN; upstream licenses: https://github.com/pyodide/pyodide and https://numpy.org/doc/stable/license.html\n')
    print(output, flush=True)
    return output

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--offline',action='store_true',help='Use already cached vendor assets.')
    build(offline=parser.parse_args().offline)
