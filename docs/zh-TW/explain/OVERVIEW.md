# 說・解說影片 `explain/`

把一首 MV 背後的歷史和傳說，做成 3–6 分鐘的 YouTube 橫式解說：一個旁白、三十幾張畫、MV 的伴奏當配樂、跟著聲音走的字幕。畫面是靜態圖（靜態 B-roll）加平滑的推拉橫移，不跑影片任務，所以點數很省：一集 5 分鐘原價約 1,000 點，離峰約一半。

中文 | [English](../../en/explain/OVERVIEW.md)

## 一集的資料夾

```
projects/<系列>/
  voices/NARRATOR.wav        旁白的聲音樣本（整個系列共用）
  music/<歌>_inst.flac       MV 去人聲的伴奏（選用）
  fonts/ExplainerSerif.ttf   字幕字型（靜態字重，見下面）
  e01_<主題>/
    project.py               這一集的所有設定
    script.md                文案：## 旁白 底下每個 ### 是一章
    jobs/  voice/  images/  out/
```

範例：[examples/explain/demo](../../../examples/explain/demo/)（每個欄位都有註解）。

## 步驟

每一批要花點數的任務，送出前都先報「原價／離峰」兩種價，等你點頭。

1. **文案** `script.md`：`## 旁白`（或 `## Narration`）底下一章一個 `### 章名`。第一章當開場，講完會浮出片名（`TITLE`）。5 分鐘大約 1,400 字。
2. **旁白的聲音**（一個系列做一次）：用文生影音讓一位旁白員開口說一句（`voice_how` 寫口音和語氣，例如「台灣國語、咬字輕柔、像深夜電台」），再取出人聲成 5–15 秒的樣本。不用找人錄音。API 的語音克隆沒有口音參數，口音完全來自樣本。
3. **旁白**：
   ```bash
   python explain/narration.py P jobs          # 依章節切成每段 ≤1,100 字（API 上限 1,200），一段 50 點
   python dreamfab/aip_runner.py P/jobs/voice_jobs.json [--off-peak]
   python explain/narration.py P check         # 語速、哪幾個字要聽、結尾有沒有少、有沒有鬼打牆
   ```
   - 常被唸錯的字放進 `SAY`，換成**同樣長度、同音**的常用字（宓妃→伏妃、曹叡→曹銳、二二〇→二二零）；字幕照原文。
   - `check` 用拼音比對文稿和語音辨識，所以同音字不會誤報。列出來的是聽起來不一樣的地方，給耳朵最後確認。
   - 長段落有時會在結尾**鬼打牆**，不停重複最後幾句。`check` 會指出從哪一秒開始；用 `narration.py P cut voice/part2.flac 秒數` 剪掉，缺的句子另外補唸一小段，再寫進 `NARRATION`。
4. **畫面**：
   ```bash
   python explain/make_images.py P            # 還沒有圖的都排進 jobs/images_jobs.json，v4 一張 20 點
   python dreamfab/aip_runner.py P/jobs/images_jobs.json [--off-peak]
   ```
   AutoIP 文生圖 v4 就是 **MOSS-Image**，提示詞照它的 [prompt enhancer](https://github.com/OpenMOSS/MOSS-Image/blob/main/skills/moss-image-prompt-enhancer/SKILL.md) 寫：
   - **Caption**：一段連貫的英文描述，依序寫主體和動作、外觀、場景、鏡頭構圖、媒材、光線、色彩、氛圍。不要「8k, masterpiece, highly detailed」這類標籤串。畫面上要出現的字，用引號原文寫出來。`LOOKS` 也寫成一段散文，接在每個 caption 後面。
   - **Layout**（要擺字的封面、多格、物件位置）：在 `IMAGES` 直接放一個 dict：畫布 `width`／`height`（16 的倍數，等於出圖尺寸：v4 的 960x540 會出 1312x736）、`summary.caption`、扁平的 `items`（`label`、`caption`、像素 `bbox` [x1,y1,x2,y2]、字的 `text`）。`make_images.py` 會換算成 MOSS 讀的一行 JSON，結果跟官方的 compile_prompt.py 一致。
   - 送出前一定先看總表。AI 會畫出不該有的東西，例如三國軍帳裡掛一張現代地圖，送出之前和成片之前都要看過。
5. **配樂和 MV 片段**：MV 用 demucs 去人聲（`python -m demucs --two-stems=vocals -n htdemucs ...`）得到伴奏。`CH_MUSIC` 指定每一章從伴奏第幾秒開始：開場用前奏，故事高潮用副歌，安靜的章節用主歌伴奏。每段音量會自動拉平，旁白一出現就壓低。結尾想放 MV 片段，就把 `MV_CLIP` 指向 MV 檔，在 `SHOTS` 寫 `("MV:8.5", "我們的 MV", None, None)`，片段會放進金框，下面留字幕位置。
6. **合成**（不花點數）：
   ```bash
   python explain/sub_styles.py P               # 字幕樣式對照圖 out/subtitle_styles.jpg，給使用者選
   python explain/render.py P --until 東漢末年   # 先出 30 秒試片看美感
   python explain/render.py P                   # 整集：out/NAME.mp4 + out/NAME.zh-TW.srt
   ```
   `SHOTS` 每一項是（圖、從哪幾個字開始、運鏡、焦點）。運鏡有這幾種：
   - `in`／`out`：往焦點推近／從焦點拉遠
   - `left`／`right`：橫移
   - `frame`：整張放進金框，適合有字的封面
   - `scroll`：白底長卷切出來，由右往左橫移

   字幕、換圖、章名都跟著旁白的時間走。

   **字幕樣式讓使用者選**：`sub_styles.py` 把 4 種樣式（白字細黑邊、米白字深棕粗邊、加細金框、底部柔光暗帶）配上 `FONT` 資料夾裡的每個字型，放在這集最亮和最暗的畫上，排成一張對照圖。給使用者看，選好寫進 `project.py`，例如 `SUBS = dict(style="band", font="DFKai-SB", size=66)`（底部柔光暗帶＋標楷體；標楷體是 Windows 內建的 `kaiu.ttf`，要自己複製到 fonts/）。沒寫就是白字細黑邊。工筆、水墨這類亮的畫面，柔光暗帶最好讀。
7. **封面**：可以用 `mv/thumbkit.py` 拿片中的圖加大字（範例 `examples/mv/demo/thumbs.py`），或在 `IMAGES` 用 Layout 直接讓 v4 畫出帶標題的封面。
8. **上架**：
   ```bash
   python mv/youtube_upload.py P --title A --category 27 --dry-run   # 27 = 教育；讀 YouTube_SEO.txt、project.py 的 NAME/EDITS/RENDER
   python mv/youtube_upload.py P --title A --category 27             # 預設私人，在 Studio 看過再自己公開
   ```
   - 說明欄第一行放 MV 連結。章節時間從 render.py 印出的時間抄，每章至少 10 秒。
   - 播放清單用 `dreamfab/youtube_playlists.py`。
   - 影片還是私人時 API 不能留言，置頂留言要等公開之後，用留言的 ⋮ →「置頂」。
   - Studio 的「相關影片」只有 Shorts 才有。長片要連到 MV，用結束畫面和資訊卡，而且要等影片處理完才能設定。
9. **資源庫**：`python dreamfab/library.py serve projects` 之後，解說系列在 `http://127.0.0.1:8765/files/<系列>/`。每集一張卡片，標出做到哪一步；點進一集看成片和章節、封面、每張畫面和說明、旁白、文案、說明欄。加 `?raw` 看原始檔案清單。

## project.py

| 欄位 | 意思 |
|---|---|
| `LINE = "explain"` | 資源庫把這個資料夾當一般檔案瀏覽 |
| `NAME`、`RENDER`、`EDITS` | 輸出檔名、字幕語言；`EDITS` 給上傳程式用 |
| `SCRIPT`、`VOICE` | 文案、旁白樣本 |
| `SAY` | （字幕原文, 配音稿）成對，一樣長 |
| `NARRATION` | 選用：實際播哪些音檔（剪過、補唸過時） |
| `TITLE`、`ENDCARD` | 開場後的片名（主標、副標）；最後的 AI 生成字卡 |
| `FONT` | （字型家族名, 資料夾）：`python dreamfab/make_static_font.py NotoSerifTC-VF.ttf 600 "Explainer Serif" fonts/ExplainerSerif.ttf` |
| `SUBS` | 字幕樣式：`dict(style=..., font=字型家族名, size=58)`，使用者從 `sub_styles.py` 的對照圖選（見步驟 6）。`style`：`outline` 白字細黑邊（預設）、`heavy` 米白字深棕粗邊、`gold` 再加細金框、`band` 底部柔光暗帶。字型檔放在 `FONT` 那個資料夾 |
| `MUSIC`、`MUSIC_DB`、`CH_MUSIC` | 伴奏、每段的音量、每章從第幾秒開始 |
| `MV_CLIP` | `"MV:秒"` 畫面用的影片 |
| `GAPS` | 片頭、章節間、片名、段落間、片尾、交叉淡化的秒數 |
| `LOOKS`、`NEG`、`IMAGES`、`IMAGE_FIELDS` | 生圖（見步驟 4） |
| `SHOTS` | 時間軸（見步驟 6） |

## 學到的事

- 語速：克隆出來的聲音每秒大約唸 5 個字（不算標點）。章與章之間留 1.4 秒，開場後片名停 3.4 秒，聽起來比較從容。
- 一段旁白就算只唸一句也是 50 點。要補唸的句子集中起來一次唸。
- 史實和傳說要分清楚：文案裡講到傳說的地方就說它是傳說，說明欄附出處。
- 同一個主題換一個角度，就能再做一集。播放清單要專門放解說，讓 MV 和解說互相導流。
