# 示範專案：洛神是誰？（MV《洛川》的解說）/ Demo project

**中文**

MV《洛川》（https://youtu.be/OlIQYvfwZhA）的解說縮短版：開場、第一章、結尾，約 1 分半。用來示範解說線 `project.py` 的每個欄位，包括 MOSS-Image 的 caption 寫法和用 Layout 生成帶標題的封面。

本資料夾只有設定檔和文案，不附任何素材。要實際跑，請先複製到 `projects/<系列>/`，再自己放入：

```
voices/NARRATOR.wav          旁白樣本（5–15 秒，你有權使用的聲音）
music/luochuan_inst.flac     MV 去人聲的伴奏（demucs）
music/luochuan_mv.mp4        MV 本身（結尾的 MV 片段）
fonts/ExplainerSerif.ttf     見 docs/zh-TW/explain/OVERVIEW.md 的 FONT
```

然後照 [docs/zh-TW/explain/OVERVIEW.md](../../../docs/zh-TW/explain/OVERVIEW.md) 一步一步做：`narration.py jobs` → 送出 → `narration.py check` → `make_images.py` → 送出 → `render.py`（一次出寬版 `out/demo_luoshen.mp4` 和直版 Shorts `out/demo_luoshen_shorts.mp4`）。

**English**

A shortened explainer for the MV "Luo River" (https://youtu.be/OlIQYvfwZhA): the opening, chapter 1 and the ending, about a minute and a half. It shows every `project.py` field of the explain line, including MOSS-Image captions and a cover painted with its title through a Layout.

This folder holds only config and the script, no media. To run it, copy it to `projects/<series>/` and add:

```
voices/NARRATOR.wav          a narrator sample (5-15 s, a voice you have the rights to)
music/luochuan_inst.flac     the MV without vocals (demucs)
music/luochuan_mv.mp4        the MV itself (the clip at the end)
fonts/ExplainerSerif.ttf     see FONT in docs/en/explain/OVERVIEW.md
```

Then follow [docs/en/explain/OVERVIEW.md](../../../docs/en/explain/OVERVIEW.md): `narration.py jobs` → submit → `narration.py check` → `make_images.py` → submit → `render.py` (both cuts at once: the wide `out/demo_luoshen.mp4` and the vertical Short `out/demo_luoshen_shorts.mp4`).
