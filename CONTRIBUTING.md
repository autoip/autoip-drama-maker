# 貢獻原始碼

中文 | [English](CONTRIBUTING.en.md)

歡迎修 bug、補文件、加功能，或分享你實測的數字。

這個 repo 是公開的，而做短劇、MV 的人手上一定有不能公開的東西：劇本、歌詞、歌曲、角色、聲音樣本、真人照片、API key、YouTube 憑證。送出的每一行都會被所有人看到、被搜尋引擎收錄，刪掉也可能已經被 fork 或快取。所以貢獻只有一個原則：**送上來的是工具，不是你的作品，也不是你的個資。**

## 1. 開始之前

- 大的改動先開 issue 討論，例如新的鏡頭種類、改 `project.py` 的格式、加新套件、加一條新的線（例如解說、新聞）。錯字和小修可以直接開 PR。
- 流程：fork → 從 `main` 開分支 → 改 → 檢查（第 5 節）→ 對 `main` 開 PR。
- 環境安裝見 [SETUP.md](docs/zh-TW/SETUP.md)。
- 第一次 clone 下來就先裝 commit 前的檢查：

```bash
python dreamfab/check_public.py --install-hook
```

- **不要為了貢獻花大量 AutoIP 點數**：能用手上已經生成的素材驗證，就不要重新送任務。改到送任務的程式時，在 PR 寫你送了幾個任務、花了多少點數。

## 2. 什麼可以進 repo

| 可以 | 不可以 |
|---|---|
| `dreamfab/`（共用核心）、`drama/`、`mv/` 等各條線的程式碼 | `projects/` 底下的任何東西（劇本、歌、角色、聲音、素材、成片） |
| `docs/` 文件、`docs/images/` 的說明截圖 | 影片、音訊、圖片、字型、模型檔（說明截圖除外） |
| `examples/`：只有結構、沒有劇情的範例 | 任務檔 `jobs/*.json`、`*.state`（裡面有你的 prompt、台詞、本機絕對路徑） |
| `skills/`、安裝腳本、plugin 設定 | `speech.json`、`storyboard.json`、`clips.json`、`align.json`、`faces.json`（你的台詞、歌詞、角色） |
| | `youtube.json`、`upload_plan.json`、`YouTube_SEO.txt`（你的頻道、影片和文案） |
| | `client_secret*.json`、`token*.json`、`.env`、任何 API key |
| | `library.db` 和其他資料庫 |

`.gitignore` 已經擋掉大部分。但 `git add -f`、改了副檔名、或 `.gitignore` 沒列到的格式（`.mkv`、`.heic`、`.flac`……）它擋不到，commit 前的檢查會再擋一次。**不要用 `git add -f` 硬加進來。**

## 3. 去識別化

寫範例、文件、LESSONS、程式註解、測試資料、commit 訊息、PR 和 issue 時，都要把你自己的作品拿掉。**commit 訊息和推上去的檔案會永遠留在歷史裡**，之後刪檔也還查得到。

- **文件寫的是框架，不是某一支作品**：寫可以重複套用的做法，留給使用者自己決定的空間。不要照抄某一集的台詞、某支 MV 的歌詞、角色名、分鏡或畫風設定。
- **角色**：用 A／B／C，key 用 `A`、`B_CASUAL` 這種。不要用你作品裡的角色名、角色 key、劇名、集名、歌名。
- **地點**：`ROOM`、`OFFICE` 這種通用名稱可以。你作品裡專有的公司名、店名、地名不行。
- **台詞、歌詞與提示詞**：用 `<…>` 佔位，例如 `say=("B", "<B 加壓的一句>", "<delivery>")`。
- **踩坑紀錄（LESSONS）**：寫發生了什麼、怎麼解，實測數字換成泛稱。可以寫「短劇第二季第七集」「一支木版畫 MV，14 段有 4 段走進新角色」，但不要引原台詞、寫出歌名或頻道、附影片連結。
- **數字可以留**：秒數、`crop` 參數、強度、點數都是解法的一部分，不會洩露劇情。
- **截圖**（`docs/images/`）：用 `examples/<線>/demo`，或打上馬賽克。先裁掉瀏覽器分頁、書籤列、桌面、檔案總管的路徑、帳號頭像、email、點數餘額，畫面裡不要有劇名、角色的臉（尤其是真人）、帳號、頻道。存檔前把 EXIF（相機、GPS）去掉。
- **真人**：任何人的照片、聲音樣本、翻唱都不要放，包括你自己的，就算只是測試用也不行。
- **YouTube 與 AutoIP**：你的頻道 ID、影片 ID、播放清單 ID、AutoIP 任務 uuid、下載連結、點數餘額不要寫進範例或測試。

## 4. 個資與憑證

- **API key** 只放環境變數 `AUTOIP_API_KEY`。不要寫進程式、文件、測試、log 範例。程式不可以把它印出來、寫進 log、`.state` 或任何輸出。
- **YouTube OAuth**：`client_secret*.json`、`token*.json` 放在 repo 外面（預設 `~/.config/dreamfab/`），程式用環境變數或路徑參數讀。
- **路徑**：程式和文件不要寫死 `C:\Users\<你的名字>\...` 或 `/Users/<你的名字>/...`。程式從專案資料夾（`project.py` 所在的資料夾）組出路徑，或用 `os.path.expanduser("~")`、環境變數；文件用 `P`、`projects/<系列>/s1e01_<集名>` 這種寫法。
- **聯絡資料**：email、電話、身分證字號、地址、LINE ID 不要出現在任何檔案、測試資料、截圖裡。
- **commit 作者**：commit 會公開你的 `user.email`。不想公開就改用 GitHub 的 noreply 地址（GitHub 設定 → Emails → Keep my email addresses private），例如 `git config user.email <ID>+<帳號>@users.noreply.github.com`。
- **貼 log 之前先遮金鑰**，只貼錯誤碼和訊息（例如 `validation_failed`、`concurrency_limit`），不要整份 `.state` 或任務檔；路徑換成相對路徑：

```bash
python dreamfab/aip_runner.py P/jobs/x.json 2>&1 | sed 's/aip_[A-Za-z0-9_]*/aip_***/g'
```

```powershell
python dreamfab/aip_runner.py P/jobs/x.json 2>&1 | ForEach-Object { $_ -replace 'aip_\w+', 'aip_***' }
```

### 不小心推上去了

1. **先撤銷，再清理**：
   - AutoIP key：到 https://autoip.app/dashboard/api-keys 刪掉，重新申請一把。
   - YouTube OAuth：到 Google Cloud Console 重設 client secret，並撤銷已授權的 token。
2. **再清 git 歷史**（例如用 `git filter-repo`），然後通知 maintainer。只刪檔再 commit 一次不夠：舊 commit 裡還在，別人也可能已經 fork 或 clone 了。如果已經合併進主線，開一個**不含**那段內容的 issue，只寫是哪一個 commit 要清。
3. **作品或個資**：一樣要清歷史；推上去的時間越短，被複製走的機會越小。

## 5. 送出前的檢查：`check_public.py`

```bash
python dreamfab/check_public.py --install-hook                # 裝一次：之後每次 commit 前自動檢查
python dreamfab/check_public.py                               # 手動：檢查已 staged 的變更
python dreamfab/check_public.py --range origin/main..HEAD     # 開 PR 前：這次要推的所有 commit
python dreamfab/check_public.py --all                         # 整個 repo
```

它會找出：

- **不該進 repo 的檔案**：`projects/`、影音圖檔與字型（`docs/images/` 的圖除外）、任務檔與 `.state`、台詞 json、YouTube 上傳紀錄、憑證、資料庫。
- **金鑰**：AutoIP key（`aip_…`）、Google OAuth client ID／secret／token、私鑰、常見的 API token。印出來時會遮住大部分字元。
- **個資**：email、台灣手機號碼、身分證字號、帶使用者名稱的家目錄路徑、YouTube 頻道 ID。
- **你的作品**：repo 根目錄 `.private_terms` 裡列的每個詞。
- **圖片的 EXIF**（相機、GPS）：`docs/images/` 新增的圖。

**`.private_terms`** 是你自己作品的詞彙表：一行一個詞，`#` 開頭是註解，大小寫要完全一樣。這個檔在 `.gitignore` 裡，不會被推上去。把劇名、歌名、角色名、角色 key、專有地名、頻道和影片 ID 都列進去：

```
# .private_terms
<劇名或歌名>
<主角名字>
<角色 key，例如 HERO_>
<公司或店名>
<頻道 ID>
<影片 ID>
```

**誤判**：如果某一行真的要公開（例如 README 的作品展示），在那一行加 `public-ok`：Markdown 用 `<!-- public-ok -->`，Python 和 shell 用 `# public-ok`。金鑰不會因為 `public-ok` 放行。

不要用 `git commit --no-verify` 跳過檢查。檢查只是補漏，不能取代你自己看一遍 diff：它認不出你作品裡的一句台詞，除非那句的詞列在 `.private_terms` 裡。也用 `git log -p` 看看之前的 commit 有沒有帶進去。

## 6. 程式與文件

- **寫法**：跟周圍的程式碼一樣，包括命名、註解的多寡、寫法。每個腳本開頭的 docstring 寫用法和環境變數，改了行為就一起改。
- **共用的放核心**：兩條以上的線都會用到的（送任務、點數、超分補幀、資源庫、YouTube、檢查工具）放 `dreamfab/`；只有一條線用的留在那條線的資料夾。
- **套件**：能用標準函式庫加 ffmpeg 做到的，就不要加新套件；真的要加，寫進 `requirements.txt`（只有 MV 用的寫進 `requirements-mv.txt`），並在 PR 說明為什麼不能用現有的。
- **預設行為**：付費服務、實驗功能、會改變輸出的 GPU 處理（例如超分補幀）都要用參數或設定開啟，沒開時最多印一行提示；不改變結果的加速（例如 NVENC 編碼）可以自動用。
- **會花點數的流程**：
  - 送任務前要能先估點數（`dreamfab.util.estimate`），也要能先看審核圖或靜圖再送影片。不要讓程式自動送出使用者還沒看過的批次。
  - runner 預設一次一個任務（`AIP_MAX=1`）。
  - 被拒絕的任務，內容沒改就不要自動重送。
- **文件**：先寫 `docs/zh-TW/`，再同步 `docs/en/`；README 中英文都要改，兩份 `RELEASE_NOTES.md` 最上面都加一條（版本號、日期、改了什麼）。
- **新指令或新欄位**：同步更新那條線的 `PROJECT_FORMAT.md`、`WORKFLOW.md` 和 `skills/dreamfab-<線>/SKILL.md`。
- **測試**：
  - 至少跑 `python -m py_compile` 檢查改過的檔案。
  - 不花點數的部分用範例跑，例如 `python drama/storyboard.py examples/drama/demo`、`python mv/storyboard.py examples/mv/demo`。
  - 要用真的素材測，就在你自己的 `projects/` 裡測，不要把素材帶進 PR。

## 7. Pull request

- 每個 commit 只做一件事。commit 訊息用英文，比照現有的寫法：`檔名或功能: 做了什麼`，例如 `aip_runner.py: submit only in the off-peak window`。
- 說明改了什麼、為什麼、怎麼驗證：跑了哪個步驟、用什麼素材、花了多少點數。
- 附圖或影片要用示範素材，或你有權公開、已經去識別化的片段。
- 勾完 PR 範本裡的檢查清單。

## 8. 回報問題（issue）

- **請附上**：哪一條線、版本號（`RELEASE_NOTES.md` 最上面那條）、作業系統、Python 和 ffmpeg 版本、執行的指令，以及**遮過金鑰**的錯誤訊息。
- **不要附**：你的專案資料夾、真人照片、聲音、還沒公開的劇本、歌曲、角色圖。要重現問題就用 `examples/<線>/demo`、做一個最小的假專案，或描述結構，例如「三個角色、一顆多參考鏡頭、兩人同框」。
- **安全問題**（例如會讓 key 外洩的 bug）不要在公開 issue 寫細節：先開一個只寫「有安全問題要私下回報」的 issue，maintainer 會跟你聯絡。

## 授權

送出貢獻，就表示你同意它以本專案的 [MIT License](LICENSE) 釋出，而且你有權這樣做。只送你有權公開的內容：字型、音樂、圖片如果不是你自己做的，又沒有允許再散布的授權，就不要放進來。
