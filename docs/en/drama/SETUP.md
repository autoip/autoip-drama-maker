# Setup notes: short drama

[中文](../../zh-TW/drama/SETUP.md) | English

Installing, the Python environment, the GPU, the AutoIP API key and off-peak pricing, and the YouTube login are in the shared [SETUP.md](../SETUP.md). This page has only what the drama line needs on top.

## 1. Python packages

- `requirements.txt` is enough (for short dramas only, set `DREAMFAB_LINES=drama` in the one-line install).
- `faster-whisper` is for `drama/speech.py`: word timings of the lines, and whether a line was said in full. It downloads the `medium` model to the user cache on first run. Without it, `speech.py` falls back to silence detection and only finds where a line starts and ends.
- **Optional: `mediapipe`** (0.10+): `drama/restage.py` uses it to cut the person out of a cast sheet and lay it over a set; the person-segmentation model is downloaded to `~/.cache/dreamfab/` on first run. The MV line installs it anyway.
- **Optional: local super resolution + frame generation** (`drama/enhance.py`): see [GPU_ENHANCE.md](../GPU_ENHANCE.md); usage in section 7 of [WORKFLOW.md](WORKFLOW.md).

## 2. Fonts

Fonts are not distributed with the project: download them and put them in the episode's or the series' `fonts/` (a render looks in the episode first, then one level up).

| Use | Suggested | Licence |
|---|---|---|
| Lines, character cards, title cards | Noto Sans TC, Black or Bold weight | SIL OFL |

**libass only uses a variable font's default weight.** For a heavy weight, cut a static instance first and give it a new family name:

```bash
python dreamfab/make_static_font.py NotoSansTC-VF.ttf 900 "DK Sans Black" projects/<series>/fonts/DKSansBlack.ttf
```

Then set `TYPO = dict(font="DK Sans Black", ...)` in `project.py`. Covers (`drama/thumbkit.py`) use the same font file.
