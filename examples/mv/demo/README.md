# 示範專案《夜之劇場 NIGHT THEATRE》 / Demo project

**中文**

虛構的 70 秒哥德金屬雙主唱：女高音 F、嘶吼 M，另有鼓手與吉他手。用來示範 `project.py` 的每個欄位。

本資料夾只有設定檔，不附任何素材。要實際跑，請先複製到 `projects/`，再自己放入以下檔案：

```
song.mp3                   你的歌
chars/soprano.png ...      CHARS 列出的角色圖
fonts/PSSerifBlack.ttf     見 docs/zh-TW/SETUP.md
fonts/NotoSerif-*.ttf
cards/open.jpg, end.jpg    （選用）片頭、片尾卡
```

然後照 [docs/zh-TW/WORKFLOW.md](../../../docs/zh-TW/mv/WORKFLOW.md) 一步一步做。

`thumbs.py` 是縮圖範例：從成片抓畫面放進 `thumb_src/`，執行後輸出 A/B/C 三張縮圖。

**English**

A fictional 70-second gothic-metal duet: soprano F and screamer M, plus a drummer and a guitarist. It shows every `project.py` field in use.

This folder holds only config, no media. To run it, copy it to `projects/` and add these files yourself:

```
song.mp3                   your song
chars/soprano.png ...      the character images listed in CHARS
fonts/PSSerifBlack.ttf     see docs/en/SETUP.md
fonts/NotoSerif-*.ttf
cards/open.jpg, end.jpg    (optional) opening / ending cards
```

Then follow [docs/en/WORKFLOW.md](../../../docs/en/mv/WORKFLOW.md).

`thumbs.py` is a thumbnail example: grab frames from the finished MV into `thumb_src/`, and it outputs the A/B/C thumbnails.
