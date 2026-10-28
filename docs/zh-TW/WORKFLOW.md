# 完整流程：從劇本到上架

中文 | [English](../en/WORKFLOW.md)

以 `projects/<劇名>/s1e01_<集名>` 為例，下文以 `P` 代表這個路徑，所有指令都在 repo 根目錄執行。要做一整部劇（很多集），先看 [SERIES_PLANNING.md](SERIES_PLANNING.md)。

```
劇本 ─┬─ 1 劇本 ────────── 劇本_v1.md：開場鉤子、衝突、爽點、卡點
      ├─ 2 定裝與場景 ──── 角色、場景、道具靜圖 →【審核圖：人工確認】
      ├─ 3 聲音樣本 ────── 每個角色一段 5–15 秒的聲音
      ├─ 4 分鏡 ────────── project.py SHOTS → storyboard.py（台詞長度、參考圖、點數估算）
      ├─ 5 首幀靜圖 ────── 對嘴／圖生影片／關鍵幀鏡頭的首幀 →【審核圖：人工確認】
      ├─ 6 試拍 ────────── 每個角色先拍一顆，聽聲音、看長相 →【人工確認】
      ├─ 7 影片生成 ────── 任務審核表 →【報點數、人工確認】→ runner
      ├─ 8 品管 ────────── 壞檔、換鏡點、台詞有沒有講完、抽格
      ├─ 9 剪輯 ────────── EDITS：正反打、反應鏡頭、L/J cut、爽點、卡點
      ├─ 10 字幕與聲音 ─── 字幕主題、人物字卡、配樂、音效
      ├─ 11 合成 ───────── render_ep.py → mp4 + srt
      └─ 12 封面與上架 ─── 封面、標題、說明、hashtag
```

**原則：AutoIP 點數送出即扣、沒有取消 API。每一批任務送出前，都先給決策者看審核圖、報點數。**

---

## 0. 專案資料夾

```bash
mkdir -p projects/<劇名>
cp -r examples/series_template/* projects/<劇名>/          # plan.md、style.md、characters.md、集數骨架
mv projects/<劇名>/s1e01_title projects/<劇名>/s1e01_<集名>
cp examples/demo/project.py projects/<劇名>/s1e01_<集名>/   # 第一集從示範開始；之後每集複製上一集
```

- **資料夾在第一次送 AutoIP 任務之前定名。** 任務檔 `jobs/*.json` 寫的是絕對路徑，送出後改名，續跑會找不到檔案。
- 示範專案把所有素材放在這一集的資料夾裡。做整部劇時，角色、場景、道具、聲音樣本改放劇的資料夾（`projects/<劇名>/cast/` 等），`project.py` 寫 `../cast/A.png`，每集共用同一張定裝與同一段聲音。`sfx/`、`music/`、`fonts/` 不用改路徑：會先找這一集，再找上一層。

## 1. 劇本

劇情只寫在你自己的專案裡（`projects/` 不進 git），repo 的範例與文件都只有結構。寫 `劇本_v1.md`（格式見 `examples/series_template/s1e01_title/劇本_v1.md`），改版另存 `v2`、`v3`，不覆蓋。

- 一集 1–2 分鐘。**前 3 秒就是衝突**：不要從片名、空景、自我介紹開始。
- 一集至少一個爽點（反擊、揭露、打臉），最後 3–5 秒停在卡點（下一集才回答的問題）。
- 一句台詞一個人講。多參考影片一次只能帶一段聲音樣本，所以**每顆鏡頭只有一個人說話**；對話靠正反打剪出來。
- 每句台詞以每秒 4 字估算：10 秒的鏡頭最多 40 字。更長的拆成兩句，或改用對嘴（自己錄音）。

劇本定稿後，把場次寫進 `project.SCENES`、鏡頭寫進 `project.SHOTS`，欄位見 [PROJECT_FORMAT.md](PROJECT_FORMAT.md)。

## 2. 定裝、場景、道具

在 `CAST`、`SETS`、`PROPS` 寫好外觀描述（英文，所有生成都沿用）。角色圖可以自己提供（你有權使用的照片或美術），或寫 `prompt` 讓 AutoIP 畫：

```bash
python dramakit/make_jobs.py P refs                    # 還沒有檔案的角色（有 prompt 或 base 的）、場景、道具
python dramakit/aip_runner.py P/jobs/refs_jobs.json    # 一次一個；可中斷後續跑
python dramakit/qc/sheets.py stills P/review_cast.jpg P/cast     # 整部劇共用的素材在 P/../cast
python dramakit/qc/sheets.py stills P/review_sets.jpg P/sets
```

把審核圖給決策者看。不滿意的處理方式：
1. 把該圖移到 `rejected/`（不要刪，之後才查得到為什麼退）。
2. 改 `desc` 或 `prompt`。
3. `ONLY=A python dramakit/make_jobs.py P refs` 只重做這一張。

- **一個角色一套造型**，整個篇章都用同一張定裝圖。換裝就是新的一張圖、新的 key（例如 `A_ARC2`）。
- 場景底圖不要有人：`make_jobs.py` 會自動加上「空無一人」。
- 定裝圖背景簡單、腰上、正面。
- 多參考影片常會溶進定裝圖的背景。角色在某個場景演一整集時，用 `python dramakit/restage.py cast/A.png sets/ROOM.png cast/A_room.png` 把人去背貼進那個場景（臉不動，不花點數），那一集的 `file` 改用這張。頭飾、流蘇這類被切掉的東西，加第五個參數保留周圍的原背景：`... 3 70`。需要 `pip install mediapipe`，第一次會下載分割模型。

## 3. 聲音樣本

每個角色一段乾淨的聲音（5–15 秒、一個人、沒有配樂）。

**讓 AutoIP 配（預設）**：在 `CAST` 寫 `voice_line`（角色說的一句話，約 20–30 字）、`voice_how`（語氣），`voice_src` 寫成 `voices/raw/<KEY>.mp4`。`make_jobs.py P voices` 用定裝圖當首幀跑圖生影音，讓角色開口說這句；模型會依這張臉配出聲音。沒有臉的角色（`file=None`）改跑文字生成動畫，畫面照 `voice_who`（沒寫就用 `unseen`）。

```bash
python dramakit/make_jobs.py P voices    # -> jobs/voices_jobs.json（480p，約 6 點／秒，一個角色 40–55 點）
python dramakit/aip_runner.py P/jobs/voices_jobs.json
python dramakit/voices.py P              # -> voices/<KEY>.wav：去頭尾靜音、去低頻、音量標準化
```

先聽：是不是一個人在講、有沒有配樂或音效、聲音配不配這張臉。不喜歡就刪掉 `voices/raw/<KEY>.mp4` 和 `voices/<KEY>.wav`，改 `voice_how` 再跑一次。定案後整部劇都用這段樣本。

**自己錄**：`voice_src` 指向錄音檔（任何 ffmpeg 讀得到的格式），必要時用 `voice_span` 指定秒數，直接跑 `voices.py P`。只用你有權使用的聲音：自己的、取得同意的演員、授權允許的合成語音。
- 沒有聲音樣本的角色，每一顆鏡頭的聲音都可能不一樣。

## 4. 分鏡

```bash
python dramakit/storyboard.py P       # 印出鏡頭表、警告、影片點數估算；寫 storyboard.json
```

`storyboard.py` 幫你處理：
- 參考圖：說話的人、`act` 裡的 `@KEY`、`cast`、`props`，最後一定加上這場的場景，最多 6 張。
- `@KEY` 換成 `@圖片 N`，順序跟送出的 `images[]` 一致。
- 每個 `SHOT` 都寫地點（多參考影片的 SHOT 沒寫地點，背景會變成灰色攝影棚）。
- 有聲音樣本的鏡頭，參考圖描述裡的性別字眼會拿掉（描述的性別會蓋過樣本的音色）。

必看的警告：台詞太長（超過每秒 4 字）、參考圖超過 6 張、找不到的 key、沒有聲音樣本的說話角色、一張靜圖裡有兩個人。

**鏡頭類型怎麼選：**

| 鏡頭 | 用 | 說明 |
|---|---|---|
| 對白、反應、多人同框 | `M` 多參考影片 | 預設。角色、道具、場景的參考圖直接生成，說話的人用自己的聲音講台詞，嘴型一起生出來 |
| 長台詞、要逐字準確 | `LS` 對嘴 | 首幀靜圖＋你自己錄的這句（`lines/<id>.wav`） |
| 空景、外景、插入鏡頭 | `I2V` 圖生影片 | 首幀靜圖動起來，不講話 |
| 開門、轉場、A→B 的瞬間 | `K` 關鍵幀影片 | 首幀到尾幀，6／10／15 秒 |

## 5. 首幀靜圖（LS、I2V、K 鏡頭）

```bash
python dramakit/make_jobs.py P kf
python dramakit/aip_runner.py P/jobs/kf_jobs.json
python dramakit/qc/sheets.py stills P/review_kf.jpg P/kf
```

- 有角色的首幀從定裝圖做圖生圖，沒有角色的用文生圖。
- 對嘴的首幀要**已經在說話**（張嘴）：閉嘴、表情平靜的靜圖會發呆 3–5 秒才開始動嘴。表情也要跟這句的情緒一致。
- 一張靜圖只放一個人。兩人同框的靜圖很難做穩，改用多參考影片。

## 6. 試拍

整批送之前，每個角色先拍一顆有台詞的 `M` 鏡頭：

```bash
ONLY=S2_01,S2_02,S2_08 python dramakit/make_jobs.py P video
python dramakit/aip_runner.py P/jobs/video_jobs.json
```

聽：聲音像不像樣本、有沒有被描述帶成另一個性別、台詞有沒有講完。看：臉像不像定裝圖、場景對不對、有沒有冒出多的人。有問題就先改 `desc`、聲音樣本或台詞，再整批送。

## 7. 影片生成

```bash
python dramakit/make_jobs.py P video                                   # 印出任務數與點數估算
python dramakit/qc/sheets.py jobs P/review_jobs.jpg P/jobs/video_jobs.json   # 每個任務的參考圖、台詞、prompt
python dramakit/aip_runner.py P/jobs/video_jobs.json
```

把 `review_jobs.jpg` 和點數給決策者看，同意後才跑 runner。

- runner 一次一個任務（`AIP_MAX=1`），遇到 429 會等，不會一直重送。帳號上限較高再調大；只在離峰調大用 `AIP_MAX_UNTIL=09:00 AIP_MAX_AFTER=1`。
- 已經下載的檔案會跳過，要重做就把那個檔案移走（移到 `clips_rejected/`）。
- 失敗的任務自動退點，runner 最多重試 3 次。

## 8. 品管

```bash
python dramakit/qc/clips.py P          # 每支片能不能完整解碼、長度、有沒有聲音、片段內的換鏡點
python dramakit/speech.py P            # 每句台詞在片段的哪幾秒、有沒有講完、講的是不是劇本那句
python dramakit/qc/sheets.py strips P/review_clips.jpg P/clips/*.mp4
```

必看項目：
- `BROKEN`：只下載到一半。刪掉檔案重跑同一個任務檔，會用同一個任務重新下載，不用重生。
- `CUT?`：台詞一路講到片尾，可能被截掉。`TEXT?`：聽到的跟劇本不一樣（漏句、多句）。`SILENT?`：沒有聲音。這幾支都要用耳朵聽。
- 換臉、冒出多的人、背景變成灰色攝影棚、畫面出現亂碼字：每支每秒抽格看，剪輯時只用乾淨的秒數。
- `cuts`：多參考影片 8–10 秒內常自己換 2–4 次鏡，一支片可以當好幾鏡用。

處理方式見 [LESSONS.md](LESSONS.md)。

## 9. 剪輯

先產生一份照劇本順序、每鏡剪到台詞前後的初剪：

```bash
python dramakit/edl_draft.py P            # 印出 EDITS，貼進 project.py 再開始剪
python dramakit/edl_draft.py P main       # 看目前的剪輯展開成幾秒、總長多少
```

剪輯表的寫法：

```python
EDITS = {"main": dict(shots="""
    S2_01 auto flash intro=B         # src [in|auto] [dur] [flags]：一列一鏡，接在上一鏡後面
    S2_03 auto zoom
    ^S2_04 0.8 1.0 @-1.0             # 插入鏡頭：只換畫面，聲音照舊（反應鏡頭、L/J cut）
    S2_08 auto zoom sfx=hit          # 爽點：推近＋音效
    S2_10 auto freeze=1.6 end        # 卡點：定格＋「未完待續」
""")}
```

- `auto`（或只寫 id）：照 `speech.json` 剪到台詞前 0.15 秒、後 0.35 秒（`RENDER.pad`）；沒有台詞的鏡頭取前 2 秒（`RENDER.hold`）。
- 時間都是**片段自己的秒數**，整集的時間軸由每一列的長度接起來。
- 剪輯心法（鉤子、正反打、反應鏡頭、節奏、爽點、卡點）見 [EDITING.md](EDITING.md)。
- **NG 花絮**：重拍前把舊版移到 `clips/_takes/<id>_v1.mp4`，不要刪。`speech.py` 會順便辨識 `_takes` 裡的片段。NG 花絮獨立成一支影片：在 `EDITS` 另外寫一組 `"ng": dict(suffix="_NG", music=[("theme", None, None, -20)], shots="""clips/_takes/S4_03_v1 0.4 4.2 black label=第3集NG花絮""")`，再用 `render_ep.py P ng` 輸出 `<NAME>_NG.mp4`。正片照樣停在「未完待續」。如果 NG 的笑點是唸錯話（例如把舞台指示唸出來），加上 `heard`，字幕就會顯示實際聽到的內容。

## 10. 字幕、人物字卡、配樂、音效

- 字幕：台詞會依標點切成每段 ≤14 字（直式），時間照 `speech.json` 的逐字時間對上。字型、大小、位置在 `TYPO`。
- 人物字卡：`intro=KEY` 在那一列開頭出現「職稱＋名字」（`CAST[k]["title"]`、`name`）。
- 片名卡：`title` 在那一列出現劇名＋第幾集。`label=前情提要` 在左上角標一段字。
- 配樂：`MUSIC = [("tension", "S2_01", "S2_05", -18), ...]`，檔案放 `music/`。對白出現時配樂會自動壓低（ducking）。起訖可以寫列名（第一次出現的那一列）或秒數。配樂可以用 AutoIP 作曲（`/voice/song`，一首 30 點，`lyrics` 留空就是純音樂，長度 30–240 秒）；作曲跟影片共用任務名額。
- 音效：`sfx=hit` 在那一列開頭放 `sfx/hit.wav`。

調字幕時只渲字幕，不渲影片，幾秒就看得到結果：

```bash
python dramakit/qc/subprev.py P main P/subprev.jpg 0.9 2.5 9.0 21.0
```

要檢查的地方：字有沒有蓋到臉、人物字卡的位置、片名卡會不會擋到開場的衝突、卡點文字出現的時間。

## 11. 合成

```bash
python dramakit/render_ep.py P main
REUSE_BODY=1 python dramakit/render_ep.py P main        # 只改字幕、配樂、音效時，沿用已渲好的畫面
SUBST="S2_05:S2_02" python dramakit/render_ep.py P main # 還沒生好的鏡頭先拿別的頂著，看節奏
```

- 輸出 `P/out/<NAME>.mp4` 與 `.zh-TW.srt`。
- 聲音：每一列用自己片段的聲音（AutoIP 生成的台詞與音效），插入鏡頭不換聲音；配樂壓在對白下面，音效疊上去，整體標準化到 −16 LUFS（`RENDER.lufs`）。
- 合成時印出的 `WARN` 都要處理：`covers the start of`（插入鏡頭蓋住下一列的字卡或爽點）、`asks for ... -> the last frame is held`（片段不夠長、會定格）。
- 渲完抽格檢查：`python dramakit/qc/sheets.py video P/review_final.jpg P/out/<NAME>.mp4 1 5 10 20 30`

### 橫式版（16:9）

整部劇是橫式就把 `ASPECT = "16:9"`；直式劇另出一個橫式版，在剪輯加 `size`：

```python
EDITS["wide"] = dict(EDITS["main"], size=(1920, 1080), suffix="_wide", focus={"S2_08": 0.4})
```

`focus` 是每支素材的水平裁切中心（0 = 最左、1 = 最右，預設 0.5）。直式素材放進橫式畫面會被放大裁切，盡量只用在全劇本來就是橫式的情況。

## 12. 封面與上架

見 [PUBLISHING.md](PUBLISHING.md)：直式封面（`dramakit/thumbkit.py`，範例 `examples/demo/covers.py`）、標題、說明欄、hashtag、合集播放清單、AI 揭露。

## 13. 資源索引與瀏覽

劇一長，素材散在每一集的 `project.py`、`clips/`、`jobs/`、`speech.json`、`out/` 和系列資料夾的 `cast/`、`covers/`、`youtube/`。`python dramakit/library.py serve <系列資料夾>` 會把它們掃進 `<系列資料夾>/library.db`（SQLite），再開一個只給本機看的網頁（http://127.0.0.1:8765）：

- 總覽：依劇名分季，每一集的封面、長度、鏡數、估計點數、YouTube 公開時間（封面放 `covers/out/s2/ep01.jpg` 或 `covers/out/<集資料夾>.jpg`；還沒做封面就顯示成片的縮圖）
- 單集：正片和 NG 花絮、每一顆鏡頭的台詞／辨識結果／吻合度／片段、剪輯表、重拍的舊版
- 角色（每套造型和每個場景版本、聲音樣本）、場景、檔案（依類別）、任務與點數、YouTube 上架細節
- 搜尋台詞、角色、標題、檔名

只用 Python 標準函式庫和 ffprobe／ffmpeg。`serve` 開著時每 15 秒檢查一次，檔案有變就在背景重建（`index` 只建不開網頁，`--no-index` 啟動時不先建）；影片長度和縮圖會快取，第二次只要幾秒。點數是照任務檔估的，重拍的鏡頭只算最後一次。也可以直接用任何 SQLite 工具查 `library.db`。

---

## 成本參考

以下是 2026-10-27 `GET /api/v1/pricing` 的點數，實際以當下的價目為準。`make_jobs.py`、`storyboard.py`、`qc/sheets.py jobs` 都照這張表估算（`dramakit/common.py` 的 `PRICE`）。

| 任務 | 點數 |
|---|---|
| 文生圖 | 10（`v3`、standard）；`v4` 20 |
| 圖生圖 | 15 |
| 對嘴 2.0（≤31 秒） | 50；對嘴 3.0 480p 50、768p 75（音檔 ≤20 秒） |
| 圖生影片 768p | 每秒 15（5 秒 75） |
| 多參考影片 768p | 5 秒 80、6 秒 115、7 秒 145、8 秒 170、9 秒 225、10 秒 265 |
| 多參考影片 2k | 5 秒 95、6 秒 115、8 秒 150、10 秒 195 |
| 關鍵幀影片 | 每秒 8（6 秒 48） |
| 影片修復（去字幕） | 每 8 秒 30 |
| 語音克隆 | 50 |

- 多參考影片 768p 的價格不是照秒數等比例：6 秒以上一秒貴很多。台詞放得進 5 秒就用 5 秒。
- 這是送出前的估計，實際花費用 `dramakit/credits.py P/jobs` 稽核。

示範專案（1 分鐘、11 鏡）：影片約 870 點、首幀約 50 點；定裝與場景整部劇共用，約 60 點。重拍另計。要省點數：
- 先試拍，確定聲音與長相再整批送。
- 反應鏡頭和插入鏡頭用 5 秒就好；一支多參考影片常可以剪出好幾鏡。
- 前情提要直接用上一集的片段（`../s1e01_x/clips/S2_08`），不用重生。
