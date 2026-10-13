# autoip-mv-maker：AI 音樂 MV 製作管線

把一首歌做成完整 MV 的半自動流程。可以輸出完整版和 1 分鐘短版：

- 對嘴主唱、固定陣容的樂團、劇情 B-roll
- 依情緒卡點的剪輯
- 動態字幕（kinetic typography），含韻腳標音與關鍵字特效
- 推廣卡、縮圖、上架文案

影像生成使用 [AutoIP](https://autoip.app) 公開 API：文生圖、圖生圖、圖生影片、對嘴、多參考影片。剪輯、字幕與合成全部在本機用 ffmpeg + libass 完成。

> English summary: a semi-automatic pipeline that turns a song into a full music video:
> - generation: lip-synced singers, a fixed band line-up and story B-roll via the AutoIP API
> - editing: an emotion-driven, beat-snapped cut
> - typography: libass kinetic subtitles with per-keyword effects
> - packaging: thumbnails
>
> Everything is configured from one `project.py` per song. Docs are in Traditional Chinese; code comments are in English.

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

## 快速開始

```bash
python -m venv venv && venv/Scripts/activate        # macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
export AUTOIP_API_KEY=aip_xxx                       # 在 AutoIP 儀表板申請；不要寫進任何檔案
cp -r examples/demo projects/my_song                # projects/ 已被 .gitignore 排除
# 放入 song.mp3、chars/*.png、fonts/，編輯 projects/my_song/project.py
```

接著照 [docs/WORKFLOW.md](docs/WORKFLOW.md) 一步一步做。從歌曲分析到上架共 10 個步驟，每一步都附指令和審核點。

## 文件

| 文件 | 內容 |
|---|---|
| [docs/SETUP.md](docs/SETUP.md) | 安裝：Python 套件、ffmpeg、模型檔、字型 |
| [docs/WORKFLOW.md](docs/WORKFLOW.md) | 完整流程：音訊 → 分鏡 → 生成 → 品管 → 剪輯 → 字幕 → 合成 → 縮圖 → 上架 |
| [docs/PROJECT_FORMAT.md](docs/PROJECT_FORMAT.md) | `project.py` 每個欄位的說明 |
| [docs/LESSONS.md](docs/LESSONS.md) | 踩過的坑與解法（生成模型的怪癖、libass、ASR、成本） |
| [docs/EMOTIONAL_BEAT_EDITING.md](docs/EMOTIONAL_BEAT_EDITING.md) | 情緒卡點剪輯心法 |
| [docs/PUBLISHING.md](docs/PUBLISHING.md) | 縮圖、YouTube SEO、社群貼文範本 |

`claude/skills/` 是 [Claude Code](https://claude.com/claude-code) 的情緒卡點 skill。複製到 `~/.claude/skills/` 後，Claude 規劃剪輯時會自動套用。

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
  qc/                  align / mouth / sheets / subprev
examples/demo/         虛構示範專案（project.py、thumbs.py）
claude/skills/         Claude Code skill：情緒卡點剪輯
```

## 注意事項

- 生成影像會消耗 AutoIP 點數，送出即扣、沒有取消 API。正式送影片任務前務必先看靜圖。
- 本專案不附任何歌曲、角色圖、字型檔或生成素材。請使用你有權使用的素材，並遵守各平台對 AI 生成內容的揭露規定。
- 範例專案的歌詞與角色皆為虛構。

## 授權

[MIT](LICENSE)
