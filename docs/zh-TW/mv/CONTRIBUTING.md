# 貢獻指南

中文 | [English](../en/CONTRIBUTING.md)

歡迎修 bug、加功能、補文件，或分享你實測的數字。這個 repo 是公開的，送出的每一行都會被所有人看到、被搜尋引擎收錄，刪掉也可能已經被 fork 或快取。所以除了程式本身，**送出前一定要做「去識別化」**（見下方）。

## 開始之前

- 想改的東西比較大，先開 issue 說明要改什麼、為什麼。錯字、小修正可以直接送 PR。
- 環境照 [SETUP.md](SETUP.md) 裝好。Python 3.10 起，加上 ffmpeg／ffprobe。
- 測試時不要為了貢獻花大量 AutoIP 點數。能用手上已經生成的素材驗證，就不要重新送任務。改到送任務的程式時，在 PR 寫你送了幾個任務、花了多少點數。

## 程式規範

- **跟周圍的程式碼一致**：命名、註解多寡、寫法都比照同一個檔案。每個腳本開頭的 docstring 寫用法和環境變數，改了行為就一起改。
- **公開程式預設走 CPU**：GPU、付費服務、實驗功能都要用環境變數或參數開啟，沒開時最多印一行提示。
- **套件**：只用標準函式庫和 `requirements.txt` 裡的套件。要加新套件，在 PR 說明為什麼不能用現有的。
- **花點數的功能**：送任務前要能先估點數（`common.estimate`），也要有先看靜圖再送影片的關卡。不可以預設就送出。
- **路徑**：程式裡不要寫死本機路徑。路徑一律從專案資料夾（`project.py` 所在的資料夾）組出來。
- **秘密資訊**：API key、OAuth 檔只能從環境變數或 repo 外的檔案讀。程式不可以把它們印出來、寫進 log、`.state` 或任何輸出。

## 文件規範

- **中英文兩份一起改**：`README.md`／`README.en.md`、`docs/zh-TW/`／`docs/en/`，用到的話 `skills/autoip-mv-maker/SKILL.md` 也要改。
- **在兩份 `RELEASE_NOTES.md` 最上面加一條**：版本號、日期、改了什麼。
- **文件寫的是「框架」，不是某一支作品**：寫可以重複套用的公式，留給使用者自己決定的空間。不要照抄某支 MV 的歌詞、角色名、分鏡或畫風設定。
- **實測數字很有價值，但要換成泛稱**：寫「一支木版畫 MV，14 段有 4 段走進新角色」可以；寫出歌名、頻道或影片連結不行。

## 去識別化：送出前一定要檢查

### 絕對不能出現

| 類別 | 例子 | 說明 |
|---|---|---|
| 金鑰與憑證 | `aip_` 開頭的 AutoIP API key、`client_secret_*.json`、`*token*.json`、`.env` | 洩漏就等於把帳號和點數交出去 |
| 真人的影像和聲音 | 你或別人的照片、臉部參考圖、錄音、翻唱 | 就算只是測試用也不行 |
| 個人資料 | 本名、email、電話、地址、身分證號、生日 | 也包括 commit 作者資訊以外、寫在檔案內容裡的 |
| 帳號識別 | YouTube 頻道 ID、私人或不公開的影片／播放清單 ID、AutoIP 任務 uuid、下載連結、點數餘額 | 可以拿來對應到你本人或你的帳號 |
| 本機路徑 | `C:\Users\王小明\...`、`/home/alice/...`、`/Users/bob/...` | 路徑裡常常有使用者名稱 |
| 未公開的創作 | 還沒發表的歌詞、歌曲、角色設定、企劃筆記 | 你的作品留在你自己的 `projects/` |

`projects/`、影音圖檔、`jobs/`、`*.state`、`*.log` 都已經在 `.gitignore` 裡。**不要用 `git add -f` 硬加進來。**

### 文件、範例、截圖

- **範例專案**：歌名、角色、劇情都用虛構的（參考 `examples/demo`），只放設定檔，不附素材。
- **截圖**：先裁掉瀏覽器分頁、書籤列、桌面、檔案總管的路徑、帳號頭像、email、點數餘額，再檢查畫面裡有沒有真人的臉。
- **路徑**：用 `P/`、`<project>`、`~/` 代替真實路徑。

### Log 和錯誤訊息

貼到 issue 或 PR 前，先把金鑰遮掉：

```bash
python mvkit/aip_runner.py P/jobs/x.json 2>&1 | sed 's/aip_[A-Za-z0-9_]*/aip_***/g'
```

```powershell
python mvkit/aip_runner.py P/jobs/x.json 2>&1 | ForEach-Object { $_ -replace 'aip_\w+', 'aip_***' }
```

- 只貼錯誤碼和訊息（例如 `validation_failed`、`concurrency_limit`），不要整份 `.state`、整份任務檔。
- 把路徑換成相對路徑，再檢查一次有沒有 email、頻道 ID。

### 上傳前自我檢查

```bash
git status                       # 有沒有不該加的檔案
git diff --cached --stat         # 只有預期的檔案？沒有圖片、影片、音檔、.state、jobs/
git diff --cached | grep -nE 'aip_[A-Za-z0-9]{8,}|client_secret|refresh_token|access_token|[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+\.[A-Za-z.]{2,}|[A-Za-z]:[\\/]+Users[\\/]|/home/[^/ ]+|/Users/[^/ ]+'
```

最後一行如果有找到東西，就逐筆確認後刪掉。另外，用 `git log -p` 看看之前的 commit 裡有沒有也帶進去。

### 不小心傳上去了

1. **金鑰立刻作廢**：AutoIP 到 https://autoip.app/dashboard/api-keys 撤銷並換新 key；YouTube OAuth 到 Google Cloud Console 刪掉那組憑證。只刪檔案沒有用，因為歷史紀錄、fork 和快取裡都還在。
2. 在你的分支把檔案移除，並重寫歷史，再 force push 你的分支。
3. 如果已經合併進主線，開一個**不含**那段內容的 issue，只寫是哪一個 commit 要清，維護者會處理。

## 送 PR

1. Fork，從 `main` 開一個分支。
2. 每個 commit 只做一件事。commit 訊息用英文，比照現有的寫法：`檔名或功能: 做了什麼 (版本號)`，例如 `aip_runner.py: submit only in the off-peak window (0.7.1)`。
3. 照 PR 範本的清單逐項勾選，包括去識別化檢查。
4. 說明改了什麼、為什麼、怎麼驗證：跑了哪個步驟、用什麼素材、花了多少點數。

## 回報問題

- **請附上**：版本號（`RELEASE_NOTES.md` 最上面那條）、作業系統、Python 和 ffmpeg 版本、執行的指令，以及**遮過金鑰**的錯誤訊息。
- **不要附**：你的專案資料夾、歌曲、角色圖、真人照片。需要重現時，用 `examples/demo` 或做一個最小的假專案。
- 安全問題（例如程式會把金鑰寫進輸出）不要在公開 issue 寫出細節，先開一個 issue 說「有安全問題要回報」，請維護者聯絡你。

## 授權

送出的程式和文件都以本 repo 的 [MIT 授權](../../LICENSE) 釋出。只送你有權公開的內容：字型、音樂、圖片如果不是你自己做的，又沒有允許再散布的授權，就不要放進來。
