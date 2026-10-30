# 上架：縮圖、Shorts 縮圖、YouTube SEO、社群貼文

中文 | [English](../../en/mv/PUBLISHING.md)

## 縮圖（A/B/C 測試）

**素材來源：**
- 直接從成片抓畫面，不必另外花點數生成：`ffmpeg -ss <秒> -i out/xxx.mp4 -frames:v 1 thumb_src/<id>_<秒>.png`
- 用 `mv/thumbkit.py` 組版，範例見 `examples/mv/demo/thumbs.py`。

**三個方向各做一張，上傳到 YouTube Studio 的「測試與比較」：**

| 版本 | 方向 | 版型 |
|---|---|---|
| A | 音樂性 | 兩位主唱以斜切血線對峙（`thumbkit.split`），片名置底，下方英文小字 |
| B | 梗 | 歌詞裡最狠的一句：前半句劃掉，後半句接反轉 |
| C | 群像／世界觀 | 樂團在場景中，片名置底，左上角斜標籤寫曲風 |

**規則：**
- 片名不可蓋住臉。
- 縮到 320 px 寬仍要讀得出來。
- 一張只講一件事。
- 字型與成片字幕一致。

## Shorts 縮圖

Shorts 在動態裡會直接播放，觀眾看不到縮圖。縮圖出現在首頁的 Shorts 架、搜尋結果和頻道的 Shorts 分頁。

**素材與尺寸：**
- 輸出 1080×1920（9:16）的 JPG。
- 從 `clips/<id>.mp4` 抓畫面，不要從直式成片抓，因為成片已經燒進歌詞字幕：`ffmpeg -ss <秒> -i clips/<id>.mp4 -frames:v 1 thumb_src/<id>_<秒>.png`
- 素材大多是 16:9，裁成直式約放大 2.5 倍。人物挑特寫，或兩人靠在一起的鏡頭。全身遠景縮小後看不清臉。

**組版：** `thumbkit` 的函式在呼叫時才讀畫布尺寸，所以先改尺寸，就能沿用同一套函式。`frame` 的水平裁切中心可以直接沿用直式版剪輯的 `focus`。

```python
tk.W, tk.H = 1080, 1920
im = tk.shade(tk.frame(src("<id>_<秒>.png"), 1.0, 0.5, 0.5), "top", strength=150, width=0.22)
tk.title(im, (540, 150), "片名", 200, 0.12)
tk.badge(im)
tk.grain(im).save(os.path.join(out, "shorts_A_duet.jpg"), quality=95)
```

**三個方向沿用橫式，改成上下排：**

| 版本 | 直式版型 |
|---|---|
| A | 兩位主角靠在一起的同一個鏡頭，因為直式寬度放不下左右對切。片名放在頭頂上方的空處。 |
| B | 臉放中段，梗句疊在頭頂上方，片名放在下巴下方。 |
| C | 場景或畫卷。片名可以直排，古典題材再加一枚印章。 |

**規則（橫式的規則照樣適用）：**
- 關鍵文字放在畫面上方四分之三，也就是 y < 1440。手機首頁的 Shorts 架會把影片標題疊在縮圖下緣。
- 縮到 180 px 寬仍要讀得出來，這是手機 Shorts 架上的大小。
- 縮圖和 Shorts 標題用同一個鉤子，例如標題用梗句就配 B。

**上傳：**
- 自訂縮圖只能在電腦版 YouTube Studio 上傳：「內容」→「Shorts」→ 影片的編輯圖示 →「縮圖」→「上傳檔案」→ 儲存。帳號要先完成驗證。
- 手機 App 只能從影片裡選一格畫面當縮圖。
- 「測試與比較」不支援 Shorts。三張並排縮小比較，挑一張上傳。

## 標題

給 2–3 個候選，再另外準備一個 Shorts 標題。

| 方向 | 公式 |
|---|---|
| 音樂性 | 【片名】語言＋曲風 MV｜樂團/角色 賣點 × 賣點・English Genre |
| 梗 | 最狠的一句歌詞！《片名》曲風 Official MV |
| 情緒 | 一句有畫面的歌詞｜《片名》English Genre MV |
| Shorts | 副歌第一句！曲風 #shorts |

## 說明欄結構

1. 兩三行中文介紹（世界觀 + 賣點）+ 一段英文介紹
2. 觀看建議（耳機、最高畫質）、訂閱提醒
3. **章節**：`0:00 序曲｜…`。時間取自完整版的段落起點，要扣掉 `cut`、加上片頭卡秒數。第一個章節必須是 0:00。
4. 樂團陣容／角色
5. 完整歌詞（保留作詞者的標音）
6. 聲明：
   - 諷刺作品要加「人物與場景皆為虛構，不指涉任何特定政黨或個人」。
   - 使用 AI 生成影像的，標明製作工具。
7. 5–8 個 hashtag

## 標籤

- 中英混合，約 300–400 字。
- 依序排列：片名 → 語言＋曲風 → 英文曲風 → 角色 → 主題 → 技術（AI MV、kinetic typography）。

## 上架設定檢查表

- [ ] 上傳 `.srt` 字幕：畫面上已有動態字幕，CC 預設關閉即可。
- [ ] 「經過修改或合成的內容」：寫實 AI 人像選「是」。
- [ ] 觀眾：不是為兒童打造。
- [ ] 縮圖 A/B/C 測試。
- [ ] Shorts 上傳直式版（WORKFLOW.md「直式版」）：橫式影片不會被歸到 Shorts。
- [ ] Shorts 縮圖：在電腦版 YouTube Studio 上傳 9:16 的 `thumbnails/shorts_*.jpg`，三張挑一張（見上方「Shorts 縮圖」）。
- [ ] 片尾畫面：訂閱 + 播放清單（片尾推廣卡的秒數就是預留給這個用的）。
- [ ] 標題、縮圖、標籤沒有真實人物或政黨名稱。

用 `mv/youtube_upload.py` 上傳時，字幕、「經過修改或合成的內容」、觀眾、完整版的縮圖會自動設好，見下一節。

## 自動上傳（YouTube Data API）

`mv/youtube_upload.py` 讀 `YouTube_SEO.txt`，把成片、縮圖、字幕傳上 YouTube，填好標題、說明欄、標籤、類別（音樂）、語言和上架設定。預設傳成**私人**，在 Studio 看過再公開。

**一次性設定**
1. 在 [Google Cloud Console](https://console.cloud.google.com/) 建一個專案，到「API 和服務」→「程式庫」啟用 **YouTube Data API v3**。
2. 「OAuth 同意畫面」：使用者類型選「外部」，填應用程式名稱和聯絡信箱，把自己的 Google 帳號加進測試使用者。設定完按「發布應用程式」，改成**正式版**。停在「測試中」的話，登入每 7 天就失效。正式版不送審也能自己用，登入時會看到「Google 尚未驗證這個應用程式」，按「進階」→「前往」即可。
3. 「憑證」→「建立憑證」→「OAuth 用戶端 ID」，應用程式類型選「電腦版應用程式」，下載 JSON，存成 `~/.config/dreamfab/youtube_client_secret.json`（或用環境變數 `YT_CLIENT_SECRET` 指到別處）。不要放進 repo。
4. 安裝套件：`pip install google-api-python-client google-auth-oauthlib`。
5. 先跑 `python mv/youtube_upload.py --whoami` 登入：用頻道的 Google 帳號登入並允許，最後會印出頻道名稱。登入憑證存在同一個資料夾的 `youtube_token.json`。
   - **一個 Google 帳號底下有好幾個頻道（品牌帳戶）時，登入途中會問要用哪一個，要選對。** 選錯就刪掉 `youtube_token.json` 重新登入。
   - 確認之後把頻道 ID 設成環境變數 `YT_CHANNEL_ID`，登錯頻道時腳本會拒絕上傳。
   - 從背景執行時瀏覽器可能不會自己打開：複製腳本印出的網址，在**同一台電腦**的瀏覽器打開，直到頁面顯示「The authentication flow has completed」。
6. 頻道要先完成電話驗證，才能設自訂縮圖。

**用法**
```
python mv/youtube_upload.py PROJECT_DIR --dry-run                 # 只檢查、列出要送的內容，不登入、不上傳
python mv/youtube_upload.py PROJECT_DIR --title A --playlist "播放清單名稱"
python mv/youtube_upload.py PROJECT_DIR --shorts --title B        # 完整版傳完再傳 Shorts
python mv/youtube_upload.py PROJECT_DIR --update                  # 改了 SEO 檔：重寫標題、說明欄、標籤、設定和縮圖
```
- 排程公開：`--publish-at 2026-10-25T20:00:00+08:00`，時間到之前都是私人。
- 已上傳的影片 ID 和頻道記在 `PROJECT_DIR/youtube.json`，重跑不會重複上傳，也不會傳到別的頻道。
- 上傳前會查頻道最近 50 支影片：標題裡有同一個《片名》、而且同樣是（或同樣不是）Shorts，就停下來。在 Studio 手動傳過的也擋得到：把那支的 ID 記進 `youtube.json`，或加 `--allow-duplicate`。
- `--title` 選標題，也選縮圖：`thumbnails/thumb_<字母>_*.jpg`。

**`YouTube_SEO.txt` 裡給腳本讀的區段**（用 `==== 區段標題 ====` 分段，看標題裡有沒有這些字）

| 區段標題含 | 內容 |
|---|---|
| 標題 | `A. …`、`B. …`；提到 Shorts 或「直式」的那一行（同一行冒號後面，或下一行）是 Shorts 標題 |
| 說明欄＋API | API 用的說明欄；沒有就用「說明欄」 |
| Shorts＋說明欄 | Shorts 的說明欄；裡面的 `{full}` 會換成完整版的連結 |
| 標籤 | 逗號分隔 |

**API 的限制**（送出前腳本會先檢查）
- 標題 ≤ 100 字，不能有 `<` `>`。
- 說明欄 ≤ **5,000 bytes**，不是 5,000 字。中文一個字 3 bytes，大約 1,600 字就滿了。歌詞和章節留著，考據寫短，完整版放在置頂留言。
- 標籤合計 ≤ 500 字：逗號也算，含空格的標籤要加算兩個引號。
- 章節：第一個是 0:00，至少 3 個，每段 ≥ 10 秒。
- 配額：每天 10,000 單位，另外每天最多上傳 100 支。一支影片連縮圖、字幕、播放清單約 500 單位（字幕就占 400）。API 本身不收費。

**API 做不到，還是要在 Studio 手動做的**
- 片尾畫面、資訊卡、置頂留言、縮圖「測試與比較」。
- Shorts 的自訂縮圖：API 設的縮圖會被存成 16:9（9:16 的圖放中間、左右補模糊），Shorts 架不採用。所以腳本預設不設 Shorts 縮圖，只提醒你到電腦版 Studio 上傳 `thumbnails/shorts_<字母>_*.jpg`（見上方「Shorts 縮圖」）。

## 播放清單整理（YouTube Data API）

`dreamfab/youtube_playlists.py` 用同一組登入（見上一節）整理頻道的播放清單，也能一次改很多支影片的說明欄。會寫入的指令都先印出計畫、不改任何東西，加 `--apply` 才真的寫入；開頭會印出頻道名稱，設了 `YT_CHANNEL_ID` 就只動那個頻道。

```
python dreamfab/youtube_playlists.py list                                    # 每個清單有哪些影片，以及不在任何清單的影片（唯讀）
python dreamfab/youtube_playlists.py sort "第一季" ID1 ID2 ID3 --apply        # 照這個順序排（清單裡每一支都要列到）
python dreamfab/youtube_playlists.py sort "第一季" --by oldest --apply         # 或照上傳日期（oldest / newest）、標題排
python dreamfab/youtube_playlists.py add "Shorts" ID --apply
python dreamfab/youtube_playlists.py remove "總表" ID --dead --apply           # --dead：連「Deleted video」「Private video」的空位一起拿掉
python dreamfab/youtube_playlists.py edit "第一季" --title "新名稱" --description-file 說明.txt --apply
python dreamfab/youtube_playlists.py delete "舊清單" --apply                   # 只刪空清單（或只剩已刪除影片的），否則要 --force
python dreamfab/youtube_playlists.py replace "舊系列名" "新系列名" --playlist "第二季" --apply   # 改很多支影片說明欄裡的同一段字
```
- 清單用 ID（`PL…`）或完整名稱指定；影片用 ID 或連結（`youtu.be/…`、`watch?v=…`、`shorts/…`）。
- **排序前，先把清單的預設排序方式改成「手動」**（在 YouTube 打開清單 → ⋮ → 播放清單設定）。不是手動的清單，API 不接受位置，而這個設定 API 改不了。
- 寫入之後重讀，要過幾秒才看得到變化。腳本會等到看得到（最多 45 秒）才回報，不會照舊資料重複加入。
- `replace` 會把整段 snippet（標題、標籤、類別、語言）原樣送回，只換說明欄：`videos.update` 沒給的欄位會被清空，標籤也是。
- 配額：讀取 1 單位，每次寫入 50 單位（排序是每支影片一次）。
- `youtube_upload.py` 加進播放清單後也會重讀確認，沒看到就提醒你到 Studio 檢查。

## 社群貼文（X / Threads）

| 篇 | 內容 |
|---|---|
| 主貼文 | 一句梗 + 一句介紹 + 連結 + 3 個 hashtag，附縮圖 B |
| 短片貼文 | 直接上傳短版影片（原生影片觸及通常比連結高；X 免費帳號上限約 2 分 20 秒）+ 副歌兩句 |
| 英文版 | 隔天早上發，對準美東晚上 |
| 串文 | 3 則：作品介紹 → 一段歌詞 → 連結與前作 |

- 每篇 hashtag 3–4 個。
- 不 tag 真實政黨或政治人物。
