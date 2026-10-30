# Planning a series: a whole season of MVs at once

[中文](../../zh-TW/mv/SERIES_PLANNING.md) | English

One MV follows [WORKFLOW.md](WORKFLOW.md). For a whole series (say a season of 4–8 episodes), plan the season with this page first, then make the episodes one by one.

This is a framework, not a template to copy. The **formula** covers what makes a season read as one series; the **freedom** is what each episode is about and how it looks. The framework says which boxes to fill, not what goes in them. A blank template is in [`examples/mv/series_template/`](../../../examples/mv/series_template/).

| Formula (every season has it) | Freedom (all yours) |
|---|---|
| A one-line series pitch | Subject, form, number of episodes |
| One axis that orders the episodes | Which axis, how the finale lands |
| A few fixed anchors | Which ones; everything else stays open |
| One song structure for the season | Which structure |
| One package for the season (thumbnail, title, description) | What the package looks like |
| One planning card per episode | The story, genre and look on each card |

## 1. Pitch the series in one line

**Formula**: `{subject} × {form}, one {variable} per episode`

- "A postman × folk-pop, one letter delivered per episode"
- "Seven kinds of weather × solo female vocal, one break-up per weather"
- "One old apartment building × a band, one decade's tenants per episode"
- "The last train × city pop, one passenger getting off at a different stop per episode"

**Freedom**: any subject, any form (solo, duet, band, instrumental), any number of episodes. If one line can't hold it, the subject is usually still too big.

## 2. The axis: give the episodes an order

**Formula**: find one thing that changes every episode and make it move **in one direction**. The last episode breaks it or completes it.

| Axis | How it orders the episodes |
|---|---|
| Time | Hours of a day, seasons, ages of a life, a stretch of history |
| Distance | Two people get closer, or further apart |
| Intensity | Emotion or energy rises every episode |
| Agency | The lead has more say over their own life every episode |
| Scale | One person → a family → a city → the world |
| Reverse | Told backwards from the ending; the last episode is the beginning |
| Puzzle | One clue per episode, assembled in the finale |

**Three ways to land the finale**: a reversal (what nobody could do, the last episode does), a completion (the last piece falls in), or a loop (the last shot returns to episode 1's first shot).

- **Say each episode's place on the axis in one word.** That word is the episode's pitch, and it doubles as the opening card and chapter title.
- **Use a new axis for the next season.** Same subject, new axis: that's a new season.

## 3. The series style bible: fix a few anchors, free the rest

Draft `style.md` before episode 1 and settle it from the finished episode. Check it before writing the lyrics, prompts or thumbnail of every later episode.

**Formula**: pick **3–5 anchors** from the table and fix them; everything else is free per episode.

| Layer | Anchors you can fix | What can change per episode |
|---|---|---|
| Visuals | Art style, time of day and light, a recurring object or place, transition form, aspect ratio | Lead colour, setting, symbols |
| Characters | The same lead, the same face, styling rules | Identity, costume |
| Sound | Song structure, vocal line-up, one sonic signature (the same instrument, the same hummed line) | Genre, BPM, key |
| Subtitles | Font, layout rules, keyword colour | Effects, which words change colour |
| Package | Thumbnail layout, title format, description order | Hook, copy |

- **The package is the anchor that matters most.** Viewers spot a series on the home page by its thumbnail and title.
- **If one layer is fixed, let another change a lot.** Fixed visuals: change the genre every episode. Fixed genre: change the look every episode. With every layer fixed, viewers tire by episode 3.
- **Too few anchors** (only the title format) and it doesn't read as a series; **too many** (look, cast and genre all the same) and every episode feels like the same video.
- **Put everything that changes per episode in one table and fill in the whole season at once.** Check that no two episodes in a row share a colour, genre or BPM.
- **Use an accent colour only at emotional peaks**, never over the series palette.

## 4. Song structure: one kind for the whole season

With a fixed structure, viewers wait for the same moment in every episode.

**Formula**: pick one structure and keep it all season.

| Structure | How it works |
|---|---|
| Question and answer | Chorus 1 asks; chorus 2 answers on the same melody, turning the question around |
| Shifting hook | Every chorus has the same line; the last one changes one word |
| Chapters | Each section is a scene or a moment in time, like acts |
| Bookends | Every episode opens with the same line and ends differently |

**Freedom**: section lengths, who sings, language, whether there is spoken word or an instrumental passage.

General lyric rules:
- **Don't make the verses too regular.** Lines of equal length on one rhyme sound like chanting; uneven, spoken-style lines sound like a person talking.
- **Use quotations (allusions, famous lines, dialogue) only in the chorus or at turning points**; keep the rest plain.
- **Write the lyrics in Suno format** as each episode's `歌詞_v*.txt`: Title, Style, Exclude, then tagged Lyrics. Each section tag says who sings and in what voice, e.g. `[Verse 1: Male Vocal Only, Warm Tenor, Gentle]`, so parts don't go to the wrong singer.

## 5. One planning card per episode

`research.md` has one card per episode with fixed fields:

- **One word**: the episode's place on the axis
- **Inspiration and source**: real events, allusions, works; note anything disputed
- **Story**: three to five sentences
- **Emotional arc**: five steps at most
- **Key object**: one, used for the thumbnail and the opening
- **Palette**: opening, turn, ending
- **Genre**: lead genre × one clashing element
- **Last shot**
- **To check**: facts to verify, later written into the description

Write the whole season's cards before the first song. That is when you notice two episodes sharing an object or a palette, and fixing it there costs no credits.

## 6. Genre: lead genre × one clashing element

**Formula**: one lead genre per episode, plus one element from the story that clashes with it (an instrument, a field recording, a singing style, a language).

- Pick the lead genre for the story. The clash is the hook: trap with a string quartet, synth-pop with a church organ, lo-fi with a field recording.
- Keep the clashing element to one or two, used as a hook; pile on more and the episodes blur into one song.
- **Freedom**: you can also keep one genre all season and change the look every episode instead (see section 3, "If one layer is fixed, let another change a lot").

## 7. Callbacks and the finale

- **Let one object or one line appear in two episodes**; viewers who saw the earlier one will recognise it.
- **Link episode 1 in every description**, and say which episode this is.
- **Leave a line for the next season in the finale.**

## 8. Characters

- **Freedom**: one lead for the whole season, or a new cast each episode.
- With one lead, put episode 1's character sheet in every episode's `ref/` and build each later look from that face, changing only costume and setting.
- **Write a `角色.md` (cast notes) per episode**: which candidate was approved, which costume goes in which shots, whether two people may share a frame.
- **Keep close-ups to one person**; two people together in wide shots or from behind. Two-person close-up stills are hard to keep stable (see [LESSONS.md](LESSONS.md)).
- **Suggest death, violence and other sensitive moments with objects and empty shots**; don't show them directly.

## Folders and naming

```
projects/<series>/
  style.md                  series style bible: fixed anchors, per-episode table, package format
  research.md               pitch, axis table, episode cards, open questions (one part per season)
  s1e1_<title>/             s{season}e{episode}_{title}: sorts in order, across seasons too
  s1e2_<title>/
  s2e1_<title>/
```

Inside an episode:

```
s1e1_<title>/
  project.py          the whole episode (see PROJECT_FORMAT.md)
  歌詞_v1.txt …       lyrics; a new version gets a new number, never overwrite; style.md says which is final
  角色.md             cast notes: approved art, costumes, two-person rules
  YouTube_SEO.txt     title, description, chapters, tags
  thumbs.py           thumbnails in the series layout
  ref/                the series lead's character sheet
  audio/ chars/ kf/ clips/ jobs/ out/ …      media and generated files
  kf_rejected/ clips_cand/                   rejected and candidate takes: move them here, don't delete
```

- **Use `s1e1_` from the start even if you plan one season.** A second season then needs no renaming.
- **Name the folder before the first AutoIP job.** Job files (`jobs/*.json`) store absolute paths, so renaming after submitting breaks resuming.
- **Move rejected takes, don't delete them.** Later you can still look up why one was rejected.
- Media (`ref/`, `chars/`, `kf/`, `clips/`, `audio/`, `out/`) stays out of git.

## Order of work for each episode

1. Write `歌詞_v1.txt` against `style.md` and the episode's card.
2. Generate the song and listen; save lyric changes as `v2`, `v3`.
3. Make the character art, write `角色.md`, and **have the user approve it**.
4. Episode 1 starts from [`examples/mv/demo/project.py`](../../../examples/mv/demo/project.py); from episode 2 on, copy the **previous episode's** `project.py` and change the story fields, keeping the subtitle theme, thumbnail layout and `EDITS` structure.
5. Finish it with [WORKFLOW.md](WORKFLOW.md): audio, storyboard, keyframes, video, QC, edit, subtitles, render.
6. Write `YouTube_SEO.txt` and the thumbnail in the package format of `style.md` ([PUBLISHING.md](PUBLISHING.md)).
7. Update: tick the episode in the `style.md` table and note the final lyric version; write down this episode's problems, and add the general ones to [LESSONS.md](LESSONS.md).

## Consistency check before publishing

- [ ] Every anchor fixed in `style.md` is in this episode
- [ ] The layer that changes is really different from the previous episode
- [ ] Same song structure as earlier episodes
- [ ] Same thumbnail layout, title format and description order as earlier episodes
- [ ] The description links episode 1 and says which episode this is
- [ ] The facts to check are written into the description
- [ ] Both the full version and the vertical short are done

## Asking the agent

```text
Use dreamfab-mv to plan a 6-episode MV series about <subject>
```

The agent first asks about the subject, the axis and which anchors you want fixed, writes `research.md` (pitch, axis table, episode cards) and `style.md` for your approval, and only then starts episode 1. It doesn't apply the style of any existing series.

```text
Make episode 3 following projects/<series>/style.md, starting from episode 2's project.py
```
