# Licenses and source provenance

## Chess project

The chess project preserves LICENSE.txt, bundled library license/metadata, and data/provenance.json. The take-home builder includes those same notices in every standalone ZIP. Application source and bundled python-chess use GPL-3.0-or-later. Preserve `panda-chess-club/LICENSE.txt` and `panda-chess-club/lib/chess-1.11.2.dist-info/licenses/LICENSE.txt` when redistributing. The bundled rules library includes its original package metadata.

The 4,000-position teacher sample is derived from the Lichess evaluation database, released under CC0-1.0. Source, sampling method, SHA-256, split limitations, and seed 314 are recorded in `panda-chess-club/data/provenance.json`.

The instructor demo also bundles the unmodified official Stockfish 18 Windows x86-64 release ZIP at `panda-chess-club/external/stockfish-windows-x86-64.zip`. The archive includes its GPLv3 license, AUTHORS, corresponding source and build instructions. Release: https://github.com/official-stockfish/Stockfish/releases/tag/sf_18 . Archive SHA-256: `40cc975817e7eee270b03f354810d20956df565420d320f6dd37d454dc81a139`. This is an intentional exception to excluding generated ZIPs/binaries; extracted executables remain ignored.

## Chess browser edition

`panda-chess-web` builds from the maintained chess source and preserves the same GPL notices and CC0 teacher-data provenance. Pyodide 0.27.7 and its NumPy package are loaded from the upstream runtime CDN; their upstream license notices remain with that distribution. The build downloads Stockfish.js 17.1.0 Lite single-thread WebAssembly from the npm distribution, verifies hashes in `panda-chess-web/vendor-lock.json`, and publishes its GPLv3 license and exact corresponding source archive (commit `602fd7e1a571a2be71f242942db90483731f2a1f`) beside the binary in the generated site's `vendor/` folder. Generated site files and models are excluded from Git. See the web project's README for build and redistribution instructions.

The instructor bundle also includes the official Stockfish 18 macOS releases, gzip-compressed without modifying the original TAR contents:

| Platform | Bundled file SHA-256 | Official uncompressed TAR SHA-256 |
| --- | --- | --- |
| Apple Silicon | `e52a9f915875a564ddc636e200232fb3b129693c4987ff64be1404dc62dd2ab1` | `4d77c4aa3ad9bd1ea8111f2ac5a4620fe7ebf998d6893bf828d49ccd579c8cb0` |
| Intel x86-64 | `8275b1b9f4053cad2d343da80297c7f974e9c346583b65efe88665786214d782` | `e7d7a2bca13915419d41ac6cb8cedb123dd2ba1c39a22c574df7a2aa3f526592` |

Download provenance: `https://github.com/official-stockfish/Stockfish/releases/download/sf_18/stockfish-macos-m1-apple-silicon.tar` and `https://github.com/official-stockfish/Stockfish/releases/download/sf_18/stockfish-macos-x86-64.tar`. Both include the corresponding source, GPLv3 license, authors and build instructions. The demo verifies the compressed SHA-256 before extracting only the known executable member. These three official release bundles are the user-requested exception to the repository's general binary/archive exclusion; take-home packages still exclude them.
