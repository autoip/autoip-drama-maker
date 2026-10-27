# 示範集 / Demo episode

**中文**

一集 1 分鐘直式短劇的**結構**，沒有劇情：角色是 A（主角：被壓、再揚起來）、B（對手）、C（扭轉局面的人），場景、台詞、動作都是 `<…>` 佔位。11 顆鏡頭照一集的結構排好（鉤子 → 衝突 → 爽點 → 卡點），用來示範 `project.py` 的每個欄位：

- `M` 多參考影片的對白（每個角色用自己的聲音樣本）、`LS` 對嘴（自己錄的一句）、`I2V` 外景、`K` 轉場
- 剪輯：冷開場、正反打、反應鏡頭（插入列）、片名卡、人物字卡、爽點推近加音效、卡點定格「未完待續」
- 兩段配樂、兩個音效

**劇情寫在你自己的專案裡，不進 repo。** 複製到 `projects/<劇名>/s1e01_<集名>/`（`projects/` 已被 .gitignore 排除），把所有 `<…>` 換成你的故事，再自己準備以下檔案（或讓 `make_jobs.py P refs` 生成有 `prompt` 的角色、場景、道具）：

```
cast/A.png B.png C.png             角色定裝（或由 prompt 生成）
voices/raw/a.m4a ...               每個角色一段你有權使用的錄音 -> voices.py
lines/S2_10.wav                    對嘴鏡頭 S2_10 的那句台詞
music/tension.mp3, reveal.mp3      配樂
sfx/hit.wav, door.wav              音效
fonts/DKSansBlack.ttf              見 docs/zh-TW/SETUP.md
```

然後照 [docs/zh-TW/WORKFLOW.md](../../docs/zh-TW/WORKFLOW.md) 一步一步做。

`covers.py` 是封面範例：從片段抓畫面放進 `thumb_src/`，執行後輸出 A/B/C 三張 1080×1920 封面；文字換成你的劇名與鉤子。

**English**

The **structure** of a one-minute vertical short drama, with no story: the cast is A (the lead, pushed down and then rising), B (the opponent) and C (the one who turns it), and the sets, lines and actions are `<…>` placeholders. The 11 shots follow one episode's structure (hook → pressure → payoff → cliffhanger) and show every `project.py` field:

- `M` multi-reference dialogue (each character in their own voice sample), `LS` lip-sync (one recorded line), `I2V` exterior, `K` transition
- the edit: cold open, shot / reverse shot, a reaction cutaway, title card, character cards, a punch-in with a hit on the payoff, a freeze-frame cliffhanger
- two music cues, two sound effects

**Your story lives in your own project, not in the repo.** Copy the folder to `projects/<series>/s1e01_<title>/` (`projects/` is ignored by git), replace every `<…>` with your story, and add these files yourself (or let `make_jobs.py P refs` draw the cast, sets and props that have a `prompt`):

```
cast/A.png B.png C.png             character references (or drawn from prompt)
voices/raw/a.m4a ...               a recording of each character you have the rights to -> voices.py
lines/S2_10.wav                    the line of lip-sync shot S2_10
music/tension.mp3, reveal.mp3      music
sfx/hit.wav, door.wav              sound effects
fonts/DKSansBlack.ttf              see docs/en/SETUP.md
```

Then follow [docs/en/WORKFLOW.md](../../docs/en/WORKFLOW.md).

`covers.py` is a cover example: grab frames from the clips into `thumb_src/`, and it outputs three 1080×1920 covers; replace the text with your title and hook.
