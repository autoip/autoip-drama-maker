# 安裝

中文 | [English](../en/SETUP.md)

Dreamfab 造夢廠的每一條線（短劇 `drama/`、MV `mv/`……）共用同一份安裝：同一個 repo、同一個 Python 環境、同一組 AutoIP 和 YouTube 設定。各條線另外要的東西（字型、模型檔）寫在 [短劇的安裝補充](drama/SETUP.md) 和 [MV 的安裝補充](mv/SETUP.md)。

## 0. 一行安裝（Claude Code / Codex）

**macOS / Linux / Git Bash：**

```bash
curl -fsSL https://raw.githubusercontent.com/autoip/dreamfab/main/install.sh | bash
```

**Windows PowerShell：**

```powershell
irm https://raw.githubusercontent.com/autoip/dreamfab/main/install.ps1 | iex
```

安裝程式會做這些事：
1. 把 repo 下載到 `~/.dreamfab`（已存在就更新）。
2. 建立 `~/.dreamfab/.venv`，安裝 Python 套件。
3. 有選 MV 線的話，下載 MediaPipe 臉部模型。
4. 把 skill 裝到 Claude Code（`~/.claude/skills/`）和 Codex（`~/.codex/skills/`）。同名的舊 skill 會先備份成 `<名稱>.bak`。

ffmpeg、字型、API key 不會自動安裝，請照下面第 1、4 節和各條線的安裝補充處理。

可用環境變數調整：

| 變數 | 預設 | 說明 |
|---|---|---|
| `DREAMFAB_HOME` | `~/.dreamfab` | 安裝位置 |
| `DREAMFAB_LINES` | `drama,mv,explain` | 要裝哪幾條線的 Python 套件。MV 線要 PyTorch（人聲分離）、MediaPipe、OpenCV，比較大；解說線加裝 OpenCV 和 pypinyin；只做短劇就設 `drama` |
| `DREAMFAB_AGENTS` | `claude,codex` | 要裝 skill 的對象；`none` 表示不裝 |
| `DREAMFAB_SKIP_DEPS` | — | 設為 `1` 時跳過 Python 套件 |

例：`curl -fsSL .../install.sh | DREAMFAB_LINES=drama bash`；PowerShell 則先執行 `$env:DREAMFAB_LINES='drama'`。

**改用 plugin 安裝**（只裝 skill；第一次使用時，skill 會自動執行上面的安裝程式來準備工具）：

```bash
claude plugin marketplace add autoip/dreamfab && claude plugin install dreamfab@dreamfab
codex plugin marketplace add autoip/dreamfab && codex plugin add dreamfab@dreamfab
```

**裝好之後**，在 Claude Code 或 Codex 裡直接說一句話：

> 用 dreamfab-drama 把 劇本.md 做成短劇
>
> 用 dreamfab-mv 把 song.mp3 做成 MV

agent 會照那條線的 WORKFLOW.md 進行。每一批任務送出前，都會先給你看審核圖、報點數。

以下是手動安裝的說明。

## 1. 系統工具

- **Python 3.10+**（實測 3.13）
- **ffmpeg / ffprobe**：需要內建 libass 的版本，`ffmpeg -filters | grep subtitles` 要有結果。短劇還會用到 `sidechaincompress`、`loudnorm`、`silencedetect`、`scdet`、`zoompan`，一般的完整版都有。
  - Windows：`winget install Gyan.FFmpeg`
  - macOS：`brew install ffmpeg`
  - Linux：用發行版的套件即可。
- **curl**：`dreamfab/aip_runner.py` 用它上傳 multipart。
- **git**：一行安裝需要。

## 2. Python 套件

```bash
python -m venv .venv
.venv/Scripts/activate            # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt       # 共用核心＋短劇
pip install -r requirements-mv.txt    # 再加 MV 線（含上一行）
```

只有 CPU 的機器做 MV，可以先裝 CPU 版 PyTorch：`pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu`。

## 3. 選用：NVIDIA 顯卡

沒有顯卡也能從頭跑到尾。先看這台機器的顯卡能接手哪些步驟：

```bash
python dreamfab/gpu_check.py
```

| 步驟 | 怎麼開 | 實測（RTX 5060 Ti 16 GB 對 16 執行緒 CPU） |
|---|---|---|
| 影片編碼（各條線的合成、`mv/matte_video.py`） | 自動：ffmpeg 能用 NVENC 就用；`VENC=x264` 強制用 CPU | 成品每 60 秒編碼 6.6 秒對 26.2 秒，VMAF 99.2 對 99.3；短劇一集合成 31 → 16 秒 |
| 語音辨識（`drama/speech.py`、`mv/audio/asr_words.py`） | 短劇：CTranslate2 偵測到 CUDA 就自動用；MV：`ASR_DEVICE=cuda`。都要先裝 cuBLAS 12、cuDNN 9（下面） | 60 秒人聲 1.0 秒對 10.9 秒；短劇 15 顆片段 48 → 10 秒 |
| 人聲分離 Demucs（MV） | 裝 CUDA 版 PyTorch，demucs 自己會用顯卡 | 3 分鐘的歌 21 秒對 32 秒（含載入模型） |
| 超分 2 倍＋補幀 60 fps | 選用，見 [GPU_ENHANCE.md](GPU_ENHANCE.md) | 一顆 5 秒片段約 7.5 秒 |
| 臉、人像分割、對嘴 QC（MediaPipe） | — | Windows 的 pip 版沒有 GPU，只跑 CPU |

faster-whisper（CTranslate2）在 Windows 需要 cuBLAS 12 和 cuDNN 9 的 DLL，用 pip 裝最省事：

```bash
pip install nvidia-cublas-cu12 "nvidia-cudnn-cu12>=9,<10"
```

CUDA 版 PyTorch：驅動的 CUDA 是 13 以上用 `cu130`，舊一點用 `cu128`（`gpu_check.py` 會印出完整指令）：

```bash
pip install torch --index-url https://download.pytorch.org/whl/cu130
```

- NVENC：ffmpeg 9 需要 610 版以上的驅動。GTX 10 系列的驅動停在 580 系列，開不了，`gpu_check.py` 會說。
- 顯卡載入失敗時會自動改用 CPU；每支程式都會印出用的是 GPU 還是 CPU。

## 4. AutoIP API key

- 在 AutoIP 儀表板申請 API key（需入門版以上訂閱）。
- 只放在環境變數 `AUTOIP_API_KEY`，**不要寫進專案檔或提交到 git**。
- 若要改 API 位址，設定 `AUTOIP_BASE_URL`。

```bash
export AUTOIP_API_KEY=aip_xxx           # PowerShell: $env:AUTOIP_API_KEY = "aip_xxx"
```

一般帳號同時只能跑 1 個任務，所以 `dreamfab/aip_runner.py` 預設 `AIP_MAX=1`。白天一律一次一個，即使 `/me` 的 `max_concurrent_tasks` 是 `null`（沒有上限）也一樣。上限較高的帳號只在離峰時段調大：加 `AIP_MAX_UNTIL=09:00 AIP_MAX_AFTER=1`，到那個時間 runner 自己改回 1（已經在跑的任務照常跑完）。

**離峰半價**：用 API 金鑰送出的生成任務，每天 03:00–09:00（台灣時間，假日也算）送出的一律半價（小數無條件進位，最少 1 點），以「送出」的時間為準（`GET /api/v1/pricing` 的 `off_peak` 有時段和 `active_now`）。runner 加 `--off-peak`（或設 `AIP_OFF_PEAK=1`、`AIP_OFFPEAK=1`）就只在這段時間送：

```bash
python dreamfab/aip_runner.py P/jobs/video_jobs.json --off-peak
python dreamfab/workflow.py set credits.off_peak on    # 想每次都這樣：寫進工作流程開關，之後不加參數也只在離峰送（--now 例外）
```

- 晚上先開著（電腦不能睡眠），它會等到 03:00 才開始送，09:00 前 2 分鐘停止送新任務（`AIP_OFF_PEAK_MARGIN=120` 秒，怕本機時鐘比伺服器慢）。
- 已經在跑的任務照常輪詢、下載；沒送完的留到隔天凌晨再送，runner 開著就會自己接著送。
- 送出時有打折的任務，log 會標 `(off-peak)`，`.state` 也記下實際扣的點數，資源庫照實際值算。
- 各條線的 `make_jobs.py`、`storyboard.py` 會同時印出原價和離峰價的估算；不在離峰又沒加 `--off-peak` 時，runner 會印一行提示。
- 帳號同時任務數上限較高的話，可以一起調大：`AIP_MAX=N ... --off-peak`。09:00 之後本來就不送新任務，不用再加 `AIP_MAX_UNTIL`。

## 5. YouTube 上傳（選用）

兩條線的上傳程式（`drama/youtube_upload.py`、`mv/youtube_upload.py`）和播放清單工具（`dreamfab/youtube_playlists.py`）共用同一個登入：

- 在 Google Cloud Console 建一個「電腦版應用程式」類型的 OAuth client，下載 JSON 放到 `~/.config/dreamfab/youtube_client_secret.json`（或用環境變數 `YT_CLIENT_SECRET` 指定位置）。合併前放在 `~/.config/autoip-mv-maker/` 的也讀得到。
- 第一次執行會開瀏覽器登入，登入結果存成同一個資料夾的 `youtube_token.json`。兩個檔都留在 repo 外面。
- 一個 Google 帳號有好幾個頻道時，登入時要選對；設 `YT_CHANNEL_ID` 或上架計畫的 `channel`，程式只會對那個頻道動作。
- 詳細流程見 [短劇的上架](drama/PUBLISHING.md) 和 [MV 的上架](mv/PUBLISHING.md)。

## 6. 素材的權利

- **角色圖**：用你有權使用的照片或美術，或由 AutoIP 生成。不要用真實公眾人物的臉。
- **聲音樣本**：自己的聲音、取得同意的演員、授權允許的合成語音。不要拿別人的聲音去複製。
- **歌曲、配樂、音效**：自己做的、AutoIP 生成的，或有授權的素材庫。
- **字型**：用允許再散布的授權（例如 SIL OFL），而且不要提交進 repo。

## 7. 從舊版更新

再跑一次〈0. 一行安裝〉那一行就是更新（`~/.dreamfab` 已經在就 `git pull`）；自己 clone 的，在 repo 裡 `git pull`。

### 舊的資料庫會自己併進來

舊版把資料分在好幾個 SQLite 檔，現在全部放在一個共用資料庫 `~/.config/dreamfab/dreamfab.db`（`dreamfab/db.py`）。更新後不用做任何事，舊檔第一次被用到時就會併進來：

| 舊檔 | 裡面是什麼 | 什麼時候、怎麼併 |
|---|---|---|
| `~/.config/dreamfab/youtube_log.db`（或以前 `YT_LOG_DB` 指的檔） | 上架紀錄：上傳、公開、置頂、片尾、資訊卡……每一步 | 任何程式第一次打開共用資料庫時（開資源庫、上傳、`youtube_log.py`）。一筆一筆搬進 `youtube_log` 表，已經有的不重複加 |
| 每個系列資料夾裡的 `library.db` | 短劇、MV 資源庫的索引，和影片長度的快取 | 那個系列的資源庫下一次索引時（`library.py serve` 一打開就會）。先拿走長度快取，再照資料夾裡的檔案重建索引 |

- 併完的舊檔改名成 `.merged`（已經有就 `.merged2`），不刪也不覆蓋。終端機會印一行，說併了什麼、從哪個檔。
- 索引本來就是從系列資料夾的檔案算出來的，所以舊的 `library.db` 只取影片長度快取，省掉重新量幾千支影片的時間。上架紀錄沒辦法重算，所以整份搬過來。
- 好幾支程式同時開著也沒關係：每個舊檔先改名再讀，只有一支程式拿得到，不會併兩次。

### 四種做法，挑一種

1. **什麼都不用做（建議）**：更新完照平常用，打開資源庫、上傳影片時就併好了。
2. **現在一次併完**：`python dreamfab/db.py merge` 會找 `projects/` 底下所有的 `library.db`。系列放在別的地方，就把資料夾都列出來：`python dreamfab/db.py merge projects D:/我的影片`。
3. **上架紀錄放在別的地方**：以前設過 `YT_LOG_DB` 的，環境變數還在就會自動併；已經拿掉的話，直接給檔名：`python dreamfab/db.py merge D:/backup/youtube_log.db`。
4. **共用資料庫想放別處**（例如另一顆硬碟）：先設環境變數 `DREAMFAB_DB=<檔案路徑>` 再用，舊檔會併進那一個。

### 檢查

`python dreamfab/db.py show` 列出每張表、每個系列各有幾筆；`youtube_log` 的筆數應該跟舊檔一樣多。資源庫首頁的「出貨紀錄」也看得到以前的上架紀錄。

### 回到舊版

把 `.merged` 改回原來的檔名，再 `git checkout` 回舊版就能照舊用。更新之後才記的上架紀錄只在 `dreamfab.db` 的 `youtube_log` 表，任何 SQLite 工具都能匯出。

### 注意

- `dreamfab.db` 跟著這台電腦，不要放進 Dropbox、OneDrive、Google 雲端硬碟這類同步資料夾：同步程式和 Dreamfab 同時改寫 SQLite 檔會把它弄壞。系列資料夾可以同步，每台電腦各自索引。
- 要備份就把 `dreamfab.db` 連同旁邊的 `dreamfab.db-wal`、`dreamfab.db-shm` 一起複製，或先關掉資源庫和上傳程式再複製。
- 讀不出來的舊檔（壞掉、不是資料庫）會印一行說明，程式照常跑，索引照樣重建。
