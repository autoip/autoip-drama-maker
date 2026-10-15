# autoip-mv-maker：AI 音樂 MV 製作管線

中文 | [English](README.en.md)

把一首歌做成完整 MV 的半自動流程。可以輸出完整版、1 分鐘短版和直式 Shorts：

- 對嘴主唱、固定陣容的樂團、劇情 B-roll
- 依情緒卡點的剪輯
- 動態字幕（kinetic typography），含韻腳標音與關鍵字特效
- 推廣卡、縮圖、上架文案

影像生成使用 [AutoIP](https://autoip.ai) 公開 API：文生圖、圖生圖、圖生影片、對嘴、多參考影片。剪輯、字幕與合成全部在本機用 ffmpeg + libass 完成。

## 範例影片

同一套流程，四種曲風與畫面風格。點縮圖到 YouTube 觀看。

| **暗黑金屬史詩** | **王家衛風港式抒情** | **國風古風對唱** | **賽博龐克女聲 Rap** |
|:---:|:---:|:---:|:---:|
| [![《黑日聖殿》](https://img.youtube.com/vi/ErQCd04OGA8/mqdefault.jpg)](https://youtu.be/ErQCd04OGA8) | [![《過期的那一分鐘》](https://img.youtube.com/vi/fMTLkI7qDq8/mqdefault.jpg)](https://youtu.be/fMTLkI7qDq8) | [![《洛川》](https://img.youtube.com/vi/OlIQYvfwZhA/mqdefault.jpg)](https://youtu.be/OlIQYvfwZhA) | [![《科技睪丸》](https://img.youtube.com/vi/fZ9SlclC9ng/mqdefault.jpg)](https://youtu.be/fZ9SlclC9ng) |
| 《暗影之島，烈焰之島》<br>男精靈死腔怒吼 × 女精靈空靈吟唱；颱風、古廟、赤潮、黑日 | 《過期的那一分鐘》<br>抽格殘影、霓虹綠與琥珀光、雨夜，時間與錯過 | 《洛川》<br>曹植 × 洛神；青綠山水、金箔礦彩、巨月與水龍、畫卷轉場 | 《科技睪丸》<br>霓虹賽博姐妹團駭進父權系統；動態字幕跟著節奏炸 |

## 一行安裝（Claude Code / Codex）

**macOS / Linux / Git Bash：**

```bash
curl -fsSL https://raw.githubusercontent.com/jsleetw/autoip-mv-maker/main/install.sh | bash
```

**Windows PowerShell：**

```powershell
irm https://raw.githubusercontent.com/jsleetw/autoip-mv-maker/main/install.ps1 | iex
```

安裝程式會把工具裝到 `~/.autoip-mv-maker`，內容包括 Python 虛擬環境和臉部模型。skill 會同時裝進 Claude Code 和 Codex。

也可以改用 plugin 安裝：

```bash
claude plugin marketplace add jsleetw/autoip-mv-maker && claude plugin install autoip-mv-maker@autoip-mv-maker
codex plugin marketplace add jsleetw/autoip-mv-maker && codex plugin add autoip-mv-maker@autoip-mv-maker
```

還需要自己準備三樣東西：
- **ffmpeg**（含 libass）
- **字型**
- **AutoIP API key**：放在環境變數 `AUTOIP_API_KEY`，不要寫進任何檔案。

詳見 [docs/zh-TW/SETUP.md](docs/zh-TW/SETUP.md)。

裝好後，在 Claude Code 或 Codex 裡說：

> 用 autoip-mv-maker 把 song.mp3 做成 MV

agent 會照流程一步一步做。每一批影片任務送出前，都會先給你看靜圖、報點數。

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

## 手動使用

```bash
git clone https://github.com/jsleetw/autoip-mv-maker && cd autoip-mv-maker
python -m venv venv && venv/Scripts/activate        # macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
export AUTOIP_API_KEY=aip_xxx                       # 在 AutoIP 儀表板申請；不要寫進任何檔案
cp -r examples/demo projects/my_song                # projects/ 已被 .gitignore 排除
# 放入 song.mp3、chars/*.png、fonts/，編輯 projects/my_song/project.py
```

接著照 [docs/zh-TW/WORKFLOW.md](docs/zh-TW/WORKFLOW.md) 一步一步做。從歌曲分析到上架共 10 個步驟，每一步都附指令和審核點。

## 文件

| 文件 | 內容 |
|---|---|
| [SETUP.md](docs/zh-TW/SETUP.md) | 安裝：一行安裝、Python 套件、ffmpeg、模型檔、字型 |
| [WORKFLOW.md](docs/zh-TW/WORKFLOW.md) | 完整流程：音訊 → 分鏡 → 生成 → 品管 → 剪輯 → 字幕 → 合成 → 縮圖 → 上架 |
| [PROJECT_FORMAT.md](docs/zh-TW/PROJECT_FORMAT.md) | `project.py` 每個欄位的說明 |
| [LESSONS.md](docs/zh-TW/LESSONS.md) | 踩過的坑與解法（生成模型的怪癖、libass、ASR、成本） |
| [EMOTIONAL_BEAT_EDITING.md](docs/zh-TW/EMOTIONAL_BEAT_EDITING.md) | 情緒卡點剪輯心法 |
| [PUBLISHING.md](docs/zh-TW/PUBLISHING.md) | 縮圖、YouTube SEO、社群貼文範本 |

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
  group_still.py       群像：拼貼 -> 圖生圖候選
  aip_runner.py        送出、輪詢、下載（可續跑、預設一次一個）
  credits.py           每個任務資料夾花了多少點數
  render_mv.py         EDL -> 分段 -> 字幕 -> 推廣卡 -> 成品 mp4 + srt
  epic.py              史詩劇場動態字幕引擎 (ASS)
  thumbkit.py          YouTube 縮圖工具
  make_static_font.py  可變字型 -> 靜態字重（libass 用）
  audio/               analyze / voice_probe / split_voices / asr_words / emotion_map
  qc/                  align / mouth / sheets / subprev / focus（直式裁切中心）
skills/                Claude Code / Codex skills
examples/demo/         虛構示範專案（project.py、thumbs.py）
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
