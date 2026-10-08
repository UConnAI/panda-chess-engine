# Panda Chess · browser edition

The same club lecture and hands-on lab, running entirely in each student's browser. No Python installation, login or training server. Open the published link, train and play, then download a complete personal Python project with saved work or a clean starter.

The maintained engine/UI live in the sibling `panda-chess-club/` project. This folder contains only the web adapter and build tools, so shared code is maintained once. The generated site is self-contained and can be copied to a public club repository without publishing the private instructor guide.

## Preview locally

From this folder, with Python 3.10+:

```sh
python -m pip install -r ../panda-chess-club/requirements.txt
python build.py
python -m http.server 4343 --bind 127.0.0.1 --directory .build/site
```

Open http://127.0.0.1:4343/. A static file server is all that runs locally; Python training executes inside the browser via Pyodide. First build prepares the reference model and downloads pinned Stockfish browser assets and corresponding source. Later builds reuse them; `python build.py --offline` uses the existing cache. The first browser visit also needs access to `cdn.jsdelivr.net` for pinned Pyodide 0.27.7 and NumPy.

## GitHub Pages

The `Panda Chess Web` Actions workflow builds and deploys on pushes to `main` and manual dispatch. GitHub Pages uses **GitHub Actions**. Live site: https://uconnai.github.io/panda-chess-engine/.

For your public club repository, build here and copy **the contents of `.build/site/`** into the club repository's Pages publishing folder. Keep `.nojekyll`. Enable Pages for that folder. All page and asset links support a repository subpath, such as `https://club.github.io/projects/chess/`. No desktop folder is required at runtime. Alternatively copy both source folders and the workflow into the club repository to rebuild there.

The build includes lecture pages, the shared engine, public teacher data, reproducibly prepared reference weights, and standalone take-home source. It excludes INSTRUCTOR.md, local participant records, desktop Stockfish binaries and caches. Stockfish Lite WebAssembly and its exact corresponding source/license are supplied separately under `vendor/`; the engine loads only when used after final reveal.

## What works

- Random, material, positional and neural bots; both-side hints, legal moves, castling, search continuation and telemetry.
- Real NumPy training in a background Web Worker, validation curves, model save/load/delete/restore and held-out testing.
- Paired arena games, replay, continuation, history deletion and PGN export.
- Prepared Panda and single-thread Stockfish 17.1 Lite reference, including play, comparisons and arena games. This browser release differs from the Stockfish 18 architecture illustration in the lecture.
- Persistent per-browser model/game/project storage in IndexedDB, with one active app tab to avoid competing writes.
- **Download my project + saved work** includes saved models, custom bots, project identity, experiments, arena records, PGNs and a report. **Clean starter** excludes student records. Both exports contain the full independent Python project and licenses, without lecture or instructor notes.

## Practical limits

First loading time and search/training speed depend on network and device. Training runs are bounded by the existing lab controls; arena Pause takes effect after the current move. Closing/reloading during a computation abandons that action; each successful request is persisted before the app reports success. Use one workshop tab at a time. Browser storage is specific to the site, browser and device. Clearing site data or private browsing can erase it. Export before leaving or clearing storage; export failure is shown explicitly.

No server collects participant work. Python runtime/NumPy are fetched from their CDN, and normal static asset requests reach the site's host. Browser Stockfish is loaded from the same site. The student ZIP needs Python and NumPy when run locally; it does not include a desktop Stockfish executable. Install that separately using its README.

## Verification

Run `python -m unittest discover -s tests -v` here after building. The browser smoke test also exercises the actual worker, training, save/reload, both downloads and Stockfish under a simulated repository subpath. See `tests/browser-smoke.cjs` for its Playwright dependency and command. Automated/browser checks establish functionality, not human playing strength or a guaranteed startup time.

The web adapter uses the same GPL-3.0-or-later license as the chess project; see [LICENSE.txt](../panda-chess-club/LICENSE.txt). All generated distributions retain the required notices.
