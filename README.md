# Panda Chess Engine · UConn AI Club

**[Open the live chess lab](https://uconnai.github.io/panda-chess-engine/)** · [Concepts / lecture](https://uconnai.github.io/panda-chess-engine/lecture.html) · [Take-home project](https://uconnai.github.io/panda-chess-engine/take-home.html)

Build an opponent, train a small neural evaluator, inspect its search, and test it in the Arena. The website runs on your device with no installation or API key. Export your personal project and saved work from the take-home page.

## Two versions, one engine

- **[panda-chess-web/](panda-chess-web/)**: browser version deployed to GitHub Pages. Python/NumPy run in a browser worker; models and games stay in browser storage.
- **[panda-chess-club/](panda-chess-club/)**: local Python demo, shared engine/interface, and take-home project templates. Official Stockfish bundles cover Windows x86-64 and Apple Silicon/Intel Macs.

## Run locally

Requires Python 3.10+:

```sh
cd panda-chess-club
python -m pip install -r requirements.txt
python -m training.prepare_reference
python main.py
```

Open the printed localhost URL. For the independent portfolio project, run `python take-home/run.py` or use the website's take-home download.

## Develop and publish

Maintain shared engine/interface code in `panda-chess-club`; browser adapters and the static builder live in `panda-chess-web`. See each folder's README for checks and build instructions. The **Panda Chess Web** GitHub Actions workflow builds and deploys the website when changes reach `main`, and can also be started manually.

The website does not deliver the desktop Stockfish archives. Downloading the entire repository includes about 230 MB of official desktop engine bundles. Take-home downloads exclude those bundles and teaching pages. Export your saved browser work before clearing browser data.

## License and provenance

GPL-3.0-or-later; see [LICENSE.txt](LICENSE.txt) and [THIRD_PARTY.md](THIRD_PARTY.md). Public evaluation sample: Lichess, CC0, with recorded sampling provenance. Engine bundles preserve their matching source and notices. No instructor-only guide or participant records are published in this repository.
