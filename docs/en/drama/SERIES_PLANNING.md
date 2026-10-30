# Planning a whole series

[中文](../../zh-TW/drama/SERIES_PLANNING.md) | English

One episode follows [WORKFLOW.md](WORKFLOW.md). A short drama often runs 20–80 episodes of 1–2 minutes each; before shooting, plan the whole series with this page. A blank template is in [`examples/drama/series_template/`](../../../examples/drama/series_template/).

This is a framework, not a template to copy. The **formula** covers "why the audience keeps watching episode after episode"; the **freedom** is "what story you tell and how it looks". The framework says which boxes to fill, not what goes in them.

| Formula (every series has it) | Freedom (all yours) |
|---|---|
| A one-line pitch for the series | Subject, genre, number of episodes |
| A payoff (爽點) engine: the push-down → rise (壓 → 揚) repeated every episode | What gets pushed down, what rises |
| The same structure every episode: hook, conflict, payoff, cliffhanger (卡點) | How long each part is, how it plays |
| A few big reveals that cut the series into arcs | What is revealed, in which episode |
| Fixed character looks and voices | Faces, voices, how many characters |
| A fixed package (cover, title, title card, cliffhanger) | What the package looks like |
| One card per episode | The story on each card |

## 1. The pitch

**Formula**: `{the lead's situation} × {what is hidden}, {the moment the audience is waiting for}`

- "<a nobody everyone looks down on> × <an identity no one knows about>, and we wait for <the people who looked down on them> to learn the truth"
- "<a lead in a terrible situation> × <an ability nobody else has>, and we wait for <that ability> to turn things around"
- "<a lead who was betrayed> × <remembers what is going to happen>, and we wait for <the betrayers> to be exposed one by one"

The examples are only boxes; the story is yours to fill in. Don't copy the plot or characters of an existing work.

If the one line can't name "the moment the audience is waiting for", the series doesn't have an engine yet.

## 2. The payoff engine: push-down → rise

**Formula**: find a loop that can run again every episode: the lead **is pushed down** (humiliated, misjudged, robbed) → the lead **rises** (comeback, reveal, face-slap (打臉)). The audience follows this loop, not the plot details.

| Engine | Push-down | Rise |
|---|---|---|
| Hidden identity | Looked down on as a nobody | The identity comes out bit by bit |
| Rebirth / foresight | Betrayed in a past life | Exposes it a step ahead this time |
| Cheat ability (金手指) | A terrible situation | One ability turns it around |
| Contrast | Looks weak | Is actually strong |
| Revenge | Everything taken | Takes it all back, one by one |

- **Complete at least one small loop every episode** (one villain face-slapped), and **one big loop every few episodes** (one big reveal).
- Keep the push-down short and the rise long. If the push-down goes on too long, the audience swipes away.
- For the next season, use a different engine, or the same engine against a bigger opponent.

## 3. The structure of each episode

**Formula**: every episode of the series has the same structure, so the audience expects the same thing at the same point.

| Part | 1-minute episode | What it does |
|---|---|---|
| Hook | 0–3 s | The middle of the conflict, or the answer to the last episode's cliffhanger |
| Conflict | 3–35 s | Push-down: people close in one after another, each line harsher than the last |
| Payoff | 35–50 s | Rise: reveal, comeback, face-slap, with reaction shots |
| Cliffhanger | Last 3–5 s | A new question that only the next episode answers |

- **The last episode's cliffhanger is this episode's hook.**
- Episode 1's first 10 seconds set up the lead's situation (who, and how they are pushed down); later episodes don't introduce it again.

## 4. Arcs and big reveals

**Formula**: use 3–5 big reveals to cut the series into arcs of 8–15 episodes each. The big reveal goes in the last episode of the arc.

- The platform's paywall point (if there is one) usually goes just before the first big reveal: the audience is hooked but doesn't have the answer yet.
- Each arc gets a new main villain, or a bigger stage (from one room to a company to a family).
- Fill in the arc table before writing episode 1. If you can't write the arc table, the engine is usually too small to carry that many episodes.

## 5. Characters and voices: fix them

Write `characters.md` before shooting, and follow it in every episode after that:

- **3–6 main characters**, each with a one-line profile, one look, one voice sample and a catchphrase (optional).
- **One look per arc.** A costume change is a new character sheet with a new key, written into `characters.md`.
- Use the same voice sample for the whole series. If it changes, the audience will hear it.
- Show extras from behind, in wide shots or blurred, so faces outside the cast don't steal the scene.
- Write down the relationships clearly: who knows the lead's secret and who doesn't. That table decides who gets face-slapped in each episode.

## 6. The style bible: fix a few anchors

Draft `style.md` before work on episode 1 starts, and settle it from the finished episode 1.

**Formula**: pick **4–6 anchors** from the table and fix them; everything else is free per episode.

| Layer | Anchors you can fix | What can change per episode |
|---|---|---|
| Visuals | Art style and lighting (`STYLE`, `MOTION_PREFIX`), aspect ratio | Sets, time of day |
| Characters | Character sheets, voice samples, the character intro card style | Who appears |
| Edit | The form of the hook, how the payoff is handled (push-in + sound effect), the cliffhanger's freeze and text | Number of shots, pacing |
| Sound | Theme music, the cliffhanger sound effect | Music for each scene |
| Package | Cover layout, title format, title card | Hook copy |

- **Fix the cliffhanger and the cover above all**: those two are how the audience recognises the series.
- Fix too little and it doesn't read as one series; fix everything and it gets dull by episode 5.

## 7. One card per episode

Write one card per episode in `plan.md`, with fixed fields:

- **One line**: who gets face-slapped in this episode
- **Hook** (the picture and line of the first 3 seconds)
- **Push-down**: who does it, and how
- **Rise**: how the lead hits back, and what is revealed
- **Cliffhanger**: the last frame and its line
- **Characters and sets that appear**: new characters or sets need character sheets first (credits)
- **New characters / new looks**
- **Estimated number of shots and credits**

Write the cards for the whole series (at least the whole arc) before writing the script for episode 1. While writing the cards you often find two episodes with the same face-slap, or a cliffhanger that doesn't connect; fixing that now costs no credits.

## 8. Budget

A 1-minute episode is about 10–16 shots. With mostly multi-reference video, the video is roughly 800–1,500 credits per episode (the demo episode's 11 shots come to about 870), plus first-frame stills and retakes; character sheets and sets are made only once for the whole series. Make episode 1 first, audit the actual spend with `dreamfab/credits.py`, then estimate the whole series.

## Folders and naming

```
projects/<series>/
  plan.md               pitch, engine, arc table, episode cards, open questions
  style.md              style bible: fixed anchors, package format
  characters.md         profiles, looks, voice samples, relationship map
  cast/ sets/ props/    references shared by the whole series (project.py writes ../cast/A.png)
  voices/               voice samples
  music/ sfx/ fonts/    shared music, sound effects, fonts
  s1e01_<title>/        s{season}e{two-digit episode}_{title}: sorts in order
  s1e02_<title>/
```

Inside an episode:

```
s1e01_<title>/
  project.py          the whole episode (PROJECT_FORMAT.md)
  劇本_v1.md …        script; a new version gets a new number, never overwrite
  YouTube_SEO.txt     title, description, hashtags
  lines/              recordings for lip-sync shots
  kf/ clips/ jobs/ out/ covers/ …     generated files
  rejected/ clips_rejected/           rejected takes: move them here, don't delete
```

- Use two-digit episode numbers (`s1e01`); over 99 episodes, use three digits.
- **Name the folder before the first AutoIP job** (job files store absolute paths).
- Media stays out of git.

## Order of work for each episode

1. Write `劇本_v1.md` against `style.md`, `characters.md` and the episode's card.
2. Make character sheets for new characters, new looks and new sets first, **have the user approve them**, and write them into `characters.md`.
3. Episode 1 starts from [`examples/drama/demo/project.py`](../../../examples/drama/demo/project.py); from episode 2 on, copy the **previous episode's** `project.py`, keep `CAST`, `SETS`, `TYPO` and `RENDER`, and change `SCENES`, `SHOTS`, `EDITS` and `MUSIC`.
4. Finish it with [WORKFLOW.md](WORKFLOW.md).
5. Write `YouTube_SEO.txt` and make the cover in the package format of `style.md` ([PUBLISHING.md](PUBLISHING.md)).
6. Update: tick the episode card in `plan.md`; write down the problems you hit, and add the general ones to [LESSONS.md](LESSONS.md).

## Consistency check before publishing

- [ ] The hook connects to the last episode's cliffhanger
- [ ] This episode completes one push-down → rise
- [ ] Character looks and voices match `characters.md`
- [ ] The cliffhanger's freeze, text and sound effect are the same as earlier episodes
- [ ] Same cover layout and title format as earlier episodes
- [ ] The description links back to episode 1 and the series playlist

## Asking the agent

```text
Use dreamfab-drama to plan a 30-episode short drama: <premise>
```

The agent first asks about the subject, the engine, the arcs and which anchors you want fixed, writes `plan.md`, `characters.md` and `style.md` for your approval, and only then starts writing episode 1. It doesn't reuse the plot or characters of any existing work.

```text
Make episode 3 following projects/<series>/plan.md, starting from episode 2's project.py
```
