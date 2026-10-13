# 安裝

## 1. 系統工具

- **Python 3.10+**（實測 3.13）
- **ffmpeg / ffprobe**：需要內建 libass 的版本，`ffmpeg -filters | grep subtitles` 要有結果。
  - Windows：`winget install Gyan.FFmpeg`
  - macOS：`brew install ffmpeg`
  - Linux：用發行版的套件即可。
- **curl**：`aip_runner.py` 用它上傳 multipart。

## 2. Python 套件

```bash
python -m venv venv
venv/Scripts/activate            # macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
```

- 人聲分離用 Demucs，需要 PyTorch。
- 只有 CPU 的機器可以先裝 CPU 版：`pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu`。
- 一首 2 分多鐘的歌，在 CPU 上分離約需數分鐘。

## 3. 模型檔

**MediaPipe 臉部模型**：`faces.py`、`qc/mouth.py` 會用到。

```bash
curl -L -o models/face_landmarker.task \
  https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task
```

也可以用環境變數 `FACE_MODEL=/path/to/face_landmarker.task` 指定位置。

**Demucs（htdemucs）、faster-whisper（medium）**：第一次執行時會自動下載到使用者快取。

## 4. 字型

字型不隨專案發布，請自行下載後放進每個專案的 `fonts/`。

| 用途 | 建議 | 備註 |
|---|---|---|
| 中文標題/歌詞 | Noto Serif TC（思源宋體），取 Black 字重 | SIL OFL |
| 拉丁字（ACT、名牌、標音） | Noto Serif（Regular / Bold / Italic） | SIL OFL |

**libass 只會用可變字型的預設字重。** 想要粗體宋體，要先切出靜態字重，再取一個新的家族名稱：

```bash
python mvkit/make_static_font.py NotoSerifTC-VF.ttf 900 "PS Serif Black" projects/my_song/fonts/PSSerifBlack.ttf
```

接著在 `project.py` 設定 `TYPO = dict(font="PS Serif Black", font_file="fonts/PSSerifBlack.ttf", ...)`。

- `font_scale` 是 libass 字級換算係數，Noto Serif TC 約 1.45。
- 換字型後用 `qc/subprev.py` 看一下大小是否合適。

## 5. AutoIP API key

- 在 AutoIP 儀表板申請 API key（需入門版以上訂閱）。
- 只放在環境變數 `AUTOIP_API_KEY`，**不要寫進專案檔或提交到 git**。
- 若要改 API 位址，設定 `AUTOIP_BASE_URL`。

```bash
export AUTOIP_API_KEY=aip_xxx           # PowerShell: $env:AUTOIP_API_KEY = "aip_xxx"
```

一般帳號同時只能跑 1 個任務，所以 `aip_runner.py` 預設 `AIP_MAX=1`。上限較高的帳號可以調大。
