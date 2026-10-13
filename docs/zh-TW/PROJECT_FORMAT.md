# project.py 欄位說明

中文 | [English](../en/PROJECT_FORMAT.md)

`project.py` 是一般的 Python 模組，由 `mvkit/common.load_project()` 載入。

- 時間一律是**歌曲秒數**。
- 路徑一律**相對於專案資料夾**。
- 完整範例見 [`examples/demo/project.py`](../../examples/demo/project.py)。

## 基本

| 欄位 | 說明 |
|---|---|
| `NAME` | 輸出檔名主體，例如 `my_song_MV` |
| `SONG` | 歌曲檔，例如 `song.mp3` |
| `STYLE` | 所有靜圖 prompt 結尾共用的風格句（英文） |
| `MOTION_PREFIX` | 所有圖生影片 prompt 開頭共用的一句（可中文） |
| `BAND_STAGE` | 樂手單人鏡頭的舞台描述 |
| `NEG` *(選填)* | 共用 negative prompt |
| `MULTI_NEG`、`MULTI_DESC_PREFIX` *(選填)* | 多參考影片的防矮小化 negative，以及每位成員描述前綴 |
| `GROUP_PROMPT_SUFFIX` *(選填)* | 群像靜圖的「成熟、高挑」描述 |
| `VIDEO` *(選填)* | 影片參數，預設 `dict(duration_seconds="5", resolution="768p", aspect_ratio="16:9")` |

## 陣容 `CHARS`

```python
CHARS = {"FV": dict(file="chars/soprano.png", name="主唱・女高音", kind="vocal",
                    role=("SOPRANO", "女高音"), desc="female singer with very long silver-white hair, ...")}
```

| 欄位 | 說明 |
|---|---|
| `kind` | `vocal` 會以臉為中心裁成 3:4 墊底圖，用於對嘴；`band` 則用整張圖當參考 |
| `role` | 間奏樂手名牌（英文, 本地語） |
| `desc` | 穩定的外觀描述，所有生成都沿用；多參考影片只取前 200 字 |

## 鏡頭

```python
LS_SCENES = [(id, char, scene_prompt, motion_prompt, caption)]           # 對嘴場景（關鍵影格）
LIPSYNC   = [(LS_id, scene_id, a0, dur, voice)]                          # 對嘴任務：歌曲 a0 起 dur 秒（≤30）、哪個聲部
BAND      = [(id, char | [chars], caption, prompt, motion)]               # 樂手；list = 群像
MULTI_PROMPT = {id: "多參考影片 prompt，@圖片 N = 第 N 位成員"}            # 群像沒有定稿靜圖時才用
BROLL     = [(id, caption, prompt, motion)]                              # 劇情畫面：文生圖 → 圖生影片
```

## 段落 `SECTIONS`

```python
SECTIONS = [("副歌：夜之劇場", (40.0, 56.0), "字幕設計備註", [(40.0, "歌詞一句", "F"), ...], ["LS03", "B04", ...])]
```

- 名稱格式為 `"<key>：<副標>"`。`key` 用來對應 `TYPO.acts` 與 `TYPO.specials`，副標會顯示在分幕標題下方。
- `(None, 秒數)` 的段落代表推廣卡，字幕引擎會略過。
- 每句歌詞是 `(開始秒數, 文字, 聲部)`，聲部對應 `AUDIO["voices"]` 的 key。

## 音訊 `AUDIO` / `VOICE_SPANS`

```python
AUDIO = dict(beats="audio/beats.json", vocals="audio/vocals.wav", words="audio/words.json",
             voices={"F": "audio/vocals_F.wav", "M": "audio/vocals_M.wav"})
VOICE_SPANS = {"F": [(16.5, 22.4), ...]}    # 其中一個聲部的時段；另一個聲部取補集
```

## 剪輯 `EDITS`

```python
EDITS = {"short": dict(cut=57.4, end=118.3, open_s=2, end_s=3, suffix="_1min", shots="""..."""),
         "full":  dict(cut=6.3, end=132.0, open_s=4, end_s=6, shots="""... @short ...""")}
```

| 欄位 | 說明 |
|---|---|
| `cut` / `end` | 取歌曲的哪一段 |
| `open_s` / `end_s` | 片頭、片尾卡秒數；卡片檔不存在時自動為 0 |
| `shots` | 剪輯表，規則如下 |

`shots` 的寫法：
- 每列 `start src [offset] [flash]`，以 `|` 或換行分隔，`#` 之後是註解。
- `@name` 會貼上另一組剪輯的內容。
- 第一列的 `start` 會被 `cut` 取代。
- 對嘴列的 offset 由 `align.json` 決定，填了也會被忽略。

## 合成 `RENDER`

| 欄位 | 預設 | 說明 |
|---|---|---|
| `fps` | 25 | |
| `crop` | `{}` | `{clip_id: "crop=w:h:x:y"}`，裁掉燒進字幕的區域 |
| `grade` | 對比 1.07、飽和 1.06、暗角、動態顆粒 | ffmpeg 調色濾鏡鏈 |
| `open_card` / `end_card` | — | 推廣卡圖片（1920×1080） |
| `lang` | `zh-TW` | SRT 檔名語言 |
| `tail_guard` | 0.35 | 對嘴片尾不使用的秒數 |

<a id="typo"></a>
## 動態字幕 `TYPO`

| 欄位 | 說明 |
|---|---|
| `font` / `font_file` / `font_scale` / `latin` | 字型家族名（libass 看到的名稱）、量字寬用的檔案、字級係數、拉丁字型 |
| `title` / `title_en` / `tagline` / `genre` | 片名卡用。`title` 每個字各占一拍 |
| `acts` | `{段落 key: "ACT I"}`：左上角分幕標題 |
| `specials` | `{段落 key: "intro" \| "plates" \| "finale" \| "outro"}`，見下表 |
| `band_plate` | 群像出現時的名牌，例如 `("THE BAND", "樂團")` |
| `readings` | `{韻腳詞: "標音"}`：句尾韻腳下的金色小字。單音節標在最後一個字下方，有連字號的標在整個詞下方 |
| `readings_anywhere` | 不在句尾也要標音的詞（仍需在最後 4 個字內） |
| `gags` | 關鍵字特效清單，見下表 |

`specials` 的四種特殊段落：

| 值 | 效果 |
|---|---|
| `intro` | 片名逐字燒出 |
| `plates` | 樂手名牌 |
| `finale` | 片名卡隨重拍砸入，再縮到上方 |
| `outro` | 片名銀色淡出 |

`gags` 每項格式是 `dict(type=..., match="詞" 或 ["詞", ...], ...)`。整句包含 `match` 才會觸發：

| type | 參數 | 效果 |
|---|---|---|
| `title_line` | — | 含片名的句子：片名巨字置中，紅幕拉開，聚光燈 |
| `color` | `chars`, `color` | 指定字改色（RRGGBB） |
| `enlarge` | `chars`, `scale` | 放大（咆哮） |
| `scurry` | `chars` | 縮小後竄逃出畫面右側 |
| `float_away` | `chars` | 往上飄走 |
| `tear` | `char` | 該字流下一滴淚 |
| `zone` | `zones=[a, b]` | 固定在 a 區；前一句在同一排時改用 b |
| `coins` | — | 金幣雨 |
| `clink` | `char` | 碰杯：兩道光撞擊加白閃 |
| `clap` | `char`, `word` | 滿版 CLAP |
| `wheel` | `words`, `highlight` | 詞語在圓環上旋轉（循環） |
| `explode` | — | 白閃，整句字炸散 |

聲部樣式：
- `F` 聲部：銀白色，滑入；一半機率直排。
- `M` 聲部：白字血紅邊，砸入後震動，帶隨機傾斜。
- 舊句在下一句出現時燒成灰往上飄。
