# project.py 欄位說明

中文 | [English](../en/PROJECT_FORMAT.md)

`project.py` 是一般的 Python 模組，由 `dramakit/common.load_project()` 載入。一集一個 `project.py`。

- 路徑一律**相對於這一集的資料夾**；整部劇共用的素材寫 `../cast/A.png`。
- 剪輯表的時間是**每支片段自己的秒數**，整集的時間軸由每一列接起來。
- 完整範例見 [`examples/demo/project.py`](../../examples/demo/project.py)。

## 基本

| 欄位 | 說明 |
|---|---|
| `NAME` | 輸出檔名主體，例如 `board_s1e01` |
| `TITLE` | 劇名（片名卡） |
| `EPISODE` | 第幾集（片名卡顯示「第 N 集」） |
| `ASPECT` | `"9:16"`（預設，直式短劇）或 `"16:9"`；決定生成的比例與輸出畫布 |
| `STYLE` | 所有靜圖 prompt 結尾共用的風格句（英文）。**只寫畫風與光線，不寫地點**：地點會被帶進每一張靜圖，連道具圖也是 |
| `MOTION_PREFIX` | 所有影片 prompt 開頭共用的一句（**英文**：多參考影片會把中文敘述跟台詞一起唸出來）。**只寫畫風**，寫了角色或道具會被塞進每一支影片 |
| `SFX` | 圖生影片、關鍵幀影片的 `MUSIC & SFX:` 預設句，例如 "No music, only ambience and the sounds of the action."（配樂在剪輯時統一加）。多參考影片不帶：AutoIP 的預設就是清楚的對白加環境音、沒有配樂；寫了 `MUSIC & SFX:` 反而會打開配樂 |
| `PROP_STYLE` *(選填)* | 道具參考圖的風格句，取代 `STYLE`，預設「只有物件、沒有人的產品照」。道具圖套劇照的風格會被畫成有演員的場景 |
| `NEG` *(選填)* | 共用 negative prompt（預設含 `nude, nsfw`） |
| `VIDEO` *(選填)* | 影片參數，預設 `dict(resolution="768p", aspect_ratio=ASPECT)` |
| `LS_FIELDS` *(選填)* | 對嘴的額外參數，例如 `dict(engine="h3")`（對嘴 3.0：嘴型更準，輸出較小） |
| `T2I` *(選填)* | 文生圖的額外參數，預設 `dict(mode="v3")` |
| `SIZES` *(選填)* | 靜圖尺寸：`frame`（鏡頭首幀、場景，預設 `540x960`／橫式 `960x540`）、`portrait`（定裝，`768x1024`）、`square`（道具，`1024x1024`） |

## 角色、場景、道具

三張表共用同一組 key（不能重複），鏡頭裡用 `@KEY` 指名。

```python
CAST = {"A": dict(name="<A 的名字>", file="cast/A.png", title="<A 揭露後的身分>",
                  desc="<A's look in English: age, hair, face, one outfit>",
                  prompt="neutral expression", voice="voices/A.wav", voice_src="voices/raw/a.m4a")}
SETS  = {"ROOM": dict(name="<室內場景>", file="sets/ROOM.png", desc="<the main interior in English>")}
PROPS = {"ITEM": dict(file="props/ITEM.png", desc="<the object, in English, with no writing on it>")}
```

| 欄位 | 說明 |
|---|---|
| `file` | 參考圖。自己提供，或由 `make_jobs.py P refs` 生成（角色要有 `prompt`；場景、道具用 `prompt` 或 `desc`） |
| `desc` | 穩定的外觀描述（英文），所有生成都沿用；多參考影片只讀前 200 字 |
| `ref_desc` *(選填)* | 多參考影片改用這段描述（例如更短的版本） |
| `prompt` *(選填)* | 生成參考圖時加在 `desc` 後面的句子（角色：表情、姿態） |
| `base` *(選填)* | 從一張你有的圖延伸（你有權使用的照片、美術、之前專案的定裝），改用圖生圖。圖裡有的服裝、道具、畫風會一直留著，用 `base_crop` 裁掉 |
| `base_crop` / `base_box` *(選填)* | `base_crop = (x0, y0, x1, y1)`：只取這一塊（比例）；`base_box = (x, y, 寬)`：放在畫布的哪裡（比例），例如只裁臉、放在半身照頭的位置，其餘是素色底。不設就整張放進畫布、貼齊下緣 |
| `base_strength` *(選填)* | 圖生圖強度，預設 0.8。給一串（例如 `[0.6, 0.75]`）就每個強度出一張候選到 `candidates/`，挑一張複製成 `file` |
| `name` | 角色：字幕旁的名字、人物字卡的名字。場景：prompt 裡怎麼稱呼這個地點 |
| `title` *(角色)* | 人物字卡上方的職稱／身分 |
| `color` *(角色，選填)* | 這個角色台詞字幕的顏色（RRGGBB） |
| `file=None` / `unseen` *(角色)* | 不給臉的角色（反派先不露臉、只聽到聲音）：沒有參考圖，他說的台詞照樣用他的聲音樣本；`unseen` 寫他在畫面裡的樣子，例如「背對鏡頭坐在辦公桌後的男人」（備註用；沒有定裝圖時也是配聲音那段影片的畫面），提示詞不會另外加「只有＿＿說話」（試拍時這句被唸成台詞）。`act` 裡不要 `@` 他，用文字描述；只拍手、物件的特寫最穩，背對鏡頭的人常會轉過來露出一張陌生的臉。有定裝圖也可以只寫 `unseen`：這一集照樣不露臉，圖用來配他的聲音（`make_jobs.py P voices`），之後的集數拿掉 `unseen` 就露臉 |
| `voice` *(角色)* | 聲音樣本，跟這個角色的每一句台詞一起送出 |
| `voice_src` / `voice_span` *(角色)* | 原始錄音（或 `make_jobs.py P voices` 生成的 `voices/raw/<KEY>.mp4`）與要用的秒數 `(a, b)`；`voices.py` 從這裡切出 `voice` |
| `voice_line` / `voice_how` *(角色)* | 讓 AutoIP 配聲音：角色開口說的一句話（約 20–30 字）和語氣；`make_jobs.py P voices` 用定裝圖跑圖生影音，寫到 `voice_src` |
| `voice_secs` / `voice_who` *(角色，選填)* | 那段影片的秒數（預設依字數，5–15）；沒有臉的角色跑文字生成動畫時畫面裡的樣子（預設 `unseen`） |

## 場次 `SCENES`

```python
SCENES = [("S2", "ROOM", "<日／夜>，<室內場景>")]       # (場次 id, 場景 key, 場景標題)
```

場景會放進這一場每一支多參考影片的參考圖（最後一張），每個 `SHOT` 都寫上地點。

## 鏡頭 `SHOTS`

照劇本順序排。每顆鏡頭一個 `dict`：

```python
dict(id="S2_08", scene="S2", cast=["B", "A"], say=("C", "<C 揭露 A 身分的那一句>", "<語氣>"),
     act="@C <walks past @B toward @A>, @B frozen in the background, medium shot.")
```

| 欄位 | 說明 |
|---|---|
| `id` | 鏡頭 id，也是 `clips/<id>.mp4`、`kf/<id>.png` 的檔名 |
| `scene` | 場次 id |
| `kind` | `M`（預設）多參考影片、`LS` 對嘴、`I2V` 圖生影片、`K` 關鍵幀影片，見下表 |
| `say` | `(說話的角色, 台詞, 語氣)`。台詞中文，語氣寫**英文**。一顆鏡頭一個人說話；以每秒 4 字估算長度 |
| `act` | 動作與鏡頭（**英文**；中文敘述會被 H3 跟台詞一起唸出來）。`@KEY` 指名角色、道具、場景，會換成 `@圖片 N`；不要用 he／she，用 `@KEY` 指名（性別字會蓋過聲音樣本）。要在一支片裡分好幾鏡，直接寫 `SHOT 1:`、`SHOT 2:` 多行；台詞會接在最後一個 SHOT 後面，說話的那鏡放最後 |
| `cast` / `props` | 額外要放進參考圖、但 `act` 沒有 `@` 到的角色／道具 |
| `set` *(選填)* | 這顆鏡頭改用別的場景（預設是場次的場景） |
| `secs` | 片長。`M`：5–10（預設依台詞長度）；`I2V`：預設 5；`K`：6／10／15 |
| `sfx` *(選填)* | 這顆鏡頭的 `MUSIC & SFX:`（英文），取代 `project.SFX`；多參考鏡頭寫了會連配樂一起打開 |
| `still` | `LS`／`I2V`／`K` 的首幀靜圖描述（英文），生成 `kf/<id>.png` |
| `to` | `K`：尾幀用哪一顆鏡頭的靜圖（`kf/<to>.png`） |
| `audio` | `LS`：這句的錄音，預設 `lines/<id>.wav` |
| `cap` *(選填)* | 審核表上的說明，預設是台詞或動作 |

| `kind` | AutoIP 功能 | 送出的東西 |
|---|---|---|
| `M` | 多參考影片 3.0 `/videos/multi-subject-reference` | 參考圖（說話的人、`@KEY`、`cast`、`props`、場景；≤6 張）、每張的描述、prompt、`dialogue_text`、`voice_sample` |
| `LS` | 對嘴 `/videos/lip-sync` | `kf/<id>.png` ＋ `lines/<id>.wav`；prompt 只寫語氣與「鏡頭穩定」 |
| `I2V` | 圖生影片 3.0 `/videos/image-to-video` | `kf/<id>.png` ＋ 動作 |
| `K` | 關鍵幀影片 `/videos/keyframe`（2frame） | `kf/<id>.png` → `kf/<to>.png` ＋ 動作 |

## 剪輯 `EDITS`

```python
EDITS = {"main": dict(shots="""
    S2_01 auto flash intro=B
    ^S2_04 0.8 1.0 @-1.0
"""), "wide": dict(..., size=(1920, 1080), suffix="_wide")}
```

| 欄位 | 說明 |
|---|---|
| `shots` | 剪輯表，規則如下 |
| `size` | 畫布，預設依 `ASPECT`：`(1080, 1920)` 或 `(1920, 1080)` |
| `suffix` | 輸出檔名後綴 |
| `focus` | `{素材 id: 0–1}`：素材比例跟畫布不同時的水平裁切中心，預設 0.5 |
| `music` | 只對這組剪輯換配樂（格式同 `MUSIC`） |
| `end_card` / `end_s` | 片尾卡圖片與秒數（選用；預設沒有片尾卡，結束在卡點） |

`shots` 的寫法：
- **一般列** `src [in|auto] [dur] [flags]`：接在上一列後面，畫面和聲音都用這支片段。`in`、`dur` 是片段的秒數；只寫 id 或 `auto` 時照 `speech.json` 剪到台詞前後。
- **插入列** `^src [in] [dur] @at [flags]`：只換畫面、不換聲音，蓋在上一個一般列上，從它開頭往後 `at` 秒開始（`at` 是負數時從它結尾往前算）。可以延伸到下一列（J cut）。
- `src` 寫路徑（例如 `../s1e01_x/clips/S2_08`）就從別集拿片段，前情提要用；字幕會讀那一集的台詞。
- 單獨一行 `@name` 貼上另一組剪輯（例如 `@recap`）。
- 以換行或 `|` 分隔，`#` 之後是註解。

| flag | 效果 |
|---|---|
| `flash` | 白閃進場 |
| `black` | 從黑淡入 |
| `zoom` / `zoom=1.2` | 0.25 秒內推近到 1.15 倍（或指定倍數），整列保持 |
| `freeze=S` | 這列結束後定格 S 秒（畫面降飽和，聲音靜音、配樂繼續） |
| `end` / `end=下集見` | 卡點文字（預設 `TYPO.end_text`），出現在定格上或這列最後 1.6 秒 |
| `mute` | 不用這支片段的聲音 |
| `sfx=name` | 這列開頭放 `sfx/name.wav`（或 .mp3、.m4a） |
| `intro=KEY` | 人物字卡：職稱＋名字 |
| `title` | 片名卡：劇名＋第幾集 |
| `label=前情提要` | 左上角標字，整列 |
| `heard` | 字幕顯示 `speech.py` 實際聽到的話，不顯示劇本台詞（NG 花絮：把舞台指示唸出來的那種） |
| `chat=NAME` | 直播留言：`CHAT[NAME]` 的留言在這一列從左下一則一則往上捲（人物字卡也在左邊，不要放同一列） |

直播留言寫在 `CHAT = {"hate": [("夜貓子", "這身材也敢跳？"), ...], ...}`：留言是字幕疊上去的，不靠生成（手機螢幕一律背對鏡頭）。

## 配樂 `MUSIC`

```python
MUSIC = [("tension", "S2_01", "S2_05", -18), ("reveal", "S2_08", None, -15)]
```

`(檔名, 從哪一列, 到哪一列, 音量 dB)`：檔案在 `music/`（找不到再找上一層），起訖寫鏡頭 id（那一列第一次出現的時間）、秒數或 `None`（開頭／結尾）。配樂會循環到需要的長度、淡入淡出，對白出現時自動壓低。

## 合成 `RENDER`

| 欄位 | 預設 | 說明 |
|---|---|---|
| `fps` | 25 | |
| `pad` | `(0.15, 0.35)` | `auto` 列在台詞前、後保留的秒數 |
| `hold` | 2.0 | 沒有台詞的 `auto` 列取幾秒 |
| `tail_guard` | 0.3 | 片段最後不使用的秒數 |
| `crop` | `{}` | `{素材 id: "crop=w:h:x:y"}`，裁掉角落的小字 |
| `grade` | 對比 1.03、飽和 1.05 | ffmpeg 調色濾鏡鏈 |
| `lufs` | −16 | 整體響度 |
| `sfx_gain` | −4 | 音效音量 dB |
| `lang` | `zh-TW` | SRT 檔名語言 |

## 字幕與字卡 `TYPO`

| 欄位 | 預設 | 說明 |
|---|---|---|
| `font` | `Noto Sans TC` | 字型家族名（libass 看到的名稱）；可變字型要先用 `make_static_font.py` 切出靜態字重 |
| `font_scale` | 1.45 | libass 字級換算係數（Noto CJK 約 1.45） |
| `size` | 54 | 台詞字的大小（1080 寬時的像素） |
| `max_chars` | 14（直式）／22（橫式） | 每段字幕最多幾個字，依標點切 |
| `sub_y` | 0.74（直式）／0.92（橫式） | 字幕底線的高度比例；直式避開 App 下方的標題與按鈕 |
| `intro_y` | 0.56（直式）／0.6（橫式） | 人物字卡的高度比例 |
| `intro_s` / `title_s` | 2.4 / 2.6 | 人物字卡、片名卡停留秒數 |
| `end_text` | 未完待續 | `end` 沒寫文字時用這句 |
| `badge` | — | 例如 `"第1集"`：整集右上角的小標 |
| `accent` | `F2C55C` | 人物字卡的色條、職稱、片名卡集數的顏色（直播留言的帳號名也用這個顏色） |
| `chat_y` / `chat_rows` | 0.66（直式）／0.8（橫式）／5 | 直播留言最下面一則的高度比例／同時顯示幾則 |

字幕規則：
- 台詞依標點切段，句尾的「，。」拿掉，「！？…」保留。
- 有 `speech.json` 的逐字時間就照字對上（difflib），沒有就平均分配在台詞的秒數裡。
- 字幕不跨過這一列（含定格）；下一段出現時上一段收掉。
