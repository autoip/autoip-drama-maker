# 更新紀錄

中文 | [English](../en/RELEASE_NOTES.md)

## 0.7.2（2026-10-29）：本機 GPU 超分＋補幀（選用）

- **`enhance.py`**（新）：照 autoip-drama-maker 的做法，用 NVIDIA Video Super Resolution 放大 2 倍、Video Frame Generation 補幀到 60 fps，把剪輯用到的片段存成 `clips_hd/<id>.mp4`（只有畫面）。參數記在 `.json`，片段比副本新或參數改了就重做；`--watch` 可以跟 runner 同時跑；`ONLY=` 只做指定片段。需要 RTX 40／50 系列、CUDA 版 PyTorch、PyAV、`nvidia-vfx`。
- **`render_mv.py`**：剪輯可以帶 `render=dict(...)` 蓋過 `RENDER`；`enhance=True` 時改讀 `clips_hd/` 的副本（沒有的照用原片段並提醒），`crop=`、`delogo=` 的像素值自動乘倍數。不設就跟以前一樣。
- **`common.hd_path()`**、**`gpu_check.py`** 多一行 `hd`。
- **GPU_ENHANCE.md**：「搬到 mv-maker 要注意的」改成實際用法，加上一支工筆畫風 MV 的實測：直式版明顯變清楚、橫式版幾乎看不出，但決策者覺得太利、少了畫感，成品用原版。這是選用功能，預設不跑。

## 0.7.1（2026-10-29）：離峰半價時段送任務

- **`aip_runner.py`**：`AIP_OFFPEAK=1` 只在 AutoIP 的離峰時段送新任務（2026-10-30 起，用 API 金鑰在 03:00–09:00 台灣時間送出的任務半價）。時段和是否啟用讀 `GET /pricing` 的 `off_peak`，讀不到就用公告的 03:00–09:00 UTC+8；結束前 2 分鐘停送，因為價格看送出時間。時段外照常輪詢、下載在跑的任務，等下一個時段。沒設又不在時段內時只印一行提示。送出時記下實際扣的點數和是否離峰到 `.state`，有打折的標 `(off-peak)`。
- **`common.estimate`**：`off_peak=True` 算離峰價（一半、無條件進位、最少 1 點），跟 `/pricing` 的 `off_peak_credits` 一致。
- **`library.py`**：任務點數優先用 `.state` 記的實際扣點，離峰的任務不會算成原價。
- **`feature_jobs.py`**：多參考影片的參考圖每張上限 10 MB，hd_4k 定裝圖（約 17 MB）會被 422 退回；超過 9.5 MB 的自動另存 JPEG（寬最多 2560）到 `jobs/img/` 送出。
- SETUP、WORKFLOW（成本表加離峰欄）、README、skill 同步。
- **CONTRIBUTING.md**（新，中英文）：程式與文件規範、送 PR、回報問題，以及送出前的去識別化：哪些東西絕對不能上傳（金鑰、真人影像與聲音、個資、帳號識別、本機路徑、未公開的作品）、遮金鑰的指令、上傳前的 grep 自我檢查、不小心傳上去時先作廢金鑰。`.github/` 加上 PR 範本（去識別化清單）和回報問題範本（公開頁面警告）。

## 0.7.0（2026-10-28）：資源庫網頁

- **`library.py`**（新）：把一整個系列索引進 `<系列資料夾>/library.db`（SQLite）：每一集（曲風、各版本成片與長度、封面、對嘴佔比、估計點數、進度）、每一段素材（對嘴、樂手、B-roll、關鍵幀、多參考：靜圖或參考圖、影片、提示詞、對到的歌詞、用在哪個版本幾次、舊版與候選）、歌詞時間、剪輯表（每列長度、重複用的素材）、角色與參考圖、依類別分的檔案、AutoIP 任務與估計點數、`youtube.json` 的上傳紀錄。`serve` 在 127.0.0.1 開一個瀏覽網頁（總覽、單集、素材、角色、檔案、任務與點數、YouTube、搜尋），影片有縮圖、點了才載入、可以拖拉進度；開著時每 15 秒檢查一次，檔案有變就在背景重建，建在副本上再換上去。只用標準函式庫和 ffprobe／ffmpeg；影片長度與縮圖快取，重建幾秒。預設 port 8770，被占用就換下一個（Windows 上兩個伺服器可以綁同一個 port 而不報錯，所以那裡關掉 SO_REUSEADDR）。OAuth 憑證和 token 不索引也不送出。
- **`common.estimate`**：照 `GET /pricing` 的價目估一個任務的點數（文生圖／圖生圖各模式、多角度、圖生影片與多參考的畫質 × 秒數、關鍵幀每秒、對嘴引擎與畫質、修復每 8 秒一段）。
- README、WORKFLOW、skill 加上資源庫；`.gitignore` 加上 `library.db`、`library.db.tmp`、`.library/`。

## 0.6.1（2026-10-27）：選用的 NVIDIA 顯卡加速，CPU 仍是預設

- **`gpu_check.py`**（新）：看這台機器的 NVIDIA 顯卡能接手哪些步驟，印出要加的環境變數或要裝的套件。沒有顯卡就說全部跑 CPU。
- **`common.venc`**：所有影片編碼走同一組設定。預設 x264，跟以前一樣；`VENC=nvenc` 改用顯卡（h264_nvenc）。偵測到能用的 NVENC 但沒加 `VENC` 時只印提示。
- **`render_mv.py`**：段落、片頭片尾卡、成品都走 `venc`；`VENC=nvenc` 時同時編 4 段（`JOBS` 可改，CPU 預設 1 段）。實測 RTX 5060 Ti：190 秒的全片 50 秒算完，CPU 要 2 分 45 秒，聲音完全一樣；成品 VMAF 99.2 對 99.3。**`matte_video.py`** 的輸出也走 `venc`。
- **`asr_words.py`**：`ASR_DEVICE=cuda` 改用 int8_float16（RTX 5060 Ti 上 60 秒人聲 1.0 秒，CPU 10.9 秒）；`ASR_COMPUTE` 可改。偵測到顯卡但沒加 `ASR_DEVICE` 時只印提示。
- 文件：SETUP 的顯卡段落改成一張表（每一步怎麼開、實測速度、CUDA 版 PyTorch 給 Demucs），LESSONS 加 NVENC cq 要配 `-maxrate`，WORKFLOW、skill、requirements 同步。

## 0.6.0（2026-10-25）：多參考影片、關鍵幀影片的任務檔，畫面上標出 AutoIP 功能

- **`feature_jobs.py`**（新）：從 `project.py` 的 `I2V`、`KEYFRAME`、`MULTI` 產生圖生影片 3.0、關鍵幀影片（2frame）、多參考影片 3.0 的任務檔，給一支 MV 同時展示多種 AutoIP 功能用。打鬥、多人戲走多參考，A→B 的瞬間和轉場走關鍵幀，圖生影片只留給氣氛鏡頭。參考圖依序找 `refs/`、`refs/angles/`（角色多角度）、`kf/`，描述從 `MULTI`、`REFS`、`REF_DESC` 拿。
- **`render_mv.py`**：`project.FEATURE`（素材 id 開頭 → 功能名）讓換功能的那一鏡在右上角淡入「AutoIP｜功能名」約 2 秒（AutoIP 橘色，46 px）；剪輯加 `labels=False` 就不畫。
- **`epic.py`**：`TYPO.rewrite` 可以有第三個欄位，用同一個顏色把新字寫在劃掉那段的上方。
- **`bokeh_still.py`**：`CROWN_KEY=1` 在素色背景上用顏色差留住頭頂以上的長裝飾（翎子、高冠），人像分割會切掉它們；`SAVE_CROWN=1` 另存那塊遮罩。**`matte_video.py`**：`KEEP=遮罩` 把它加回每一格，跟著臉移動。
- **`aip_runner.py`**：一個任務有多個輸出（角色多角度）時全部下載：`out`、`out_1`、`out_2`……
- **`storyboard.py`**：`project.EXTRA_CAPS` 讓不在 `BROLL`／`BAND`／`LS_SCENES` 的素材（關鍵幀、多參考）也能列進段落的鏡頭。
- LESSONS 新增「多參考影片、關鍵幀影片」：SHOT 沒寫地點那一鏡背景變成參考圖的灰色攝影棚（11 段有 4 段；每鏡寫地點重拍 3 段都對）；精確的道具動作（斬繩、拋槍）做不出來；一段 8–10 秒會自己換 2–4 次鏡；關鍵幀首尾幀是不同場景時約在 65% 處硬切或溶接（10 段有 8 段）。另外：戲曲畫風的圖生影片 2–3 秒後走進新角色（14 段有 4 段）；對嘴寫了「不要推近」3 段仍有 1 段 1 秒就跳特寫；直式 `focus` 是裁切窗可移動範圍的比例，不是畫面座標；戲偶的臉 `qc/focus.py` 抓不到；手機上標籤要夠大；片尾片名會蓋住最後一鏡的臉。PROJECT_FORMAT、WORKFLOW、README、skill 同步。

## 0.5.3（2026-10-24）：直式取景可以每鏡各設、一支木版畫 MV 的實際數字

- **`render_mv.py`**：`focus` 也接受 `"素材 id@列時間"` 的鍵，同一段素材的某一鏡可以有自己的直式裁切中心。一段對嘴裡歌手從畫面中間走到左三分之一再走回來，單一個中心會讓 Shorts 有幾鏡切到臉。
- LESSONS：兩倍速的節拍減半時選錯那一半，吸附節拍的切點全落在反拍（選小鼓強起音落的那一半）；共用前綴寫了「…動畫 MV」會被燒成字幕（67 段有 5 段）；「整個畫面維持＿＿的配色」試拍時擋住了配色漂移，整批 42 段仍有 2 段漂掉；首尾同一張圖能救一直拉遠，但另外 5 段修補有 3 段在中間塞進過場的東西（改用關鍵影格慢推）；對嘴會壞成背後疊一張巨大的同一張臉；氣音多的歌 `mouth.py` 的 OFF? 不可信；下載回來的片段要全部解碼檢查，有一段只下載到一半。PROJECT_FORMAT 加上每鏡的 `focus` 鍵。

## 0.5.2（2026-10-23）：合唱分軌、成片音訊修正、圖生影片的鏡頭提示

- **`split_voices.py`**：`project.VOICE_BOTH` 標出兩人一起唱的時段，兩條人聲軌都保留這幾段，合唱時兩個人的對嘴都會開口。
- **`render_mv.py`**：每一段都加上同一組色彩標記（bt709／tv）。素材有的有標記、有的沒有（例如 `matte_video.py` 的輸出）時，最後一次 ffmpeg 會在換段時重建整個濾鏡圖，歌曲的 `atrim` 重新起算，成片少掉約 2 秒音訊。
- LESSONS：動作提示寫了鏡頭移動或畫面外的東西，模型就自己生出新場景（66 段有 4 段），改成「鏡頭固定不動」＋只動畫面裡已有的東西；一直往後拉的鏡頭，把同一張靜圖同時當 `first_frame` 和 `last_frame` 就鎖住構圖。PROJECT_FORMAT 加上 `VOICE_BOTH`。

## 0.5.1（2026-10-22）：整批的實際數字、離峰時段

- **`aip_runner.py`**：`AIP_MAX_UNTIL=09:00 AIP_MAX_AFTER=1`，只在離峰時段同時跑多個任務，到時間自己改回 1，已經在跑的照常跑完。
- LESSONS 補上一整支水墨 MV 的數字：12 段對嘴有 4 段背景被換成照片、1 段多出寫實木柱；`matte_video.py` 在淺色畫紙背景上會切掉白銀頭飾（3 段都是），這種改用另一版；水墨圖生影片會把像歌詞的動作提示寫成題字（2 次都出字）；60 段裡 2 段後段變成彩色寫實、6 段後段冒出彩色；改了 `BROLL` 提示詞要先重跑 `storyboard.py`。SETUP、skill 加上離峰時段的用法。

## 0.5.0（2026-10-22）：畫出來的畫風、GPU 語音辨識

- **`matte_video.py`**（新）：對嘴片段逐格去背，把人貼回靜止的底圖。水墨畫風的試拍裡，對嘴 3.0 在 0.8 秒內把背景重畫成寫實庭園；逐格貼回後整段留在畫裡，嘴型是原片的。遮罩跨格平滑，不閃邊；20 秒約 40 秒，只用 CPU。
- **`bokeh_still.py`**：`BG=圖檔` 把人物貼到另一張圖上（填滿裁切，照樣用 `BLUR` 模糊）。用來做「真人站在畫裡」的對嘴靜圖：圖生圖從半寫實定裝照出發畫不出水墨背景。
- **`asr_words.py`**：`ASR_DEVICE=cuda` 改用 NVIDIA 顯卡（int8），GTX 1060 比 16 執行緒 CPU 快約 2.3 倍。Windows 會自動找到 pip 裝的 cuBLAS、cuDNN DLL。
- **`epic.py`**：`TYPO.rewrite` 片名前的「改寫」卡：一句舊的句子，一筆朱紅劃掉其中一段，再燒出片名。
- 文件同步：LESSONS（水墨要用文生圖、v3 自己蓋印章、圖生圖背景不會變畫風、對嘴可能把畫風背景重畫成照片、歌詞 prompt 讓 ASR 猜下一句、GPU 辨識、Git Bash 的 `ps` 看不到 runner）、SETUP（選用的 GPU 辨識；解碼與 NVENC 的實測）、WORKFLOW（畫風底圖、試拍、逐格貼回）、PROJECT_FORMAT（`rewrite`）、README、skill。

## 0.4.3（2026-10-20）：整理 YouTube 播放清單

- **`youtube_playlists.py`**：列出每個播放清單和不在任何清單的影片；照指定順序、上傳日期或標題排序；加入、移除影片（`--dead` 連已刪除影片的空位一起拿掉）；改清單名稱與說明；刪除空清單；`replace` 一次改很多支影片說明欄裡的同一段字（整段 snippet 原樣送回，標籤不會被清掉）。會寫入的指令先印計畫，加 `--apply` 才寫；`YT_CHANNEL_ID` 鎖定頻道；寫入後等重讀看得到變化才回報。
- **`youtube_upload.py`**：加進播放清單後重讀確認。登入程式移到 `youtube_api.py`，兩支工具共用。
- 文件同步：PUBLISHING（播放清單整理）、LESSONS（上架：手動排序、讀取延遲、snippet 要整段送回）、README、WORKFLOW、skill。

## 0.4.2（2026-10-19）：推近測試的完整結果

- **更正 0.4.1**：20 段 A/B 測試做完，「具體的鏡頭指示能降低推近」不成立。鏡頭指示讓 2 秒內跳特寫消失（0/16），但全程穩定的也從 14/29 降到 2/16，平均可用秒數比舊寫法少；推近基本上是隨機的。LESSONS「對嘴」、PROJECT_FORMAT、WORKFLOW、skill 改成：提示詞照舊，重要句子做兩版，用 `zoom.py` 挑。
- **`qc/zoom.py`** 多偵測鏡頭往後拉（臉縮到 0.75 倍以下或找不到臉，標 `OUT`、`out@`）。

## 0.4.1（2026-10-19）：對嘴推近檢查

- **`qc/zoom.py`**：每 2 秒量對嘴片段的臉部大小，標出有沒有自己推成大特寫（`ok`／`LATE`／`PUSH`／`JUMP`）、從第幾秒開始。
- LESSONS「對嘴」：29 段實測與 A/B 測試的初步結果：具體的鏡頭指示能降低推近，後面接戲劇化的情緒詞會破功，切短音檔沒用，寬靜圖可以兜底。WORKFLOW 品管步驟、PROJECT_FORMAT 的 `motion_prompt` 寫法同步。

## 0.4.0（2026-10-19）：自動上傳 YouTube

- **`youtube_upload.py`**：讀 `YouTube_SEO.txt`，用 YouTube Data API 上傳成片、縮圖、字幕，填好標題、說明欄、章節、標籤、類別、語言，設好「不是為兒童打造」和「經過修改或合成的內容」，可加進播放清單。預設傳成私人，在 Studio 看過再公開；`--publish-at` 排程，`--update` 改了文案再重寫。
- **送出前先檢查**：標題 ≤ 100 字、說明欄 ≤ 5,000 bytes（中文約 1,600 字）、標籤 ≤ 500 字（逗號、空格標籤的引號都算）、章節規則。`--dry-run` 只檢查不上傳。
- **不傳錯、不重傳**：登入後印出頻道名稱，`YT_CHANNEL_ID` 鎖定頻道（一個 Google 帳號可以有好幾個頻道）；上傳前比對頻道最近 50 支的《片名》，手動傳過的也擋得到；已上傳的 ID 記在 `youtube.json`。
- **Shorts**：完整版傳完再傳 Shorts，說明欄的 `{full}` 自動換成完整版連結。Shorts 縮圖不經 API（YouTube 會存成 16:9，Shorts 架不採用），腳本提醒到 Studio 上傳。
- `YouTube_SEO.txt` 範本加上「說明欄（API）」「Shorts 說明欄」「置頂留言」三段。
- **對嘴任務**：`project.LS_FIELDS` 指定對嘴的額外參數（例如 `engine=h3`、`resolution=768p`）；超過 10 MB 的靜圖（hd_4k 約 15 MB，會被退件）自動另存成 2560 寬的 JPEG 送出。
- **`bokeh_still.py`**：白色毛領、淺色衣服常被當成背景挖掉一塊。現在會補滿人物圍起來的洞、丟掉跟人物不相連的碎塊；`SOLID_TORSO=1` 給手上沒拿東西的半身像，下巴以下每一列從最左補到最右。
- 文件同步：PUBLISHING（一次性的 Google Cloud 設定、用法、限制、還要手動做的事）、LESSONS（上架）、WORKFLOW、README、skill。`requirements.txt` 加上選用的 `google-api-python-client`、`google-auth-oauthlib`。

## 0.3.0（2026-10-17）：一次規劃一整季

- **系列企劃框架**（`docs/zh-TW/SERIES_PLANNING.md`）：一個系列要有的公式（一句話、主軸、3–5 個固定錨點、同一種歌曲結構、同一套包裝、每集企劃卡），其他全部自由。每一步都附可以挑的選項：七種主軸、四種歌曲結構、五層錨點。另有目錄命名規則（`s{季}e{集}_{歌名}`）、每一集的製作順序和上架前檢查表。
- **空白系列範本**（`examples/series_template/`）：`research.md`、`style.md`，以及每一集的歌詞骨架、角色定案、上架文案。
- **`bokeh_still.py`**：對嘴靜圖背景虛化。清楚的畫面背景會讓模型把歌詞寫成畫裡的直排字，restore 去不掉；背景虛化後字會落到底部，restore 去得掉。人物先 inpaint 掉再模糊，不會有白邊。另外要下載一個分割模型（見 `models/README.md`）。
- **字幕**：連續兩句直排字不再疊在同一側；直式版的直排字更貼邊，不壓臉（`epic.py`）。
- 文件同步：LESSONS（背景與亂碼字、對嘴提示詞只寫情緒、限制句會被畫出來、切點吸附造成的 `before clip start`）、README、WORKFLOW、skill（新增系列流程）。

## 0.2.0（2026-10-17）：對嘴字幕有解了

做第五集《馬嵬》時，15 支對嘴影片全部被模型燒進亂碼字幕（白字、金字、底部、側邊、直排都有）。以前只能裁切畫面或換鏡頭閃過去，兩種都傷畫質、傷表演。這版把流程改掉：

- **去字幕改用 AutoIP 的影片修復 API。** `POST /videos/restore`，`source_video` ＋ `operations[]=subtitle`（另有 `watermark` 去水印、`upscale` 銳化），每 8 秒一段 30 點。實測整排字抹乾淨、衣領線條接得起來，臉和解析度都不動。對嘴片段不再裁切、不再為了字幕換鏡頭。
- **對嘴 3.0（`engine=h3`）。** 不燒字、嘴型和表情更準（嘶吼真的會張大嘴），但輸出 864×480。文件說明何時值得用。
- **對嘴靜圖定案：定裝圖直接裁。** 半寫實定裝圖裁成 16:9、每個場景不同放大倍率，不去背、不貼空景、不圖生圖。去背貼空景（斷手、白邊）、文生圖半身（臉跑掉）、換臉，這些彎路都記在 LESSONS 裡。
- **字幕 `TYPO.hold`。** 指定句子在最後一個字之後幾秒就收掉，給喊聲之後接死寂的段落用。
- **合成 `EDITS[mode]["crop"]`。** 直式版和橫式版各裁各的。
- 文件同步：LESSONS（對嘴字幕、靜圖、聲部要用耳朵確認、嘶吼提示詞要寫嘴怎麼動）、PROJECT_FORMAT、WORKFLOW、skill。

系列進度：《國風淒美對唱》第一集《洛川》已上架，第二到四集完成，第五集《馬嵬》（唐玄宗 × 楊貴妃，暗黑 K-pop 抒情 × metalcore）製作中。

## 0.1.0（2026-10-15）

首次公開：一個 `project.py` 就是一支 MV。分鏡、AutoIP 對嘴與圖生影片、情緒驅動的卡拍剪輯、動態字幕、合成、縮圖與上架文案。
