# 安裝補充：MV

中文 | [English](../../en/mv/SETUP.md)

安裝、Python 環境、顯卡、AutoIP API key 和離峰半價、YouTube 登入都見共用的 [SETUP.md](../SETUP.md)。這裡只寫 MV 線另外要的東西。

## 1. Python 套件

- 裝 `requirements-mv.txt`（一行安裝的 `DREAMFAB_LINES` 包含 `mv` 就會裝）。
- 人聲分離用 Demucs，需要 PyTorch。只有 CPU 的機器可以先裝 CPU 版：`pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu`。一首 2 分多鐘的歌，在 CPU 上分離約需數分鐘。
- 語音辨識（`mv/audio/asr_words.py`）要用顯卡時設 `ASR_DEVICE=cuda`，DLL 的裝法見共用 [SETUP.md](../SETUP.md) 第 3 節。

## 2. 模型檔

**MediaPipe 臉部模型**：`mv/faces.py`、`mv/qc/mouth.py` 會用到。一行安裝會自動下載；手動下載：

```bash
curl -L -o models/face_landmarker.task \
  https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task
```

也可以用環境變數 `FACE_MODEL=/path/to/face_landmarker.task` 指定位置。對嘴靜圖的背景模糊（`mv/bokeh_still.py`）另外要人像分割模型，見 [models/README.md](../../../models/README.md)。

**Demucs（htdemucs）、faster-whisper（medium）**：第一次執行時會自動下載到使用者快取。

## 3. 字型

字型不隨專案發布，請自行下載後放進每個專案的 `fonts/`。

| 用途 | 建議 | 備註 |
|---|---|---|
| 中文標題／歌詞 | Noto Serif TC（思源宋體），取 Black 字重 | SIL OFL |
| 拉丁字（ACT、名牌、標音） | Noto Serif（Regular / Bold / Italic） | SIL OFL |

**libass 只會用可變字型的預設字重。** 想要粗體宋體，要先切出靜態字重，再取一個新的家族名稱：

```bash
python dreamfab/make_static_font.py NotoSerifTC-VF.ttf 900 "PS Serif Black" projects/my_song/fonts/PSSerifBlack.ttf
```

接著在 `project.py` 設定 `TYPO = dict(font="PS Serif Black", font_file="fonts/PSSerifBlack.ttf", ...)`。

- `font_scale` 是 libass 字級換算係數，Noto Serif TC 約 1.45。
- 換字型後用 `mv/qc/subprev.py` 看一下大小是否合適。
