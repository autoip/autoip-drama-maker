<!-- 中文說明見 CONTRIBUTING.md；English: CONTRIBUTING.en.md -->

## 改了什麼、為什麼／What and why

<!-- 哪一條線：core（dreamfab/）、drama、mv、explainer…／which line: core (dreamfab/), drama, mv, explainer … -->

## 怎麼測的／How it was tested

<!-- 跑了哪個步驟、用什麼素材、花了多少 AutoIP 點數／which step, on what footage, how many AutoIP credits -->

## 檢查清單／Checklist

- [ ] `python dreamfab/check_public.py --range origin/main..HEAD` 沒有找到東西／finds nothing
- [ ] 沒有 `projects/` 的檔案、影音圖檔、任務檔、憑證／no files from `projects/`, no media, job files or credentials
- [ ] 範例、文件、註解、commit 訊息裡沒有我的劇名、角色、台詞、歌詞、頻道或影片 ID／no series title, character, line, lyric, channel or video id of mine in examples, docs, comments or commit messages
- [ ] 沒有 API key、email、電話、家目錄路徑、真人照片或聲音／no API key, e-mail, phone number, home-folder path, or real person's photo or voice
- [ ] 截圖已去識別化、去掉 EXIF／screenshots de-identified, EXIF stripped
- [ ] 文件先改 `docs/zh-TW/` 再同步 `docs/en/`，`RELEASE_NOTES.md` 兩份都加了一條（有改文件的話）／docs: zh-TW first, then en, an entry in both `RELEASE_NOTES.md` (if docs changed)
- [ ] 預設行為沒變：GPU、付費、實驗功能都要另外開啟／defaults unchanged: GPU, paid and experimental features are opt-in
