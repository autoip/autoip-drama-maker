# 貢獻原始碼

中文 | [English](CONTRIBUTING.en.md)

歡迎修 bug、補文件、加功能。

這個 repo 是公開的，而做短劇的人手上一定有不能公開的東西：劇本、角色、聲音樣本、真人照片、API key、YouTube 憑證。所以貢獻只有一個原則：**送上來的是工具，不是你的劇，也不是你的個資。**

## 1. 開始之前

- 大的改動先開 issue 討論，例如新的鏡頭種類、改 `project.py` 的格式、加新套件。小修可以直接開 PR。
- 流程：fork → 從 `main` 開分支 → 改 → 檢查（第 5 節）→ 對 `main` 開 PR。
- 環境安裝見 [SETUP.md](docs/zh-TW/SETUP.md)。
- 第一次 clone 下來就先裝 commit 前的檢查：

```bash
python dramakit/check_public.py --install-hook
```

## 2. 什麼可以進 repo

| 可以 | 不可以 |
|---|---|
| `dramakit/` 的程式碼 | `projects/` 底下的任何東西（劇本、角色、聲音、素材、成片） |
| `docs/` 文件、`docs/images/` 的說明截圖 | 影片、音訊、圖片、字型（說明截圖除外） |
| `examples/`：只有結構、沒有劇情的範例 | 任務檔 `jobs/*.json`、`*.state`（裡面有你的 prompt、台詞、本機絕對路徑） |
| `skills/`、安裝腳本、plugin 設定 | `speech.json`、`storyboard.json`、`clips.json`（裡面有你的台詞） |
| | `youtube.json`、`upload_plan.json`（你的頻道與影片） |
| | `client_secret*.json`、`token*.json`、`.env`、任何 API key |
| | `library.db` 和其他資料庫 |

`.gitignore` 已經擋掉大部分。但 `git add -f`、改了副檔名、或 `.gitignore` 沒列到的格式（`.mkv`、`.heic`、`.flac`……）它擋不到，commit 前的檢查會再擋一次。

## 3. 去識別化

寫範例、文件、LESSONS、程式註解、測試資料、commit 訊息、PR 和 issue 時，都要把你自己的劇拿掉。**commit 訊息和推上去的檔案會永遠留在歷史裡**，之後刪檔也還查得到。

- **角色**：用 A／B／C，key 用 `A`、`B_CASUAL` 這種。不要用你劇裡的角色名、角色 key、劇名、集名。
- **地點**：`ROOM`、`OFFICE` 這種通用名稱可以。你劇裡專有的公司名、店名、地名不行。
- **台詞與提示詞**：用 `<…>` 佔位，例如 `say=("B", "<B 加壓的一句>", "<delivery>")`。
- **踩坑紀錄（LESSONS）**：寫發生了什麼、怎麼解。可以寫「短劇第二季第七集」，但不要引原台詞，改成描述，例如「一句先說一個字、停很久才接下去的台詞」。
- **數字可以留**：秒數、`crop` 參數、強度都是解法的一部分，不會洩露劇情。
- **截圖**（`docs/images/`）：用 `examples/demo` 或打上馬賽克。畫面裡不要有劇名、角色的臉（尤其是真人）、帳號、頻道、資料夾路徑、瀏覽器分頁。存檔前把 EXIF（相機、GPS）去掉。
- **真人**：任何人的照片、聲音樣本都不要放，包括你自己的。
- **YouTube**：你的頻道 ID、影片 ID、播放清單 ID 不要寫進範例或測試。

## 4. 個資與憑證

- **API key** 只放環境變數 `AUTOIP_API_KEY`。不要寫進程式、文件、測試、log 範例；貼 log 之前先看一遍。
- **YouTube OAuth**：`client_secret*.json`、`token*.json` 放在 `projects/` 或 repo 外面，程式用路徑參數讀。
- **路徑**：程式和文件不要寫死 `C:\Users\<你的名字>\...` 或 `/Users/<你的名字>/...`。程式用相對路徑、`os.path.expanduser("~")` 或環境變數；文件用 `P`、`projects/<系列>/s1e01_<集名>` 這種寫法。
- **聯絡資料**：email、電話、身分證字號、地址、LINE ID 不要出現在任何檔案、測試資料、截圖裡。
- **commit 作者**：commit 會公開你的 `user.email`。不想公開就改用 GitHub 的 noreply 地址（GitHub 設定 → Emails → Keep my email addresses private），例如 `git config user.email <ID>+<帳號>@users.noreply.github.com`。

### 不小心推上去了

1. **先撤銷，再清理**：
   - AutoIP key：到儀表板刪掉，重新申請一把。
   - YouTube OAuth：到 Google Cloud Console 重設 client secret，並撤銷已授權的 token。
2. **再清 git 歷史**（例如用 `git filter-repo`），然後通知 maintainer。只刪檔再 commit 一次不夠：舊 commit 裡還在，別人也可能已經 fork 或 clone 了。
3. **劇情或個資**：一樣要清歷史；推上去的時間越短，被複製走的機會越小。

## 5. 送出前的檢查：`check_public.py`

```bash
python dramakit/check_public.py --install-hook                # 裝一次：之後每次 commit 前自動檢查
python dramakit/check_public.py                               # 手動：檢查已 staged 的變更
python dramakit/check_public.py --range origin/main..HEAD     # 開 PR 前：這次要推的所有 commit
python dramakit/check_public.py --all                         # 整個 repo
```

它會找出：

- **不該進 repo 的檔案**：`projects/`、影音圖檔與字型（`docs/images/` 的圖除外）、任務檔與 `.state`、台詞 json、YouTube 上傳紀錄、憑證、資料庫。
- **金鑰**：AutoIP key（`aip_…`）、Google OAuth client ID／secret／token、私鑰、常見的 API token。印出來時會遮住大部分字元。
- **個資**：email、台灣手機號碼、身分證字號、帶使用者名稱的家目錄路徑、YouTube 頻道 ID。
- **你的劇**：repo 根目錄 `.private_terms` 裡列的每個詞。
- **圖片的 EXIF**（相機、GPS）：`docs/images/` 新增的圖。

**`.private_terms`** 是你自己的劇的詞彙表：一行一個詞，`#` 開頭是註解，大小寫要完全一樣。這個檔在 `.gitignore` 裡，不會被推上去。把劇名、角色名、角色 key、專有地名、頻道和影片 ID 都列進去：

```
# .private_terms
<劇名>
<主角名字>
<角色 key，例如 HERO_>
<公司或店名>
<頻道 ID>
<影片 ID>
```

**誤判**：如果某一行真的要公開（例如 README 的作品展示），在那一行加 `public-ok`：Markdown 用 `<!-- public-ok -->`，Python 用 `# public-ok`。金鑰不會因為 `public-ok` 放行。

不要用 `git commit --no-verify` 跳過檢查。檢查只是補漏，不能取代你自己看一遍 diff：它認不出你劇裡的一句台詞，除非那句的詞列在 `.private_terms` 裡。

## 6. 程式與文件

- **寫法**：跟周圍的程式碼一樣，包括命名、註解的多寡、寫法。能用標準函式庫加 ffmpeg 做到的，就不要加新套件；真的要加，寫進 `requirements.txt`，並在 PR 說明為什麼。
- **會花點數的流程**：
  - 送出前要能先看審核圖，不要讓程式自動送出使用者還沒看過的批次。
  - runner 預設一次一個任務（`AIP_MAX=1`）。
  - 被拒絕的任務，內容沒改就不要自動重送。
- **文件**：先寫 `docs/zh-TW/`，再同步 `docs/en/`；README 中英文都要改。
- **新指令或新欄位**：同步更新 [PROJECT_FORMAT.md](docs/zh-TW/PROJECT_FORMAT.md)、[WORKFLOW.md](docs/zh-TW/WORKFLOW.md) 和 `skills/autoip-drama-maker/SKILL.md`。
- **測試**：
  - 至少跑 `python -m py_compile` 檢查改過的檔案。
  - 不花點數的部分用 `examples/demo` 跑，例如 `python dramakit/storyboard.py examples/demo`。
  - 要用真的素材測，就在你自己的 `projects/` 裡測，不要把素材帶進 PR。

## 7. Pull request

- 說明改了什麼、為什麼、怎麼測的。
- 附圖或影片要用示範素材，或你有權公開、已經去識別化的片段。
- 勾完 PR 範本裡的檢查清單。

## 8. 回報問題（issue）

- 貼 log 之前，把 key、token、路徑裡的使用者名稱、email 遮掉。
- 不要附真人照片、聲音、還沒公開的劇本。要重現問題就用 `examples/demo`，或描述結構，例如「三個角色、一顆多參考鏡頭、兩人同框」。
- **安全問題**（例如會讓 key 外洩的 bug）不要在公開 issue 寫細節：先開一個只寫「有安全問題要私下回報」的 issue，maintainer 會跟你聯絡。

## 授權

送出貢獻，就表示你同意它以本專案的 [MIT License](LICENSE) 釋出，而且你有權這樣做。
