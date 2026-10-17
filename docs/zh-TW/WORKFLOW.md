# 完整流程：從一首歌到上架

中文 | [English](../en/WORKFLOW.md)

以 `projects/my_song` 為例。下文以 `P` 代表這個路徑，所有指令都在 repo 根目錄執行。

```
歌曲 ─┬─ 1 音訊分析 ── 節拍 / 結構 / 人聲分離 / 分軌 / 歌詞時間 / 情緒地圖
      │
      ├─ 2 陣容與分鏡 ── project.py → storyboard.json + shots.json
      ├─ 3 關鍵影格 ──── 文生圖 / 圖生圖 →【審核圖：人工確認】
      ├─ 4 影片生成 ──── 對嘴 / 圖生影片 / 群像 →【審核圖：人工確認】
      ├─ 5 品管 ──────── 對嘴對位 / 嘴巴有沒有動 / 雜訊尾巴
      ├─ 6 剪輯表 ────── 情緒卡點 EDL（完整版 + 短版）
      ├─ 7 字幕 ──────── 動態字幕主題、快速預覽
      ├─ 8 合成 ──────── render_mv.py → mp4 + srt
      ├─ 9 縮圖 ──────── 從成片抓畫面做 A/B/C 三張
      └─ 10 上架 ─────── 標題 / 說明 / 章節 / 標籤 / 社群貼文
```

**原則：AutoIP 點數送出即扣、沒有取消 API。每一批影片任務送出前，都要先產生靜圖審核圖給決策者看。**

---

## 1. 音訊分析

```bash
mkdir -p P/audio
ffmpeg -i P/song.mp3 -ar 44100 -ac 2 P/audio/song.wav
python mvkit/audio/analyze.py P/audio/song.wav P/audio/beats.json          # 節拍、強拍、段落邊界
python -m demucs --two-stems=vocals -n htdemucs -o P/audio/sep P/audio/song.wav
cp P/audio/sep/htdemucs/song/vocals.wav P/audio/vocals.wav
```

**誰在唱：** 遇到雙主唱（例如嘶吼與女高音），先看每秒的音高與有聲比例：

```bash
python mvkit/audio/voice_probe.py P/audio/vocals.wav
```

- 女高音的窗格有聲比例高、f0 > 350 Hz。
- 嘶吼的窗格有能量，但幾乎無聲（unvoiced）。
- 把其中一個聲部的時段寫進 `project.VOICE_SPANS`，然後切軌：

```bash
python mvkit/audio/split_voices.py P          # -> audio/vocals_F.wav, audio/vocals_M.wav
```

每支對嘴影片只吃自己聲部的音軌，另一個人唱的時候嘴巴不會亂動。

**歌詞時間：**
1. 先在 `project.SECTIONS` 填好每句的開始時間：聽歌、對照 `beats.json` 和波形。
2. 再跑分段 ASR 取得逐字時間：

```bash
python mvkit/audio/asr_words.py P 15.5,46.5 58.5,74 74.5,103      # 有人聲的區段
```

- 台語、嘶吼、重混音的辨識文字幾乎不可用，但以歌詞當 prompt、切短區段後，**時間點**大致可用。
- 對不上的句子會在句首時間之間平均分配，所以句首時間一定要準。

**情緒地圖：** 剪輯的依據，見 [EMOTIONAL_BEAT_EDITING.md](EMOTIONAL_BEAT_EDITING.md)。

```bash
python mvkit/audio/emotion_map.py P/audio/song.wav P/audio/beats.json P/audio/vocals.wav > P/audio/emotion.txt
```

## 2. 陣容與分鏡

1. 角色圖放在 `P/chars/`。
2. 在 `project.py` 填寫以下欄位，各欄位說明見 [PROJECT_FORMAT.md](PROJECT_FORMAT.md)：
   - `CHARS`：固定陣容。每個角色一句穩定的英文外觀描述，所有 prompt 都會沿用。
   - `LS_SCENES`、`LIPSYNC`：主唱對嘴場景，以及每段對嘴取歌曲的哪 ≤30 秒。
   - `BAND`：樂手單人鏡頭、群像鏡頭。
   - `BROLL`：劇情畫面。
   - `SECTIONS`：段落、歌詞、聲部、這段要用哪些鏡頭。

```bash
python mvkit/faces.py P          # 角色臉部框；偵測不到的可以手動加
python mvkit/storyboard.py P     # -> storyboard.json, shots.json；會列出沒被任何段落用到的鏡頭
```

**分鏡設計要點：**
- 段落情緒決定鏡頭規模：鋪陳用特寫、副歌用中景與群像、高潮用大場面。
- 歌詞裡的關鍵意象各配一個 B-roll，例如「乾杯」配紅酒碰杯、「眼淚」配面具流淚。
- B-roll 裡的路人一律 `NO_FACES`（面具或陰影），避免冒出陣容以外的臉。
- 樂團陣容一旦定案就不要再改，所有鏡頭都要能認出同一批人。

## 3. 關鍵影格（靜圖）

```bash
python mvkit/make_jobs.py P kf                       # -> P/jobs/kf_jobs.json
python mvkit/aip_runner.py P/jobs/kf_jobs.json       # 一次一個；可中斷後續跑
python mvkit/qc/sheets.py stills P/review_kf.jpg P/kf
```

把 `review_kf.jpg` 給決策者看。不滿意的處理方式：
1. 把該圖移到 `kf_rejected/`。
2. 修改 `project.py` 的 prompt。
3. 用 `ONLY=ID1,ID2` 重跑這幾張。

```bash
ONLY=O1,B05 python mvkit/make_jobs.py P kf && python mvkit/aip_runner.py P/jobs/kf_jobs.json
```

**群像鏡頭**（`BAND` 中有多位成員）：

```bash
python mvkit/group_still.py P W1                     # 拼貼 + 2 個強度的圖生圖任務
python mvkit/aip_runner.py P/jobs/W1_stills.json
# 看 P/kf_candidates/W1_*.png，挑一張複製成 P/kf/W1.png
```

## 4. 影片生成

```bash
python mvkit/make_jobs.py P video                    # 對嘴音訊會自動從分軌切出
python mvkit/aip_runner.py P/jobs/video_jobs.json
python mvkit/qc/sheets.py strips P/review_clips.jpg P/clips/*.mp4
```

- 對嘴：關鍵影格 + 該聲部音軌。
- 單人樂手與 B-roll：圖生影片。
- 群像：有定稿靜圖就走圖生影片，沒有才用多參考影片。

**新角色、群像、改過的畫面一律先給靜圖審核，才送影片。**

## 5. 品管

```bash
python mvkit/qc/align.py P                    # 每支對嘴影片的音訊實際落在歌曲哪裡 -> align.json
python mvkit/qc/mouth.py P timeline LS01 LS02  # 每 0.5 秒的嘴部動作量；'.' = 找不到臉（拉遠了）
```

必看項目：
- 對嘴開頭幾秒沒動嘴。
- 對嘴中途鏡頭拉遠成全身。
- 對嘴片尾 0.2 秒白色雜訊：合成時預設不用最後 0.35 秒。
- 對嘴畫面燒進字幕：送 AutoIP `/videos/restore`（`source_video` ＋ `operations[]=subtitle`）去掉，不裁切、不換鏡頭。
- 圖生影片冒出亂碼文字：只取乾淨的那幾秒。
- 人物中途換臉：只用前段。

處理方式見 [LESSONS.md](LESSONS.md)。

## 6. 剪輯表（EDL）

寫在 `project.EDITS`，每種剪法一組，例如 `full` 和 `short`。每列格式為 `start src [offset] [flash]`，`start` 是歌曲秒數：

```python
EDITS = {
    "short": dict(cut=57.4, end=118.3, open_s=2, end_s=3, suffix="_1min", shots="""
        57.4 W1 0 flash | 58.2 D1 | 59.0 LS01 | 60.3 B10 ...
    """),
    "full": dict(cut=6.3, end=132.0, open_s=4, end_s=6, shots="""
        6.3 B01 | 8.4 B02 ...
        @short                          # 直接沿用短版的剪輯
        119.1 B28 0 flash ...
    """),
}
```

- 對嘴列不用填 offset：合成時依 `align.json` 自動對齊嘴型。
- 切點會自動吸附到 0.08 秒內的節拍。
- 照情緒地圖排：
  - 高峰段 1–2 拍一切，但保留一個錨點長鏡頭。
  - 低谷段 2 小節以上才切。
  - 呼吸點與驟降點不放切點。
  - 最強重拍加 `flash`。
- 檢查嘴型：`python mvkit/qc/mouth.py P edl short`，標 `IDLE?` 的鏡頭要換。

## 7. 字幕

在 `project.TYPO` 設定字型、片名、分幕名稱、韻腳標音、關鍵字特效，詳見 [PROJECT_FORMAT.md](PROJECT_FORMAT.md#typo)。調整時只渲字幕、不渲影片，幾秒就能看到結果：

```bash
python mvkit/qc/subprev.py P 74 90 P/subprev.jpg 75.6 79.5 82.5 86.0
```

要檢查的地方：
- 字有沒有蓋到主唱的臉。
- 字有沒有超出畫面（會印出 `offscreen`）。
- 標音是否和歌詞註記一致。
- 片名卡在高潮時有沒有及時讓位。

## 8. 合成

```bash
python mvkit/render_mv.py P short
python mvkit/render_mv.py P full
REUSE_BODY=1 python mvkit/render_mv.py P full        # 只改字幕或推廣卡時，沿用已渲好的畫面
```

- 輸出 `P/out/<NAME><suffix>.mp4` 與 `.zh-TW.srt`。
- 剪輯表在合成時才從 `project.EDITS` 解析，不會發生「拿短版 EDL 去渲完整版」的錯。
- 渲完抽格檢查：`python mvkit/qc/sheets.py video P/review_final.jpg P/out/xxx.mp4 5 20 35 ...`

### 直式版（Shorts / Reels）

在剪輯加上 `size=(1080, 1920)` 就會渲成直式。沿用既有的剪法，只換畫布：

```python
V = dict(open_s=0, end_s=4, size=(1080, 1920), end_card="cards/end_v.jpg",
         focus={"S12": 0.64, "B16": 0.2},   # 每個素材的裁切中心：0 = 最左、1 = 最右，預設 0.5
         zones={"TL": (400, 300), "TR": (680, 300), "TC": (540, 260), "BL": (420, 1480), "BR": (660, 1480),
                "BC": (540, 1560), "ML": (420, 1250), "MR": (660, 1250), "C": (540, 960)})
EDITS["shorts"] = dict(EDITS["short"], suffix="_shorts", **V)
```

```bash
python mvkit/qc/focus.py P shorts       # 用臉部偵測算出每個人物鏡頭的 focus
python mvkit/render_mv.py P shorts
```

- 每個鏡頭各自從 16:9 素材裁出 9:16，不是把橫式成片切中間，所以字幕會依直式畫布重新排版，不會被切掉。
- `focus`：`qc/focus.py` 會印出一行 `focus={...}`，直接貼進剪輯。沒有臉的空鏡印 `?`，先渲一次看抽格，再用眼睛挑主體的位置。
- `zones`：橫排歌詞的落點。直式畫面的臉在中段，所以把歌詞放在頭頂上方和胸口以下；直排歌詞會自動貼在左右兩側。
- 片頭不放推廣卡：Shorts 的前一兩秒決定觀眾滑不滑走，直接從副歌第一句開始。片尾卡要換成直式圖，剪輯裡的 `end_card` 會覆蓋 `RENDER` 的設定。
- 英文歌詞：一段以空格連起來的英文是一個字塊，不會自動折行。直式寬度只有 1080，在 `SECTIONS` 把英文拆成 15 個字母以內的短句。
- 素材大多 1280 寬，裁成直式約放大 2.7 倍。人物鏡頭挑半身或特寫，空鏡挑主體明確的。
- 放大後對嘴全是大臉，字幕也顯得很大：直式版把 `TYPO.font_scale` 調低（例如 1.45 → 1.0），對嘴的長音特寫不要超過 2 秒，前段也要密集穿插劇情畫面（見 [EMOTIONAL_BEAT_EDITING.md](EMOTIONAL_BEAT_EDITING.md)「敘事剪輯技巧」）。

## 9. 縮圖

從成片抓 3–5 個候選畫面，用 `thumbkit` 做 A/B/C 三個方向，範例見 `examples/demo/thumbs.py`：

| 版本 | 方向 |
|---|---|
| A | 音樂性：主唱對決、樂團群像 |
| B | 梗：歌詞最狠的一句 |
| C | 世界觀：場景、片名 |

## 10. 上架

見 [PUBLISHING.md](PUBLISHING.md)：標題公式、說明欄結構、章節、標籤、AI 揭露、諷刺聲明、社群貼文。

---

## 成本參考

以下是撰寫時的點數，實際以 `GET /api/v1/pricing` 為準：

| 任務 | 點數 |
|---|---|
| 文生圖 | 10 |
| 圖生圖 | 15 |
| 對嘴（≤30 秒） | 50 |
| 圖生影片 768p 5 秒 | 75 |
| 多參考影片 768p 5 秒 | 80 |

一支 2 分鐘、約 100 個鏡頭的完整版，連同重做大約 4,000–4,700 點。要省點數：
- 短版先做，完整版沿用短版的素材。
- 同一段對嘴生成 2–3 個場景輪替使用。
- 群像先做靜圖。
