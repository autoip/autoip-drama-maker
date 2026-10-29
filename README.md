# autoip-mv-maker：AI 音樂 MV 製作管線

中文 | [English](README.en.md)

把一首歌做成完整 MV 的半自動流程。可以輸出完整版、1 分鐘短版和直式 Shorts：

- 對嘴主唱、固定陣容的樂團、劇情 B-roll
- 依情緒卡點的剪輯
- 動態字幕（kinetic typography），含韻腳標音與關鍵字特效
- 推廣卡、縮圖、上架文案

影像生成使用 [AutoIP](https://autoip.ai) 公開 API：文生圖、圖生圖、圖生影片、對嘴、多參考影片。剪輯、字幕與合成全部在本機用 ffmpeg + libass 完成。

## 一句話做出 MV

裝好之後（安裝方式見下方），在 Claude Code 或 Codex 裡說：

```text
用 autoip-mv-maker 把 song.mp3 做成 MV
```

agent 會照流程一步一步做。**每一批影片任務送出前，都會先給你看靜圖、報點數**，你點頭才會送出。

要做一整個系列：

```text
用 autoip-mv-maker 規劃一個 6 集的 MV 系列：<題材>
```

agent 會先問你題材、主軸和想固定的錨點，寫好整季企劃和系列風格聖經給你確認，再一集一集做。框架有公式，題材和風格全部由你決定。方法見 [SERIES_PLANNING.md](docs/zh-TW/SERIES_PLANNING.md)，做完的一整季見[系列範例](https://www.youtube.com/playlist?list=PLfoBI7oPycHg)。

## 範例影片

同一套流程，四種曲風與畫面風格。點縮圖到 YouTube 觀看。

| **暗黑金屬史詩** | **王家衛風港式抒情** | **國風古風對唱** | **賽博龐克女聲 Rap** |
|:---:|:---:|:---:|:---:|
| [![《黑日聖殿》](https://img.youtube.com/vi/ErQCd04OGA8/mqdefault.jpg)](https://youtu.be/ErQCd04OGA8) | [![《過期的那一分鐘》](https://img.youtube.com/vi/fMTLkI7qDq8/mqdefault.jpg)](https://youtu.be/fMTLkI7qDq8) | [![《洛川》](https://img.youtube.com/vi/OlIQYvfwZhA/mqdefault.jpg)](https://youtu.be/OlIQYvfwZhA) | [![《科技睪丸》](https://img.youtube.com/vi/fZ9SlclC9ng/mqdefault.jpg)](https://youtu.be/fZ9SlclC9ng) |
| 《暗影之島，烈焰之島》<br>男精靈死腔怒吼 × 女精靈空靈吟唱；颱風、古廟、赤潮、黑日 | 《過期的那一分鐘》<br>抽格殘影、霓虹綠與琥珀光、雨夜，時間與錯過 | 《洛川》<br>曹植 × 洛神；青綠山水、金箔礦彩、巨月與水龍、畫卷轉場 | 《科技睪丸》<br>霓虹賽博姐妹團駭進父權系統；動態字幕跟著節奏炸 |

**一整季的系列範例**：[《國風淒美對唱》播放清單](https://www.youtube.com/playlist?list=PLfoBI7oPycHg)，6 集，同一套畫面和包裝，每集換一種曲風。

## 一行安裝（Claude Code / Codex）

**macOS / Linux / Git Bash：**

```bash
curl -fsSL https://raw.githubusercontent.com/autoip/autoip-mv-maker/main/install.sh | bash
```

**Windows PowerShell：**

```powershell
irm https://raw.githubusercontent.com/autoip/autoip-mv-maker/main/install.ps1 | iex
```

安裝程式會把工具裝到 `~/.autoip-mv-maker`，內容包括 Python 虛擬環境和臉部模型。skill 會同時裝進 Claude Code 和 Codex。

也可以改用 plugin 安裝：

```bash
claude plugin marketplace add autoip/autoip-mv-maker && claude plugin install autoip-mv-maker@autoip-mv-maker
codex plugin marketplace add autoip/autoip-mv-maker && codex plugin add autoip-mv-maker@autoip-mv-maker
```

還需要自己準備三樣東西：
- **ffmpeg**（含 libass）
- **字型**
- **AutoIP API key**：放在環境變數 `AUTOIP_API_KEY`，不要寫進任何檔案。

詳見 [docs/zh-TW/SETUP.md](docs/zh-TW/SETUP.md)。

## 特色

- **一個 `project.py` 就是一支 MV**：陣容、分鏡、對嘴段落、歌詞時間、剪輯表、字幕主題、特效關鍵字都寫在這裡，其餘檔案都由它產生。
- **先看圖再花點數**：每個影片任務都先產生靜態關鍵影格，做成審核圖給人確認後才送出。
- **雙主唱分軌對嘴**：人聲分離後再依段落切成兩軌（例如嘶吼與女高音），每個主唱的嘴只在自己的句子動。
- **群像不再變矮變小孩**：先拼貼、再圖生圖產出定稿靜圖，然後才做圖生影片（`group_still.py`）。
- **情緒卡點**：能量地圖、呼吸點、驟降點引導剪輯表，切點自動吸附到節拍。
- **史詩劇場字幕引擎**（`epic.py`）：
  - 不同聲部有不同進場（滑入或砸入加震動），舊句燒成灰。
  - 分幕標題、樂手名牌、片名卡。
  - 韻腳下方顯示羅馬拼音。
  - 關鍵字特效：金幣、眼淚、碰杯、CLAP、轉輪、爆炸、逃竄、飄走。
- **品管工具**：對嘴對位、嘴巴是否在動（MediaPipe jawOpen）、審核圖、只渲字幕的快速預覽、點數稽核。
- **資源庫網頁**：整個系列的每一集、每一段素材（靜圖、影片、舊版與候選）、角色、歌詞、剪輯表、成片、任務點數、YouTube 上架紀錄索引進一個 SQLite 檔，本機開網頁就能瀏覽、播放、搜尋（見下方〈資源庫網頁〉）。

## 手動使用

```bash
git clone https://github.com/autoip/autoip-mv-maker && cd autoip-mv-maker
python -m venv venv && venv/Scripts/activate        # macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
export AUTOIP_API_KEY=aip_xxx                       # 在 AutoIP 儀表板申請；不要寫進任何檔案
cp -r examples/demo projects/my_song                # projects/ 已被 .gitignore 排除
# 放入 song.mp3、chars/*.png、fonts/，編輯 projects/my_song/project.py
```

接著照 [docs/zh-TW/WORKFLOW.md](docs/zh-TW/WORKFLOW.md) 一步一步做。從歌曲分析到上架共 10 個步驟，每一步都附指令和審核點。

## 資源庫網頁

做成一個系列之後，素材會散在每一集的 `project.py`、`kf/`、`clips/`、`jobs/`、`out/`、`thumbnails/`。資源庫把它們全部索引進一個 SQLite 檔，再開一個本機網頁瀏覽：

```bash
python mvkit/library.py serve projects/my_series      # 重建索引，開 http://127.0.0.1:8770
python mvkit/library.py index projects/my_series      # 只重建 projects/my_series/library.db
python mvkit/library.py serve projects/my_series --no-index --port 8800   # 沿用現有索引、換 port
```

| 頁面 | 看得到什麼 |
|---|---|
| 總覽 | 依季分區，每一集的封面、曲風、完整版／短版／Shorts 長度、素材數、對嘴佔比、估計點數、YouTube 連結；全系列的片段數、完整版總長、點數、容量 |
| 單集 | 完整版、短版、Shorts 和歌曲；歌詞、狀態、SEO、`project.py` 連結；角色與參考圖；每一段素材的說明、對到的歌詞、靜圖（關鍵幀影片是首尾幀）、影片、用在哪個版本幾次、舊版數；歌詞時間；每個版本的剪輯表（重複用的素材標紅）；縮圖與審核圖 |
| 素材 | 一段素材的影片、靜圖或多參考的每張參考圖、提示詞、在剪輯表的哪幾列、產生它的任務、所有舊版與候選 |
| 角色 | 每一集 `CHARS` 的定裝圖與 `REFS` 的參考圖、描述 |
| 檔案 | 依類別（片段、舊版、候選、關鍵影格、角色、縮圖、成片、字幕、審核圖、任務檔……）列出大小、長度、尺寸、修改時間 |
| 任務與點數 | 每一集送了哪些 AutoIP 任務、狀態、估計點數（其中影片多少）、提示詞 |
| YouTube | 每一集各版本的標題、上傳時間、影片與 Studio 連結；做完但沒有上傳紀錄的集數 |
| 搜尋 | 歌詞、素材說明與提示詞、角色、標題、曲風、檔名 |

- 只用 Python 標準函式庫和 ffprobe／ffmpeg，不用另外裝套件。
- 系列資料夾下有 `project.py`、或命名為 `s<季>e<集>_<歌名>` 的子資料夾都算一集（還沒有 `project.py` 的顯示「企劃中」）；`_` 開頭的資料夾不算。直接指向單一專案資料夾也可以。
- 封面用 `thumbnails/thumb_*.jpg` 裡最新的一張，沒有就用完整版的畫面。
- `serve` 開著的時候每 15 秒檢查一次系列資料夾，有檔案新增或修改就在背景重建索引，重新整理網頁就看得到；不用手動重跑。
- 影片長度和縮圖快取在 `library.db` 與 `.library/`，重建一次只要幾秒（第一次要掃過全部影片）。兩者都在 `.gitignore` 裡。
- 只聽 `127.0.0.1`，也只送出系列資料夾裡的檔案；OAuth 憑證和 token 不索引也不送出。影片支援拖拉進度（Range）。port 被占用時自動換下一個。
- 點數用 `.state` 記下的實際扣點（離峰半價也算對），舊的 `.state` 沒有記才照任務檔估算（`common.estimate`）：失敗會退點，不算；同一個任務重送只算最後一次；沒有 `.state` 但輸出還在的算一次。要對帳用 `credits.py`。
- `library.db` 也可以直接用任何 SQLite 工具查（`episodes`、`shots`、`versions`、`lyrics`、`edit_rows`、`chars`、`files`、`jobs`、`youtube`）。

## 文件

| 文件 | 內容 |
|---|---|
| [SETUP.md](docs/zh-TW/SETUP.md) | 安裝：一行安裝、Python 套件、ffmpeg、模型檔、字型 |
| [WORKFLOW.md](docs/zh-TW/WORKFLOW.md) | 完整流程：音訊 → 分鏡 → 生成 → 品管 → 剪輯 → 字幕 → 合成 → 縮圖 → 上架 → 資源庫 |
| [PROJECT_FORMAT.md](docs/zh-TW/PROJECT_FORMAT.md) | `project.py` 每個欄位的說明 |
| [LESSONS.md](docs/zh-TW/LESSONS.md) | 踩過的坑與解法（生成模型的怪癖、libass、ASR、成本） |
| [RELEASE_NOTES.md](docs/zh-TW/RELEASE_NOTES.md) | 更新紀錄 |
| [EMOTIONAL_BEAT_EDITING.md](docs/zh-TW/EMOTIONAL_BEAT_EDITING.md) | 情緒卡點剪輯心法 |
| [PUBLISHING.md](docs/zh-TW/PUBLISHING.md) | 縮圖、YouTube SEO、自動上傳 YouTube、社群貼文範本 |
| [SERIES_PLANNING.md](docs/zh-TW/SERIES_PLANNING.md) | 系列企劃框架：一句話、主軸、固定錨點、歌曲結構、包裝、目錄命名、每集流程 |
| [CONTRIBUTING.md](docs/zh-TW/CONTRIBUTING.md) | 貢獻程式碼與文件：規範、送 PR、回報問題，以及送出前的去識別化檢查 |
| [GPU_ENHANCE.md](docs/zh-TW/GPU_ENHANCE.md) | 本地 NVIDIA 顯卡超分 2 倍＋補幀 60 fps：工具、實測速度與效果、autoip-drama-maker 的做法、搬到 MV 要注意的 |

英文版在 [docs/en/](docs/en/)。

## Skills

| skill | 用途 |
|---|---|
| `autoip-mv-maker` | 主流程：找到工具、檢查環境，帶 agent 走完 10 個步驟並遵守審核點 |
| `emotional-beat-editing` | 情緒卡點：規劃剪輯表時套用 |

兩個 skill 都放在 `skills/`，Claude Code 和 Codex 都能用。一行安裝或 plugin 安裝都會一起裝好。

## 目錄

```
mvkit/
  common.py            專案載入、EDL 解析、ffmpeg 小工具
  storyboard.py        project.py -> storyboard.json + shots.json
  faces.py             角色臉部框 (MediaPipe)
  make_jobs.py         產生 AutoIP 任務檔（關鍵影格 / 影片）
  feature_jobs.py      多參考影片、關鍵幀影片、圖生影片的任務檔（展示多種功能的 MV）
  group_still.py       群像：拼貼 -> 圖生圖候選
  bokeh_still.py       對嘴靜圖背景虛化（人物不動、不留白邊）；BG= 換成另一張畫風底圖
  matte_video.py       對嘴片段逐格去背，貼回靜止的畫風底圖；KEEP= 保住頭上的長裝飾
  aip_runner.py        送出、輪詢、下載（可續跑、預設一次一個；AIP_OFFPEAK=1 只在離峰半價時段送）
  credits.py           每個任務資料夾花了多少點數
  render_mv.py         EDL -> 分段 -> 字幕 -> 推廣卡 -> 成品 mp4 + srt
  enhance.py           （選用）本機 NVIDIA 超分 2 倍＋補幀 60 fps -> clips_hd/，剪輯寫 render=dict(fps=60, enhance=True) 才用
  epic.py              史詩劇場動態字幕引擎 (ASS)
  thumbkit.py          YouTube 縮圖工具
  youtube_upload.py    照 YouTube_SEO.txt 上傳成片、縮圖、字幕（YouTube Data API，預設私人）
  youtube_playlists.py 整理播放清單（排序、加入／移除、改名與說明、刪空清單），批次改影片說明欄
  library.py           整個系列的資源索引（SQLite library.db）＋本機瀏覽網頁
  make_static_font.py  可變字型 -> 靜態字重（libass 用）
  audio/               analyze / voice_probe / split_voices / asr_words / emotion_map
  qc/                  align / mouth / zoom（對嘴推近）/ sheets / subprev / focus（直式裁切中心）
skills/                Claude Code / Codex skills
examples/demo/         虛構示範專案（project.py、thumbs.py）
examples/series_template/  空白系列範本（research.md、style.md、每集骨架）
docs/zh-TW/, docs/en/  文件（中文 / 英文）
install.sh, install.ps1                    一行安裝
.claude-plugin/, .codex-plugin/            plugin 與 marketplace 設定
```

## 注意事項

- 生成影像會消耗 AutoIP 點數，送出即扣、沒有取消 API。正式送影片任務前務必先看靜圖。
- 本專案不附任何歌曲、角色圖、字型檔或生成素材。請使用你有權使用的素材，並遵守各平台對 AI 生成內容的揭露規定。
- 範例專案的歌詞與角色皆為虛構。

## 授權

[MIT](LICENSE)
