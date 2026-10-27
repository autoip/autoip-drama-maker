# 整部劇範本 / Series template

**中文**

空白的整部劇範本，只有要填的格子，沒有任何故事或風格。每個格子為什麼存在、可以怎麼填，見 [docs/zh-TW/SERIES_PLANNING.md](../../docs/zh-TW/SERIES_PLANNING.md)。

```
plan.md                一句話、爽點引擎、篇章表、分集卡、待確認：最先寫
characters.md          人設、造型、聲音樣本、關係圖
style.md               風格聖經：固定的錨點、包裝格式
s1e01_title/
  劇本_v1.md           一集的劇本骨架
  YouTube_SEO.txt      標題、說明欄、hashtag
```

怎麼用：

1. 複製成 `projects/<劇名>/`，把 `s1e01_title` 改成 `s1e01_<集名>`。資料夾要在第一次送 AutoIP 任務之前定名。
2. 先寫 `plan.md`：一句話、引擎、篇章表，至少第一個篇章的分集卡。
3. 再寫 `characters.md` 和 `style.md` 的草稿；新角色先做定裝、錄聲音樣本。
4. 第一集的 `project.py` 從 [`examples/demo/project.py`](../demo/project.py) 複製，路徑改成 `../cast/…`；第二集起複製上一集的。
5. 每集照 [WORKFLOW.md](../../docs/zh-TW/WORKFLOW.md) 做。第一集做完後回頭定稿 `style.md`。

格子都可以刪或加。框架只要求每部劇有一句話、一個引擎、同一個每集結構、幾個大揭露、固定的角色與包裝；其他都由你決定。

**English**

A blank template for a whole drama: only the boxes to fill, no story or style of its own. Why each box exists and how it can be filled: [docs/en/SERIES_PLANNING.md](../../docs/en/SERIES_PLANNING.md). The template files are in Chinese with English headings.

- `plan.md`: pitch, engine, arc table, episode cards, open questions. Write it first.
- `characters.md`: who each character is, their look, voice sample and relations.
- `style.md`: fixed anchors and the package.
- `s1e01_title/`: a script skeleton (`劇本_v1.md`) and publishing copy (`YouTube_SEO.txt`).

Copy it to `projects/<series>/` and rename `s1e01_title` to `s1e01_<title>` before the first AutoIP job. Episode 1's `project.py` starts from [`examples/demo/project.py`](../demo/project.py) with paths changed to `../cast/…`; later episodes copy the previous one.
