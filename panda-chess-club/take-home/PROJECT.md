# My Chess Engine

A personal chess engine studio: design a custom evaluation recipe, save reproducible engine versions, inspect their decisions, and compare their game results. Includes baseline bots, a trainable neural evaluator and search analysis.

## Run

Requires Python 3.10+ and NumPy. No GPU or API key is required.

```sh
python -m pip install -r requirements.txt
python main.py
```

Open http://127.0.0.1:4340/. Keep the terminal running; Ctrl+C stops the server.
Use `python3` if that is your Python command. A virtual environment is recommended.
On Windows, `Start Panda Chess.cmd` uses `.venv` if present, otherwise the Python launcher or `python`.
Use `python main.py --port 4341` if the default port is occupied.
Python and NumPy are prerequisites rather than bundled executables. After installation the app works locally offline.

## Make your own engine

The app opens in **My engine**, with a collapsible seven-milestone project guide and a copyable AI mentoring prompt. The prompt includes your saved project identity and recipe context; review it before sharing with an AI assistant. Copying it does not transmit any data automatically. Set your project name, author and description. In the engine designer, name a bot, write your hypothesis, and tune five evaluation weights: material, center control, attacked squares, king pawn shelter and pawn weaknesses. These are manual evaluation choices, not neural training.

**Inspect this draft** evaluates a selected position using the current sliders and shows each contribution. The suggested move uses depth-2 search with a 1,000-node budget; its score comes from future boards, whereas the contribution table describes the displayed board.

**Save a new engine version** freezes the recipe under a new `custom-0001` ID. Play against it or select it in Arena. **Use as draft** copies a saved recipe to the editor; it never changes the saved version. Change one idea, save another version, then compare them under the same search limits.

The three-position experiment records your bot's and Positional Scout's choices with completed search depths. It illustrates behavior, not a calibrated strength benchmark. Arena provides W/D/L and unfinished-game evidence. Long capped games remain unfinished.

**Export my project report** downloads a Markdown record of your project identity, frozen recipes, hypotheses, position experiments and actual Arena results. Add screenshots, your source changes and interpretation in your own repository. Credit this starter and the bundled libraries; a renamed app alone is not an original engineering contribution.

Your project identity, recipes and experiments are saved locally in `project_data/project.json`. Back up this directory with your models and games. It is excluded from source ZIPs and Git by default; intentionally include selected non-private experiment evidence in your own portfolio repository.

## Features

- Random, material and positional opponents.
- Minimax with optional alpha-beta pruning, move ordering and iterative deepening.
- Search budgets, actual node/cutoff counters and inspectable candidate continuations.
- A 782-input, 32-hidden-unit neural evaluator trained on public engine labels.
- Training/validation curves and immutable model checkpoints.
- Paired arena games with color exchange, PGN exports and champion promotion criteria.
- Human-versus-engine play and saved games.

Train a model in **Train** to make it available as an opponent. Training settings control data count, learning rate and epochs. Each action saves a new version. **Arena** compares fixed versions with the same search settings; it does not train them automatically.

Saved model choices are sorted by validation MSE and mark the lowest error; this measures agreement with teacher scores, not playing strength. Selecting a version displays validation MSE/MAE, example count, epochs and learning rate. Use **Delete selected model** to remove unwanted versions from the lists. Deleted files remain in `models/.trash/` and can be restored under **Deleted models**. The current champion and models in an unfinished arena match are protected; model IDs are never reused.

## Architecture

| Component | Responsibility |
| --- | --- |
| `engine/` | Rules adapter, handcrafted evaluators, search and opponent selection; `personal.py` defines editable recipes and position experiments |
| `training/` | Board encoding, neural model, gradient descent and checkpoint storage |
| `arena/` | Match scheduling, result persistence and paired game comparisons |
| `ui/` | Play, analysis, training, arena and saved-game interface |
| `data/` | 4,000 teacher-labeled positions and checksum/provenance |
| `lib/` | Bundled python-chess library |
| `tests/` | Rules, search, gradients, model persistence, arena, HTTP and packaging checks |

Runtime files are stored in `project_data/`, `models/`, `arena_results/` and `games/`. They are excluded from Git and source ZIPs by default. Back up these folders separately to retain experiments.

## Development

```sh
python -m unittest discover -s tests -v
```

Tests create temporary files under `.build/` and a loopback HTTP server. JavaScript changes can also be checked with `node --check ui/app.js`; Node is not required to run the app.
Use seed 314 for reproducible experiments. Evaluator changes belong in `engine/evaluation.py`, model changes in `training/model.py`, and search changes in `engine/search.py`. A changed model shape may require new checkpoints and matching UI descriptions.

Build a clean source archive with `python package_project.py`. The generated ZIP contains the standalone application and its tests, not local runtime state.

## Evaluation and limitations

Targets are engine evaluations transformed by `tanh(centipawns / 400)`. Neural output is not a calibrated win probability. Lower validation error does not establish stronger play. Related positions can cross dataset splits, and the small sample is not representative of all chess.

Arena ratings are relative to the selected opponent under the selected settings, not calibrated human Elo. Incomplete/capped matches withhold ratings; boundary all-win/all-loss scores have no finite Elo estimate. Search is deliberately shallow and lacks quiescence, transposition tables, opening books and tablebases. Self-play outcome training and automatic labeling of saved games are not implemented.

## Credits and license

Based on the AI Club Panda Chess project. Application source and bundled python-chess are GPL-3.0-or-later; preserve `LICENSE.txt` and the library's license/metadata when redistributing. Teacher positions derive from the Lichess evaluation database (CC0); see `data/provenance.json` for source, sampling and checksum details. Describe your own modifications and results separately from the upstream project when presenting a derivative.

Saved model details and deleted-model choices show the checkpoint file size. Under **Deleted models**, **Delete permanently** erases only the selected trashed checkpoint after confirmation; it bypasses your system’s trash and cannot be restored through the app. Saved games are kept.

## Final references

The References tab reveals two approaches after a saved neural model and a finished arena trial exist. Reveal is an explicit end-of-session action and resets when the server restarts. Capped trial games are still reported as unfinished; completing a trial does not establish playing strength.

**Prepared Panda** uses the same 782 → 32 → 1 network, all 3,199 training boards, Adam (step size 0.003), seed 314, and validation checkpoint selection. Prepare before starting the server:

```sh
python -m training.prepare_reference
```

The script creates `references/prepared.json`, outside members' model registry. It tries at most 2,000 updates and stops after 200 updates without validation improvement. Test scores are measured once after selection, never used to select weights. The bundled sample is small and not guaranteed game-disjoint; this reference has no claimed human Elo or guaranteed win rate. Preparation is not part of interactive training. Generated reference weights are ignored by Git and intentionally included in the portfolio ZIP when present; a fresh clone can reproduce them with the command above.

**Stockfish** is a separate optional reference engine. Download an official build for your OS/CPU from https://stockfishchess.org/download/ and extract it. Copy just its executable to `external/stockfish` (macOS/Linux) or `external/stockfish.exe` (Windows), preserving executable permission on macOS/Linux. Restart the server. No executable is downloaded or run from a browser-supplied path. This project does not bundle the OS-specific executable in the portable ZIP. If redistributing Stockfish yourself, retain its GPL license and provide the exact corresponding source: https://github.com/official-stockfish/Stockfish .

After reveal, both installed references become playable opponents and arena choices. The comparison uses depth 2 / 3,000 nodes for both Panda models and 0.3 seconds, one thread, 32 MiB hash for Stockfish. These are visibly different compute limits, not an equal-compute strength benchmark. Stockfish is not assigned a made-up teacher-validation MSE. The app displays actual errors for the Panda models on the same validation boards, and actual moves/continuations for all engines.

The ZIP builder uses `package_manifest.json` as an explicit source list. Add new source files there when extending the project; arbitrary files placed under source/data/vendor folders are excluded.

Move inspection supports a separate White hint engine and the selected opponent’s Black reply. **Preview my best move** searches White’s current position; **Preview opponent’s reply** searches after that suggestion without playing it. Continuations have Start, Back, Play/Pause, Forward and End controls, plus clickable move steps. These controls affect only the view-only preview board and never save, play or train moves.
