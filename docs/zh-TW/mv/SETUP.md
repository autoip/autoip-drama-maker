# 安裝

中文 | [English](../en/SETUP.md)

## 0. 一行安裝（Claude Code / Codex）

**macOS / Linux / Git Bash：**

```bash
curl -fsSL https://raw.githubusercontent.com/autoip/autoip-mv-maker/main/install.sh | bash
```

**Windows PowerShell：**

```powershell
irm https://raw.githubusercontent.com/autoip/autoip-mv-maker/main/install.ps1 | iex
```

安裝程式會做這些事：
1. 把 repo 下載到 `~/.autoip-mv-maker`（已存在就更新）。
2. 建立 `~/.autoip-mv-maker/.venv`，安裝 Python 套件。
3. 下載 MediaPipe 臉部模型。
4. 把 skill 裝到 Claude Code（`~/.claude/skills/`）和 Codex（`~/.codex/skills/`）。同名的舊 skill 會先備份成 `<名稱>.bak`。

ffmpeg、字型、API key 不會自動安裝，請照下面第 1、4、5 節處理。

可用環境變數調整：

| 變數 | 預設 | 說明 |
|---|---|---|
| `AUTOIP_MV_HOME` | `~/.autoip-mv-maker` | 安裝位置 |
| `AUTOIP_MV_AGENTS` | `claude,codex` | 要裝 skill 的對象；`none` 表示不裝 |
| `AUTOIP_MV_SKIP_DEPS` | — | 設為 `1` 時跳過 Python 套件（PyTorch 很大） |

例：`curl -fsSL .../install.sh | AUTOIP_MV_AGENTS=codex bash`；PowerShell 則先執行 `$env:AUTOIP_MV_AGENTS='codex'`。

**改用 plugin 安裝**（只裝 skill；第一次使用時，skill 會自動執行上面的安裝程式來準備工具）：

```bash
claude plugin marketplace add autoip/autoip-mv-maker && claude plugin install autoip-mv-maker@autoip-mv-maker
codex plugin marketplace add autoip/autoip-mv-maker && codex plugin add autoip-mv-maker@autoip-mv-maker
```

**裝好之後**，在 Claude Code 或 Codex 裡直接說：

> 用 autoip-mv-maker 把 song.mp3 做成 MV

agent 會照 [WORKFLOW.md](WORKFLOW.md) 的流程進行。每一批影片任務送出前，都會先給你看靜圖、報點數。

以下是手動安裝的說明。

## 1. 系統工具

- **Python 3.10+**（實測 3.13）
- **ffmpeg / ffprobe**：需要內建 libass 的版本，`ffmpeg -filters | grep subtitles` 要有結果。
  - Windows：`winget install Gyan.FFmpeg`
  - macOS：`brew install ffmpeg`
  - Linux：用發行版的套件即可。
- **curl**：`aip_runner.py` 用它上傳 multipart。
- **git**：一行安裝需要。

## 2. Python 套件

```bash
python -m venv venv
venv/Scripts/activate            # macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
```

- 人聲分離用 Demucs，需要 PyTorch。
- 只有 CPU 的機器可以先裝 CPU 版：`pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu`。
- 一首 2 分多鐘的歌，在 CPU 上分離約需數分鐘。

**選用：NVIDIA 顯卡加速。** 預設全部跑 CPU，沒有顯卡也能從頭跑到尾。有顯卡時工具只會印一行提示，不會自己切換。先看這台機器的顯卡能接手哪些步驟：

```bash
python mvkit/gpu_check.py
```

| 步驟 | 怎麼開 | 實測（RTX 5060 Ti 16 GB 對 16 執行緒 CPU） |
|---|---|---|
| 語音辨識 `asr_words.py` | `ASR_DEVICE=cuda`，先裝 cuBLAS 12、cuDNN 9（下面） | 60 秒人聲 1.0 秒對 10.9 秒；換顯卡後第一次跑多約 20 秒編譯 |
| 編碼 `render_mv.py`、`matte_video.py` | `VENC=nvenc`（render 的段落同時編 4 段，`JOBS` 可改） | 成品每 60 秒編碼 6.6 秒對 26.2 秒，VMAF 99.2 對 99.3；190 秒的全片 50 秒算完，CPU 要 2 分 45 秒 |
| 人聲分離 Demucs | 裝 CUDA 版 PyTorch，demucs 自己會用顯卡 | 3 分鐘的歌 21 秒對 32 秒（含載入模型） |
| 臉、人像分割、對嘴 QC（MediaPipe） | — | Windows 的 pip 版沒有 GPU，只跑 CPU |

faster-whisper（ctranslate2）在 Windows 需要 cuBLAS 12 和 cuDNN 9 的 DLL，用 pip 裝最省事，`asr_words.py` 會自己找到它們：

```bash
pip install nvidia-cublas-cu12 "nvidia-cudnn-cu12>=9,<10"
```

CUDA 版 PyTorch：驅動的 CUDA 是 13 以上用 `cu130`，舊一點用 `cu128`（`gpu_check.py` 會印出完整指令）：

```bash
pip install torch --index-url https://download.pytorch.org/whl/cu130
```

- NVENC：ffmpeg 9 需要 610 版以上的驅動。GTX 10 系列的驅動停在 580 系列，開不了，`gpu_check.py` 會說。
- 解碼：新顯卡解碼比 CPU 快（60 秒 1080p：1.1 秒對 1.8 秒），但只佔算圖時間的一小部分，所以沒有開。
- 舊顯卡參考：GTX 1060 的語音辨識約快 2.3 倍，NVENC 開不了，解碼比 CPU 慢。

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

一般帳號同時只能跑 1 個任務，所以 `aip_runner.py` 預設 `AIP_MAX=1`。上限較高的帳號可以調大；只在離峰時段調大的話，加 `AIP_MAX_UNTIL=09:00 AIP_MAX_AFTER=1`，到那個時間 runner 自己改回 1（已經在跑的任務照常跑完）。

從 2026-10-30 起，用 API 金鑰在離峰時段（每天 03:00–09:00 台灣時間，以送出的時間為準）送出的生成任務一律半價（小數無條件進位，最少 1 點）。不急的批次加 `AIP_OFFPEAK=1`：runner 只在這個時段送新任務，時段外照常輪詢、下載已經在跑的任務，然後等下一個時段（結束前 2 分鐘就不再送）。時段和是否啟用以 `GET /api/v1/pricing` 的 `off_peak` 為準；送出時有打折的任務會標 `(off-peak)`，實際扣的點數記在 `.state`。沒設 `AIP_OFFPEAK` 又不在時段內時，runner 只印一行提示。
