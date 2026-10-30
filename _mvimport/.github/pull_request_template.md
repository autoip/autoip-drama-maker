## 改了什麼、為什麼 / What and why



## 怎麼驗證 / How it was verified

<!-- 跑了哪個步驟、用什麼素材、花了多少 AutoIP 點數 / which step, on what footage, how many AutoIP credits -->

## 檢查清單 / Checklist

- [ ] 中英文文件都改了，`RELEASE_NOTES.md` 兩份都加了一條 / Both languages updated, an entry in both `RELEASE_NOTES.md`
- [ ] 預設行為沒變：GPU、付費、實驗功能都要另外開啟 / Defaults unchanged: GPU, paid and experimental features are opt-in

### 去識別化 / De-identification ([說明](https://github.com/autoip/autoip-mv-maker/blob/main/docs/zh-TW/CONTRIBUTING.md#去識別化送出前一定要檢查) / [guide](https://github.com/autoip/autoip-mv-maker/blob/main/docs/en/CONTRIBUTING.md#de-identification-check-before-you-send))

- [ ] 沒有 API key（`aip_…`）、`client_secret_*.json`、token、`.env` / No API keys, OAuth files, tokens or `.env`
- [ ] 沒有真人的照片、臉部參考圖、聲音 / No photos, face references or voices of real people
- [ ] 沒有本名、email、電話、頻道 ID、私人影片 ID、任務 uuid、點數餘額 / No real names, emails, phone numbers, channel IDs, private video IDs, task uuids or credit balances
- [ ] 沒有含使用者名稱的本機路徑（`C:\Users\…`、`/home/…`）/ No local paths with a user name in them
- [ ] 範例、截圖、log 都是虛構或遮過的 / Examples, screenshots and logs are made up or masked
- [ ] 沒有影音圖檔、`projects/`、`jobs/`、`.state`（沒用 `git add -f`）/ No media, `projects/`, `jobs/` or `.state` (no `git add -f`)
