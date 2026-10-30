# 系列範本 / Series template

**中文**

空白的系列範本，只有要填的格子，沒有任何風格。每個格子為什麼存在、可以怎麼填，見 [docs/zh-TW/SERIES_PLANNING.md](../../docs/zh-TW/SERIES_PLANNING.md)。

```
research.md            一句話、主軸表、每集企劃卡、待確認清單：最先寫
style.md               系列風格聖經：固定的錨點、每集對照表、歌曲結構、包裝格式
s1e1_title/
  歌詞_v1.txt          Suno 格式的歌詞骨架
  角色.md              定裝定案與同框規則
  YouTube_SEO.txt      標題、說明欄、章節、標籤
```

怎麼用：

1. 複製成 `projects/<系列名>/`，把 `s1e1_title` 改成 `s1e1_<歌名>`。資料夾要在第一次送 AutoIP 任務之前定名。
2. 先寫 `research.md`：一句話、主軸、整季的企劃卡。
3. 再寫 `style.md` 的草稿：挑 3–5 個固定錨點、填每集對照表、定歌曲結構和包裝。
4. 第一集的 `project.py` 從 [`examples/demo/project.py`](../../examples/demo/project.py) 複製；第二集起複製上一集的。
5. 每集照 [WORKFLOW.md](../../docs/zh-TW/WORKFLOW.md) 做。第一集做完後回頭定稿 `style.md`。

格子都可以刪或加。框架只要求每一季都有一句話、一條主軸、幾個固定錨點、同一種結構和同一套包裝；其他都由你決定。

**English**

A blank series template: only the boxes to fill, no style of its own. Why each box exists and how it can be filled: [docs/en/SERIES_PLANNING.md](../../docs/en/SERIES_PLANNING.md). The template files are in Chinese with English headings.

- `research.md`: pitch, axis table, episode cards, open questions. Write it first.
- `style.md`: series style bible: fixed anchors, per-episode table, song structure, package format.
- `s1e1_title/`: Suno-format lyric skeleton (`歌詞_v1.txt`), cast notes (`角色.md`), publishing copy (`YouTube_SEO.txt`).

Copy it to `projects/<series>/` and rename `s1e1_title` to `s1e1_<title>` before the first AutoIP job. Write `research.md`, then a draft `style.md` (3–5 fixed anchors, the per-episode table, the structure and the package). Episode 1's `project.py` starts from [`examples/demo/project.py`](../../examples/demo/project.py); later episodes copy the previous one. Make each episode with [WORKFLOW.md](../../docs/en/WORKFLOW.md), and settle `style.md` after episode 1.

Delete or add boxes freely. The framework only asks that every season has a pitch, an axis, a few fixed anchors, one structure and one package; the rest is up to you.
