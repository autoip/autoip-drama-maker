# Dreamfab 造夢廠

**AI Agent 影音製作框架：一句話，你就是導演和製作人，AI Agent 幫你把心中夢想的影視作品做出來。**

中文 | [English](README.en.md)

Dreamfab 是讓 AI Agent（Claude Code、Codex）自動做影片的框架。你跟 agent 說一句話，它就照產線的 skill 寫劇本、送生成任務、看審核圖、剪輯、上字幕、混音、上架。每一批要花點數的任務都先報價，你點頭才送。

框架分三層：

- **產線**：一種影片一條產線（短劇、MV、解說……），各有自己的流程、格式和 skill。新的影片類型，就是一條新產線。
- **生成引擎**：畫面、影片、聲音、對嘴交給外部引擎生成。目前接 [AutoIP](https://autoip.ai) 公開 API：文生圖（v4＝MOSS-Image）、圖生影片、多參考影片、對嘴、語音克隆、AI 作曲。之後會接更多生圖、生影片引擎，每條產線依需要挑。
- **共用核心** `dreamfab/`：送任務、算點數、離峰半價、本機 GPU 超分補幀、本機剪輯合成（ffmpeg + libass）、資源庫網頁、YouTube 上架。每條產線、每個引擎都用同一套。

## 產線：戲・曲・說・影・聞

| 線 | 跟 agent 說一句話 | 狀態 | 文件 |
|---|---|---|---|
| **戲**：短劇 `drama/` | 用 dreamfab-drama 把 劇本.md 做成短劇 | 可用 | [短劇總覽](docs/zh-TW/drama/OVERVIEW.md) |
| **曲**：MV `mv/` | 用 dreamfab-mv 把 song.mp3 做成 MV | 可用 | [MV 總覽](docs/zh-TW/mv/OVERVIEW.md) |
| **說**：解說影片 `explain/` | 用 dreamfab-explain 把 MV《洛川》背後的歷史做成 5 分鐘解說 | 可用（靜態 B-roll；動態規劃中） | [解說總覽](docs/zh-TW/explain/OVERVIEW.md) |
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

工具裝到 `~/.dreamfab`（含 Python 虛擬環境），skill 同時裝進 Claude Code 和 Codex。預設裝三條線（`DREAMFAB_LINES=drama,mv,explain`）；只做短劇就設 `DREAMFAB_LINES=drama`，省掉 MV 線比較大的套件。也可以改用 plugin 安裝：

```bash
claude plugin marketplace add autoip/dreamfab && claude plugin install dreamfab@dreamfab
codex plugin marketplace add autoip/dreamfab && codex plugin add dreamfab@dreamfab
```

ffmpeg（要有 libass）、字型、`AUTOIP_API_KEY` 要自己準備，見 [SETUP.md](docs/zh-TW/SETUP.md)。

## 更新

照你當初怎麼裝的，選一種：

| 當初怎麼裝 | 怎麼更新 |
|---|---|
| 一行安裝 | 再跑一次同一行。`~/.dreamfab` 已經在就 `git pull`，Python 套件和 skill 一起更新（當初設過 `DREAMFAB_LINES` 的，這次也設一樣的） |
| plugin | 先更新 skill：`claude plugin marketplace update dreamfab && claude plugin update dreamfab@dreamfab`（重開 Claude Code 生效）；Codex 是 `codex plugin marketplace upgrade dreamfab && codex plugin add dreamfab@dreamfab`。工具裝在 `~/.dreamfab`，再跑一次一行安裝 |
| 自己 clone | 在 repo 裡 `git pull`，再 `pip install -r requirements.txt`（MV、解說線各自的 `requirements-mv.txt`、`requirements-explain.txt` 也一樣） |

更新不會動到你的作品：系列資料夾在 `projects/`、設定和登入在 `~/.config/dreamfab/`，都不在 git 裡。

### 舊版的資料庫：什麼都不用做

舊版把資料分在好幾個 SQLite 檔：每個系列一個 `library.db`，加上上架紀錄 `~/.config/dreamfab/youtube_log.db`。現在全部放在一個共用資料庫 `~/.config/dreamfab/dreamfab.db`，舊檔第一次被用到時會自己併進來：

- **上架紀錄**：任何程式第一次打開共用資料庫時（開資源庫、上傳）一筆一筆搬過來，已經有的不重複加。
- **系列的 `library.db`**：那個系列的資源庫下一次索引時（`library.py serve` 一打開就會），先拿走影片長度快取，再照資料夾裡的檔案重建索引。
- 併完的舊檔改名成 `.merged` 留著，不刪也不覆蓋；終端機會印一行說併了什麼。好幾支程式同時開也只會併一次。

要自己動手的情況：

| 情況 | 怎麼做 |
|---|---|
| 想現在一次併完 | `python dreamfab/db.py merge`（找 `projects/` 底下全部的 `library.db`）；系列放在別處就列出資料夾：`python dreamfab/db.py merge projects D:/我的影片` |
| 上架紀錄以前用 `YT_LOG_DB` 放在別處 | 環境變數還在就會自動併；拿掉了就給檔名：`python dreamfab/db.py merge D:/backup/youtube_log.db` |
| 共用資料庫想放別的硬碟 | 先設 `DREAMFAB_DB=<檔案路徑>` 再用 |
| 確認有沒有併好 | `python dreamfab/db.py show` 列出每張表、每個系列幾筆，`youtube_log` 應該跟舊檔一樣多 |
| 想回到舊版 | 把 `.merged` 改回原來的檔名，再 `git checkout` 回舊版 |

`dreamfab.db` 不要放進 Dropbox、OneDrive 這類同步資料夾，同步程式和 Dreamfab 同時寫入會把它弄壞。細節見 [SETUP.md〈從舊版更新〉](docs/zh-TW/SETUP.md#7-從舊版更新)。

## 虛擬劇團與平行時空

- **平行時空**：每個系列是一個世界，放在 `projects/<系列>/`，一集或一首歌一個資料夾、一個 `project.py`。
- **虛擬劇團**：`projects/<系列>/cast/`、`voices/` 是這個世界的演員和聲音，跨集、跨季重複演出，臉和聲音都不會跑掉。
- **資源庫**：一個本機網頁看所有世界的每一集、每顆鏡頭、每個角色、點數和上架狀態，見下一節。

## 本機資源庫網頁

做久了，素材會散在幾十個資料夾：每一集的 `project.py`、鏡頭、配音、任務紀錄、成片、封面、上架紀錄。資源庫把 `projects/` 底下的所有系列整理成一個本機網頁，在瀏覽器裡看、播、搜，不用翻資料夾。

```bash
python dreamfab/library.py serve projects     # 開 http://127.0.0.1:8765
python dreamfab/library.py list projects      # 只列出找到哪些系列、各屬哪條線
```

**首頁是造夢廠的廠區圖。** 最上面一排是流程：一句話 → AI Agent → 產線 ⇄ 生成引擎 → 倉庫 → YouTube，每一格都帶著數字（在製幾件、成品幾件、已上架幾件）。

**產線**：戲・曲・說各一條輸送帶，站名照那條線的流程（短劇：劇本 → 分鏡 → 生成 → 剪輯 → 封面；解說：文案 → 旁白 → 畫面 → 剪輯 → 封面）。還在做的那一集停在它還沒過的那一站，點下去就是那一集；有工作的產線滾輪會轉、貨箱會滑進「入庫」。影・電影、聞・新聞是規劃中的產線。

![首頁：上面是流程，下面是戲・曲・說三條產線，每一集停在它目前的站](docs/images/library_home_lines.jpg)

**倉庫**：一個系列一座貨架、一季一層，每一集用封面擺上架，角落標 ▶ 已上架或待上架；還在產線上的那一集留一個虛線空位，寫著停在哪一站。點貨架名稱進入那個系列的資源庫。還不是系列的資料夾放在「散件區」。

![倉庫：短劇系列一季一層，▶ 已上架、待上架](docs/images/library_home_store_drama.jpg)

![倉庫：MV 和解說系列，虛線空位是還在產線上的那一集](docs/images/library_home_store_mv.jpg)

- **短劇系列**：每一集的封面、長度、鏡數、點數、YouTube 狀態；單集頁有正片、每顆鏡頭的台詞和辨識吻合度、片段縮圖；角色、場景、任務點數都查得到。見[短劇總覽〈資源庫網頁〉](docs/zh-TW/drama/OVERVIEW.md#資源庫網頁)。
- **MV 系列**：每一集的成片、靜圖、影片片段（含舊版與候選）、角色、歌詞、剪輯表、點數、上架紀錄。見[MV 總覽〈資源庫網頁〉](docs/zh-TW/mv/OVERVIEW.md#資源庫網頁)。
- **解說系列**：每集一張卡片，標出「文案 → 旁白 → 畫面 → 剪輯 → 封面 → 上傳」做到哪一步。單集頁有成片和章節（點一下跳到那一段）、封面 A/B/C、每張畫面和它的說明、旁白、文案全文、YouTube 標題與說明欄；系列頁下方是共用的旁白聲音和每支 MV 的伴奏。
- **其他資料夾**：`/files/<路徑>` 直接打開，資料夾就是一頁，音訊、影片、圖片都有播放器，Markdown 直接顯示。解說頁加 `?raw` 回到原始檔案清單。
- 影片、音訊都能拖拉跳轉，直接在瀏覽器裡審片、聽旁白。
- 只聽 `127.0.0.1`，不對外開放。短劇和 MV 的索引存在共用資料庫 `~/.config/dreamfab/dreamfab.db`（在 repo 外面），開著的時候會自己重新索引；解說頁每次打開都直接讀資料夾，新檔案馬上看得到。
- 網址可以直接貼進對話：agent 剪好一集，就回一個資源庫網址讓你點開審片；你也可以把某一集、某顆鏡頭的網址貼給 agent，說哪裡要改。

## 共用核心 `dreamfab/`

| 檔案 | 做什麼 |
|---|---|
| `aip_runner.py` | 送 AutoIP 任務、輪詢、下載；可續跑、一次一個、`--off-peak` 只在離峰半價時段送 |
| `util.py` | 讀專案、ffmpeg、NVIDIA 編碼器（有就自動用）、點數估算 |
| `enhance.py` | 本機 NVIDIA 超分 2 倍＋補幀 60 fps 的引擎（各條線的 `enhance.py` 呼叫它）：[GPU_ENHANCE.md](docs/zh-TW/GPU_ENHANCE.md) |
| `library.py` | 所有系列的本機資源庫網頁（見〈本機資源庫網頁〉） |
| `youtube_api.py`、`youtube_playlists.py` | YouTube 登入（頻道鎖定）、播放清單整理 |
| `db.py` | 共用資料庫：所有產線、所有系列的資源庫索引和上架紀錄都在同一個 SQLite 檔 `~/.config/dreamfab/dreamfab.db`（`show` 看內容；舊版每個系列一個的 `library.db` 和 `youtube_log.db` 會自己併進來，`merge` 一次併完） |
| `youtube_log.py` | 上架紀錄（共用資料庫的 `youtube_log` 表）：上傳、更新、公開、留言、置頂、片尾、資訊卡、說明欄連結，每一件都記時間（上傳程式自動記，Studio 手動做的用 `add` 補記）；資源庫首頁的「出貨紀錄」和解說單集頁讀它 |
| `workflow.py` | 工作流程開關：離峰才送、同時幾個任務、解說直版、GPU 超分、上傳狀態、上架紀錄，各自開或關；你自己一份、系列可以另外設（[WORKFLOW.md](docs/zh-TW/WORKFLOW.md)） |
| `credits.py` | 對帳：每個任務資料夾實際花了多少點數 |
| `check_public.py` | 送出前的去識別化檢查：金鑰、個資、你作品的詞 |
| `gpu_check.py`、`make_static_font.py` | 這台機器的顯卡能接手什麼；給 libass 用的靜態字重 |

## 文件

| 文件 | 內容 |
|---|---|
| [SETUP.md](docs/zh-TW/SETUP.md) | 安裝、顯卡、API key、離峰半價、YouTube 登入、素材權利、從舊版更新 |
| [短劇總覽](docs/zh-TW/drama/OVERVIEW.md) | 短劇線：流程、格式、剪輯、上架、踩坑紀錄 |
| [MV 總覽](docs/zh-TW/mv/OVERVIEW.md) | MV 線：流程、格式、情緒卡點、上架、踩坑紀錄 |
| [GPU_ENHANCE.md](docs/zh-TW/GPU_ENHANCE.md) | 本機超分＋補幀：工具、實測速度與效果 |
| [WORKFLOW.md](docs/zh-TW/WORKFLOW.md) | 工作流程開關：哪些步驟自動做，你自己決定 |
| [CONTRIBUTING.md](CONTRIBUTING.md) | 貢獻原始碼：什麼可以進 repo、去識別化、送出前的檢查 |

## 未來方向

- **更多生成引擎**：生圖、生影片、語音接上其他雲端 API 和本機模型，同一條產線可以換引擎、比畫質和價錢。
- **更多影片產線**：電影（影）、新聞（聞），以及更多格式；共用核心不用重寫，新產線只要寫自己的流程和 skill。
- **更完整的 agent 自動化**：從一句話到上架，agent 自己審片、自己修；人只在花錢和公開之前點頭。

## 授權

[MIT](LICENSE)。用 Dreamfab 做的作品歸你；請只用你有權使用的素材（見 [SETUP.md〈素材的權利〉](docs/zh-TW/SETUP.md#6-素材的權利)）。
