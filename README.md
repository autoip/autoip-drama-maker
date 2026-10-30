# Dreamfab 造夢廠

**AI 自動化媒體工作站：一句話，你就是導演和製作人，完成你心中夢想的影視作品。**

中文 | [English](README.en.md)

Dreamfab 用 [AutoIP](https://autoip.ai) 公開 API 生成畫面、聲音和對嘴，剪輯、字幕、混音、合成全部在本機用 ffmpeg + libass 完成。每一種媒體是一條產線，共用同一個核心：送任務、算點數、離峰半價、本機 GPU 超分補幀、資源庫、YouTube 上架。

## 產線：戲・曲・說・影・聞

| 線 | 跟 agent 說一句話 | 狀態 | 文件 |
|---|---|---|---|
| **戲**：短劇 `drama/` | 用 dreamfab-drama 把 劇本.md 做成短劇 | 可用 | [短劇總覽](docs/zh-TW/drama/OVERVIEW.md) |
| **曲**：MV `mv/` | 用 dreamfab-mv 把 song.mp3 做成 MV | 可用 | [MV 總覽](docs/zh-TW/mv/OVERVIEW.md) |
| **說**：解說影片 | 靜態或動態 B-roll，主打低點數、高流量 | 規劃中 | — |
| **影**、**聞**：電影、新聞 | — | 之後 | — |

**每一批任務送出前，agent 都會先給你看審核圖、報點數**，你點頭才會送出。

## 示範作品

**短劇《我的室友是楊貴妃》**：用短劇線做的穿越短劇。楊貴妃從馬嵬坡掉進負債三百萬的經紀人家裡，篇章一 10 集已全部上架，每集約 50 秒。 <!-- public-ok -->

- ▶ 第 1 集：https://youtu.be/kA4J9kLOVVo <!-- public-ok -->
- ▶ 全集播放清單：https://www.youtube.com/playlist?list=PLFDknh7mplug
- 🎵 同一個角色的 MV《馬嵬》：https://youtu.be/C6aGMU8mKdw（MV 線做的；短劇和 MV 的說明欄互相連結） <!-- public-ok -->

**MV**：同一條 MV 線，四種曲風與畫面風格。點縮圖到 YouTube 觀看。

| **暗黑金屬史詩** | **王家衛風港式抒情** | **國風古風對唱** | **賽博龐克女聲 Rap** |
|:---:|:---:|:---:|:---:|
| [![《黑日聖殿》](https://img.youtube.com/vi/ErQCd04OGA8/mqdefault.jpg)](https://youtu.be/ErQCd04OGA8) | [![《過期的那一分鐘》](https://img.youtube.com/vi/fMTLkI7qDq8/mqdefault.jpg)](https://youtu.be/fMTLkI7qDq8) | [![《洛川》](https://img.youtube.com/vi/OlIQYvfwZhA/mqdefault.jpg)](https://youtu.be/OlIQYvfwZhA) | [![《科技睪丸》](https://img.youtube.com/vi/fZ9SlclC9ng/mqdefault.jpg)](https://youtu.be/fZ9SlclC9ng) |

一整季的 MV 系列：[《國風淒美對唱》播放清單](https://www.youtube.com/playlist?list=PLfoBI7oPycHg)，6 集，同一套畫面和包裝，每集換一種曲風。

## 一行安裝（Claude Code / Codex）

**macOS / Linux / Git Bash：**

```bash
curl -fsSL https://raw.githubusercontent.com/autoip/dreamfab/main/install.sh | bash
```

**Windows PowerShell：**

```powershell
irm https://raw.githubusercontent.com/autoip/dreamfab/main/install.ps1 | iex
```

工具裝到 `~/.dreamfab`（含 Python 虛擬環境），skill 同時裝進 Claude Code 和 Codex。只做短劇的話設 `DREAMFAB_LINES=drama`，省掉 MV 線比較大的套件。也可以改用 plugin 安裝：

```bash
claude plugin marketplace add autoip/dreamfab && claude plugin install dreamfab@dreamfab
codex plugin marketplace add autoip/dreamfab && codex plugin add dreamfab@dreamfab
```

ffmpeg（要有 libass）、字型、`AUTOIP_API_KEY` 要自己準備，見 [SETUP.md](docs/zh-TW/SETUP.md)。

## 虛擬劇團與平行時空

- **平行時空**：每個系列是一個世界，放在 `projects/<系列>/`，一集或一首歌一個資料夾、一個 `project.py`。
- **虛擬劇團**：`projects/<系列>/cast/`、`voices/` 是這個世界的演員和聲音，跨集、跨季重複演出，臉和聲音都不會跑掉。
- **資源庫**：一個網頁看所有世界的每一集、每顆鏡頭、每個角色、點數和上架狀態：

```bash
python dreamfab/library.py serve projects     # http://127.0.0.1:8765
```

## 共用核心 `dreamfab/`

| 檔案 | 做什麼 |
|---|---|
| `aip_runner.py` | 送 AutoIP 任務、輪詢、下載；可續跑、一次一個、`--off-peak` 只在離峰半價時段送 |
| `util.py` | 讀專案、ffmpeg、NVIDIA 編碼器（有就自動用）、點數估算 |
| `enhance.py` | 本機 NVIDIA 超分 2 倍＋補幀 60 fps 的引擎（各條線的 `enhance.py` 呼叫它）：[GPU_ENHANCE.md](docs/zh-TW/GPU_ENHANCE.md) |
| `library.py` | 所有系列的資源庫網頁 |
| `youtube_api.py`、`youtube_playlists.py` | YouTube 登入（頻道鎖定）、播放清單整理 |
| `credits.py` | 對帳：每個任務資料夾實際花了多少點數 |
| `check_public.py` | 送出前的去識別化檢查：金鑰、個資、你作品的詞 |
| `gpu_check.py`、`make_static_font.py` | 這台機器的顯卡能接手什麼；給 libass 用的靜態字重 |

## 文件

| 文件 | 內容 |
|---|---|
| [SETUP.md](docs/zh-TW/SETUP.md) | 安裝、顯卡、API key、離峰半價、YouTube 登入、素材權利 |
| [短劇總覽](docs/zh-TW/drama/OVERVIEW.md) | 短劇線：流程、格式、剪輯、上架、踩坑紀錄 |
| [MV 總覽](docs/zh-TW/mv/OVERVIEW.md) | MV 線：流程、格式、情緒卡點、上架、踩坑紀錄 |
| [GPU_ENHANCE.md](docs/zh-TW/GPU_ENHANCE.md) | 本機超分＋補幀：工具、實測速度與效果 |
| [CONTRIBUTING.md](CONTRIBUTING.md) | 貢獻原始碼：什麼可以進 repo、去識別化、送出前的檢查 |

## 從 autoip-drama-maker／autoip-mv-maker 搬過來

Dreamfab 由這兩個 repo 合併而成，歷史都保留。舊的 GitHub 網址會自動轉到這裡。

| 以前 | 現在 |
|---|---|
| `dramakit/<x>.py` | `drama/<x>.py` |
| `mvkit/<x>.py` | `mv/<x>.py` |
| `dramakit/aip_runner.py`、`mvkit/aip_runner.py`，還有 `credits.py`、`check_public.py`、`gpu_check.py`、`make_static_font.py`、`youtube_playlists.py` | `dreamfab/<x>.py` |
| `~/.autoip-drama-maker`、`~/.autoip-mv-maker` | `~/.dreamfab` |
| `AUTOIP_DRAMA_*`、`AUTOIP_MV_*` | `DREAMFAB_*` |
| skill `autoip-drama-maker`、`autoip-mv-maker` | `dreamfab-drama`、`dreamfab-mv` |
| `~/.config/autoip-mv-maker/`（YouTube 憑證） | `~/.config/dreamfab/`（舊位置照樣讀得到） |

`project.py` 的格式沒有改，舊專案直接能用。

## 授權

[MIT](LICENSE)。用 Dreamfab 做的作品歸你；請只用你有權使用的素材（見 [SETUP.md](docs/zh-TW/SETUP.md) 最後一節）。
