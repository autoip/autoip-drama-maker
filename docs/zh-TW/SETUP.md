# 安裝

中文 | [English](../en/SETUP.md)

## 0. 一行安裝（Claude Code / Codex）

**macOS / Linux / Git Bash：**

```bash
curl -fsSL https://raw.githubusercontent.com/autoip/autoip-drama-maker/main/install.sh | bash
```

**Windows PowerShell：**

```powershell
irm https://raw.githubusercontent.com/autoip/autoip-drama-maker/main/install.ps1 | iex
```

安裝程式會做這些事：
1. 把 repo 下載到 `~/.autoip-drama-maker`（已存在就更新）。
2. 建立 `~/.autoip-drama-maker/.venv`，安裝 Python 套件。
3. 把 skill 裝到 Claude Code（`~/.claude/skills/`）和 Codex（`~/.codex/skills/`）。同名的舊 skill 會先備份成 `<名稱>.bak`。

ffmpeg、字型、API key 不會自動安裝，請照下面第 1、3、4 節處理。

可用環境變數調整：

| 變數 | 預設 | 說明 |
|---|---|---|
| `AUTOIP_DRAMA_HOME` | `~/.autoip-drama-maker` | 安裝位置 |
| `AUTOIP_DRAMA_AGENTS` | `claude,codex` | 要裝 skill 的對象；`none` 表示不裝 |
| `AUTOIP_DRAMA_SKIP_DEPS` | — | 設為 `1` 時跳過 Python 套件 |

**改用 plugin 安裝**（只裝 skill；第一次使用時，skill 會自動執行上面的安裝程式來準備工具）：

```bash
claude plugin marketplace add autoip/autoip-drama-maker && claude plugin install autoip-drama-maker@autoip-drama-maker
codex plugin marketplace add autoip/autoip-drama-maker && codex plugin add autoip-drama-maker@autoip-drama-maker
```

**裝好之後**，在 Claude Code 或 Codex 裡直接說：

> 用 autoip-drama-maker 把 劇本.md 做成短劇

## 1. 系統工具

- **Python 3.10+**（實測 3.13）
- **ffmpeg / ffprobe**：需要內建 libass 的版本，`ffmpeg -filters | grep subtitles` 要有結果。還會用到 `sidechaincompress`、`loudnorm`、`silencedetect`、`scdet`、`zoompan`，一般的完整版都有。
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

- `faster-whisper` 給 `speech.py` 用：台詞的逐字時間、檢查台詞有沒有講完。第一次執行會下載 `medium` 模型到使用者快取。沒裝的話 `speech.py` 改用靜音偵測，只抓得到台詞的起訖。
- **選用：NVIDIA 顯卡。** 有顯卡就自動用：語音辨識（`speech.py`）在 CTranslate2 偵測得到 CUDA 時跑在顯卡上（Windows 先 `pip install nvidia-cublas-cu12 "nvidia-cudnn-cu12>=9,<10"`；顯卡載入失敗會自動改用 CPU），合成（`render_ep.py`）在 ffmpeg 能用 NVENC 時用顯卡編碼。兩支程式都會印出用的是 GPU 還是 CPU。要強制用 CPU：`ASR_DEVICE=cpu`、`VENC=x264`。RTX 5060 Ti 實測：辨識 15 顆 48 → 10 秒，合成 54 秒的一集 31 → 16 秒（字幕、縮放這些濾鏡仍在 CPU）。
- **選用：本地超分＋補幀（`enhance.py`）。** 需要 RTX 顯卡（補幀要 RTX 40／50 系列）、驅動 570.65 以上、有 CUDA 的 PyTorch、PyAV（`pip install av`），再裝 NVIDIA 的 `pip install nvidia-vfx`（PyPI 上是一個殼，真正的套件從 pypi.nvidia.com 下載，Windows 約 436 MB，自帶需要的 NVIDIA 函式庫）。NVIDIA 專有授權，模型標示可商用。用法見 WORKFLOW.md 第 7 節。

## 3. 字型

字型不隨專案發布，請自行下載後放進這一集或這部劇的 `fonts/`（合成會先找這一集，再找上一層）。

| 用途 | 建議 | 備註 |
|---|---|---|
| 台詞、人物字卡、片名卡 | Noto Sans TC（思源黑體），取 Black 或 Bold 字重 | SIL OFL |

**libass 只會用可變字型的預設字重。** 要粗體，先切出靜態字重，再取一個新的家族名稱：

```bash
python dramakit/make_static_font.py NotoSansTC-VF.ttf 900 "DK Sans Black" projects/<劇名>/fonts/DKSansBlack.ttf
```

接著在 `project.py` 設定 `TYPO = dict(font="DK Sans Black", ...)`。封面（`thumbkit.py`）用同一個字型檔。

## 4. AutoIP API key

- 在 AutoIP 儀表板申請 API key（需入門版以上訂閱）。
- 只放在環境變數 `AUTOIP_API_KEY`，**不要寫進專案檔或提交到 git**。
- 若要改 API 位址，設定 `AUTOIP_BASE_URL`。

```bash
export AUTOIP_API_KEY=aip_xxx           # PowerShell: $env:AUTOIP_API_KEY = "aip_xxx"
```

一般帳號同時只能跑 1 個任務，所以 `aip_runner.py` 預設 `AIP_MAX=1`。白天一律一次一個，即使 `/me` 的 `max_concurrent_tasks` 是 `null`（沒有上限）也一樣。上限較高的帳號只在離峰時段調大：加 `AIP_MAX_UNTIL=09:00 AIP_MAX_AFTER=1`，到那個時間 runner 自己改回 1（已經在跑的任務照常跑完）。

**離峰半價**：用 API 金鑰送出的生成任務，每天 03:00–09:00（台灣時間，假日也算）送出的一律半價，以「送出」的時間為準（`GET /api/v1/pricing` 的 `off_peak` 有時段和 `active_now`）。runner 加 `--off-peak`（或設 `AIP_OFF_PEAK=1`）就只在這段時間送：

```bash
python dramakit/aip_runner.py P/jobs/video_jobs.json --off-peak
```

- 晚上先開著（電腦不能睡眠），它會等到 03:00 才開始送，09:00 前 2 分鐘停止送新任務（`AIP_OFF_PEAK_MARGIN=120` 秒，怕本機時鐘比伺服器慢）。
- 已經在跑的任務照常輪詢、下載；沒送完的留到隔天凌晨再送，runner 開著就會自己接著送。
- 送出時 API 回 `off_peak_discount: true` 的任務，log 會標 `(off-peak)`，`.state` 也記下實際扣的點數，資源庫照實際值算。
- `make_jobs.py`、`storyboard.py` 會同時印出原價和離峰價的估算。
- 帳號同時任務數上限較高的話，可以一起調大：`AIP_MAX=N ... --off-peak`。09:00 之後本來就不送新任務，不用再加 `AIP_MAX_UNTIL`。

## 5. 素材的權利

- **角色圖**：用你有權使用的照片或美術，或由 AutoIP 生成。不要用真實公眾人物的臉。
- **聲音樣本**：自己的聲音、取得同意的演員、授權允許的合成語音。不要拿別人的聲音去複製。
- **配樂、音效**：有授權的素材庫，或自己做的。
