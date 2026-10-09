# Panda Chess Club

A local, expandable chess-engine workshop: **15-minute instructor lecture, then hands-on experiments**. This is the current club demo. The personal project launcher and templates are in `take-home/`.

## Included in this project

- This folder: club demo and lecture.
- [take-home/](take-home/): personal project launcher, README and entry-page templates.

This is the public UConn AI Club project. The participant ZIP excludes lecture material and personal runtime records.

## Start

Requires Python 3.10+ and NumPy. From this folder, run:

```powershell
python -m pip install -r requirements.txt
python main.py
```

On Windows you can instead double-click **Start Panda Chess.cmd** after installing dependencies. Open <http://127.0.0.1:4340/> for the lab and <http://127.0.0.1:4340/lecture> for the lecture. Keep the server terminal open. Ctrl+C stops it. If this port is already occupied, use `python main.py --port 4341` and the printed URL. The app binds only to your own computer.

## Take-home / portfolio project

Open http://127.0.0.1:4340/take-home to download the personal engine studio ZIP. It includes My engine, Play & analyze, Train, Arena and References, a technical README, source, data, tests and licenses. My engine includes its own independent project guide and AI mentoring prompt. Lecture pages and instructor notes are excluded, along with personal models, recipes and game records.

Run `python take-home/run.py` from this folder to open the personal project on port 4342. It creates a complete independent copy under ignored `.build/personal-project/` on first launch and preserves your edits and saved records on later launches. The shared engine is maintained once; `take-home/` holds only the launcher and personal page/README templates.

Regenerate the take-home source and ZIP after changing shared code or those overrides:

```sh
python package_project.py --project-dir .build/personal-project
```

This writes packaged source into the ignored `.build/personal-project/` folder and the ZIP into `.build/Panda-Chess-Portfolio-Project.zip`. It preserves runtime records, but overwrites matching source files: copy participant modifications elsewhere before regenerating. The ZIP can also be shared through your club's usual file channel. The localhost download URL works only on the computer running the app.

## What works now

- Random, material, and positional bots; neural versions become playable after training.
- Minimax, optional alpha-beta pruning and capture/promotion ordering, iterative deepening with a node budget.
- Actual search counters, candidate moves, and inspectable predicted leaf boards.
- A real 782-input, 32-hidden-unit neural evaluator trained on bundled public engine evaluations.
- Training curves, one-board prediction traces, immutable model versions, continuation and loading.
- Model choices sorted by validation error, detailed model metadata, recoverable deletion/restoration, and protected champion/active arena versions. Checkbox multi-selection supports deleting several saved/deleted models or arena histories together, with selected-size totals and confirmation.
- Paired arena games with equal Panda search settings (external Stockfish uses a separate time limit), PGN exports, persistent W/D/L and unfinished counts, and a guarded champion promotion.
- Member-game PGN capture for a later training extension.

## Project structure

| Folder | Responsibility |
| --- | --- |
| `engine/` | Chess rules adapter, handcrafted evaluation, search, bot selection |
| `training/` | Board encoding, neural network, gradient descent, model versions |
| `arena/` | Paired matches, result persistence, relative Elo and promotion gate |
| `ui/` | Short lecture and interactive lab |
| `data/` | 4,000 public teacher-labeled positions and provenance/checksum |
| `lib/` | Bundled python-chess rules library and its license |
| `tests/` | Rules, search, gradients, training separation, arena and HTTP checks |
| `models/`, `arena_results/`, `games/` | Created locally as you use the app |

Run checks with `python -m unittest discover -s tests -v`. Tests use temporary subfolders inside `.build/` and need permission to bind a loopback socket.

## Next milestones, not implemented yet

Live Stockfish teacher labeling; transposition tables and quiescence; books/tablebases; training on club failures; self-play outcome learning; policy/value networks and MCTS. Network-vs-network arena games currently **evaluate** models; they do not automatically train them. This release does not establish a human Elo or prove the model beats an average player.

Teacher source: [Lichess evaluation database](https://database.lichess.org/#evals), CC0; see `data/provenance.json`. Rules: [python-chess documentation](https://python-chess.readthedocs.io/en/latest/). The bundled rules library and project distribution include the GPL license in `LICENSE.txt`.

Saved model details and deleted-model choices show the checkpoint file size. Under **Deleted models**, **Delete permanently** erases only the selected trashed checkpoint after confirmation; it bypasses your system’s trash and cannot be restored through the app. Saved games are kept.

## Final references

The References tab reveals two approaches after a saved neural model and a finished arena trial exist. Reveal is an explicit end-of-session action and resets when the server restarts. Capped trial games are still reported as unfinished; completing a trial does not establish playing strength.

**Prepared Panda** uses the same 782 → 32 → 1 network, all 3,199 training boards, Adam (step size 0.003), seed 314, and validation checkpoint selection. Prepare before starting the server:

```sh
python -m training.prepare_reference
```

The script creates `references/prepared.json`, outside members' model registry. It tries at most 2,000 updates and stops after 200 updates without validation improvement. Test scores are measured once after selection, never used to select weights. The bundled sample is small and not guaranteed game-disjoint; this reference has no claimed human Elo or guaranteed win rate. Preparation is not part of interactive training. Generated reference weights are ignored by Git and intentionally included in the portfolio ZIP when present; a fresh clone can reproduce them with the command above.

**Stockfish 18 is included for Windows x86-64, Apple Silicon Macs and Intel Macs.** Starting the local demo selects the matching archive in `external/`, verifies its checksum, and unpacks its executable automatically. On macOS it also sets executable permissions. No separate Stockfish or neural-network download is needed. An existing executable for your operating system is kept.

The three compressed archives add about 230 MB to the repository download. Each contains the official executable, GPL license, authors, corresponding source and build instructions. The Mac release TAR files are gzip-compressed without changing their contents so every file fits GitHub's individual-file limit. See the root `THIRD_PARTY.md` for provenance. Linux and Windows ARM still require a matching official executable prepared once by the instructor under `external/stockfish` or `external/stockfish.exe`. If macOS blocks the downloaded executable, review it in System Settings > Privacy & Security before allowing it; the app does not bypass macOS security controls.

The portable take-home ZIP excludes these desktop archives and executables. The browser edition uses its own browser-compatible Stockfish and works independently of these local bundles.

After reveal, both installed references become playable opponents and arena choices. The comparison uses depth 2 / 3,000 nodes for both Panda models and 0.3 seconds, one thread, 32 MiB hash for Stockfish. These are visibly different compute limits, not an equal-compute strength benchmark. Stockfish is not assigned a made-up teacher-validation MSE. The app displays actual errors for the Panda models on the same validation boards, and actual moves/continuations for all engines.

The ZIP builder uses `package_manifest.json` as an explicit source list. Add new source files there when extending the project; arbitrary files placed under source/data/library folders are excluded.

Move inspection supports a separate White hint engine and the selected opponent’s Black reply. **Preview my best move** searches White’s current position; **Preview opponent’s reply** searches after that suggestion without playing it. Continuations have Start, Back, Play/Pause, Forward and End controls, plus clickable move steps. These controls affect only the view-only preview board and never save, play or train moves.
