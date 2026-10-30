# Setup notes: MV

[中文](../../zh-TW/mv/SETUP.md) | English

Installing, the Python environment, the GPU, the AutoIP API key and off-peak pricing, and the YouTube login are in the shared [SETUP.md](../SETUP.md). This page has only what the MV line needs on top.

## 1. Python packages

- Install `requirements-mv.txt` (the one-line install does when `DREAMFAB_LINES` includes `mv`).
- Vocal separation uses Demucs, which needs PyTorch. On a CPU-only machine the CPU build is enough: `pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu`. A 2-minute song takes a few minutes to separate on the CPU.
- To run speech recognition (`mv/audio/asr_words.py`) on the GPU, set `ASR_DEVICE=cuda`; the DLLs it needs are in section 3 of the shared [SETUP.md](../SETUP.md).

## 2. Model files

**MediaPipe face model**: used by `mv/faces.py` and `mv/qc/mouth.py`. The one-line install downloads it; by hand:

```bash
curl -L -o models/face_landmarker.task \
  https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task
```

`FACE_MODEL=/path/to/face_landmarker.task` points to another place. Blurring the background of lip-sync stills (`mv/bokeh_still.py`) also needs the person-segmentation model: see [models/README.md](../../../models/README.md).

**Demucs (htdemucs), faster-whisper (medium)**: downloaded to the user cache on first run.

## 3. Fonts

Fonts are not distributed with the project: download them and put them in each project's `fonts/`.

| Use | Suggested | Licence |
|---|---|---|
| Chinese titles / lyrics | Noto Serif TC, Black weight | SIL OFL |
| Latin text (ACT, name tags, readings) | Noto Serif (Regular / Bold / Italic) | SIL OFL |

**libass only uses a variable font's default weight.** For a heavy serif, cut a static instance first and give it a new family name:

```bash
python dreamfab/make_static_font.py NotoSerifTC-VF.ttf 900 "PS Serif Black" projects/my_song/fonts/PSSerifBlack.ttf
```

Then set `TYPO = dict(font="PS Serif Black", font_file="fonts/PSSerifBlack.ttf", ...)` in `project.py`.

- `font_scale` is libass's size factor; about 1.45 for Noto Serif TC.
- After changing fonts, check the sizes with `mv/qc/subprev.py`.
