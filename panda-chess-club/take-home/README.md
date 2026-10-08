# Take-home project

This folder keeps the personal project page and portfolio README. It reuses the demo source so the repository contains one engine implementation.

From the parent `panda-chess-club` folder:

```sh
python -m pip install -r requirements.txt
python take-home/run.py
```

Open http://127.0.0.1:4342/. The launcher creates the full, independent project in `.build/personal-project/` on first launch. Edit that generated project for your own variation. Later launches preserve your edits, models and games. Stop it with Ctrl+C.

To get a fresh complete source package, use the demo's take-home download or run `python package_project.py`. The ZIP is `.build/Panda-Chess-Portfolio-Project.zip`; extract it anywhere and follow its README. It contains source, data, tests and licenses, without the lecture or instructor guide.

`PROJECT.md` becomes the downloaded project's README; `ui/index.html` becomes its personal entry page. Shared engine changes belong in the parent source. To refresh your local generated copy, preserve your own source edits first, then run `python package_project.py --project-dir .build/personal-project`. Saved runtime records are not overwritten.
