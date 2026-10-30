# Emotional beat editing

[中文](../../zh-TW/mv/EMOTIONAL_BEAT_EDITING.md) | English

> This document is also a Claude Code / Codex skill: `skills/emotional-beat-editing/`, installed by the one-line installer.

Regular beat-cutting is "cutting to hit the beat"; emotional beat editing is "cutting to tell a story and build emotion."
First learn to cut precisely on the beat, then learn to **deliberately miss it**: when a whole video cuts precisely on the beat, a sudden shot that doesn't cut, doesn't follow the beat and just holds
is often the emotional peak of the entire piece.

## Four core principles

### 1. Space and breath (breathing cuts)
- When the music drops from a noisy chorus into a quiet passage (bridge, the empty beat before an interlude, the singer taking a breath, right after a heavy line), **deliberately don't cut**.
- Hold the same shot longer (3–6 s or more) so the audience can absorb the emotion, creating the suffocating feeling of "the air suddenly going quiet."
- Implementation: at `breath` / `drop` points in the emotion map, put **no cut** in the edit list; let the previous shot continue, picking slow-motion footage or slowing it with `setpts` if needed.

### 2. Sound-design pre-roll (Sound Design Beat)
- 0.5–1 s before a downbeat lands, bring in an ambient or transition sound (a lighter clicking, a deep breath, a heartbeat, a water drop, the tail of a bell, static before thunder).
- The ear is caught by the sound first, then the picture bursts in on the downbeat — far more impact than simply cutting on the beat.
- Implementation: keep an `sfx` list next to the edit list, `[(downbeat time - 0.6, sound file, volume dB)]`, and mix it under the song with `adelay` + `amix` at render time (see the ffmpeg recipes below).
- Sound effects must come from the user or from a royalty-free source you're sure you can use; **don't download sound effects of unknown origin yourself**. With no sound effects, skip this technique and use a visual pre-roll instead (e.g. a white/red flash 0.3 s before the downbeat).

### 3. Dynamic contrast (J-Cut / L-Cut)
- **J-Cut (sound leads)**: the picture is still on the previous scene while the next scene's sound (its ambience, choir, laughter) comes in first.
- **L-Cut (picture leads)**: the picture has already cut to the next scene while the previous scene's sound still echoes.
- The offset between what you see and what you hear creates contrast, irony or a sense of loss.
- In an MV the song itself is continuous, so J/L-cuts mainly apply to the **sound-effects layer** and the **subtitle layer**:
  - J: the next scene's sound effect / the next lyric line appears 0.3–0.8 s early, and the picture cuts a little later.
  - L: the picture has cut away, but the previous scene's sound tail (bell, thunder, applause) or the afterimage of the previous lyric line (burning to ash, fading out) stays 0.5–1 s longer.
- Especially effective with satirical lyrics: the lyric sings 為民 ("for the people") while the picture has already cut to a private room full of red wine (L-cut subtitle afterimage).

### 4. Shot scale and emotional progression (Scale Match)
| Emotional stage | Shot language | Cut density |
|---|---|---|
| Setup / low | Extreme close-ups: a tear, a hand, an eye, out-of-focus lights, object details | Sparse (every 2–4 s or longer) |
| Build / turn | Medium shots, waist-up, slow push-ins | Medium (every 1–2 bars) |
| Chorus burst / peak | Extreme wide shots, full band, aerials, fast camera moves, explosions and fire | Dense (every 1–2 beats), but keep one or two long shots as anchors |
| Ending | Back to close-ups or empty frames, camera pulling away | Sparse; the last shot is the longest |

Prompt the generated footage according to this table from the start: setup sections need `extreme close-up` shots, climaxes need `wide shot / aerial / fast camera`.

## Narrative editing techniques (from practice)

These come from the edit feedback on 《楚歌》 (Farewell My Concubine in Peking-opera dress × symphonic metal). <!-- public-ok -->

### Costume progression: change costume at the lyric's turning point
- One look from start to finish makes the video flat. Change costume on the turning line — e.g. at "no more powder, into armor", court robes become battle armor.
- On that line, cut to a story shot of the change itself (fastening the armor, the cape opening) as the transition; from then on every lip-sync uses the new look.
- Prepare two sets of lip-sync stills: one before the turn, one after, with the same face and makeup.

### Dying flashback montage: a life replayed before death
- Right before a character dies or makes the fatal decision, flash back through the story shots used so far, on the beat.
- Accelerate: one cut every two beats, then one every beat. Roughly follow story order; the last beats can repeat key images.
- Pick each clip's `offset` from its cleanest seconds; add `flash` on the big moments (handing over the sword).
- End the montage on the decisive shot (eyes closed, sword in hand), then cut to the consequence (the sword falling).

### Don't return to lip-sync after the key line
- Once the chorus's key line lands (e.g. "my strength could uproot mountains"), hand the picture to story and memory, and don't cut back to the singing face.
- At the emotional peak, watching the performance pulls the audience out of the story.

### Close-up fatigue in the vertical cut
- The vertical frame is cropped from 16:9 material, about 2.7× larger, so every lip-sync shot is a huge face.
- Keep open-mouthed long-note close-ups to about 2 s, and insert a story shot every 2–4 s even early in the song, or it feels stiff.
- Make subtitles smaller in the vertical cut (lower `font_scale`), and keep horizontal lines above the head and below the chest, off the face.

### Lip-sync and story shots can use different art styles
- Semi-realistic portraits lip-sync better; story shots can be gongbi painting. Intercutting the two works.
- The cost: the same character's headdress and costume details differ between the two — tell the decision-maker up front.

### Think through the story order of the short and full cuts separately
- A short cut can let the character die on its last line; if the full song has a bridge after that (e.g. the sword-handing exchange), move the death after the bridge.
- Don't paste the short cut's ending into the full cut with `@short` before checking the story order.

## Workflow (with Dreamfab's MV line)

1. **Run the emotion map**:
   ```
   python mv/audio/emotion_map.py audio/song.wav audio/beats.json [audio/vocals.wav] > audio/emotion.txt
   ```
   It outputs, per bar, the energy, emotional stage (low / build / peak / drop), vocal breath points (breath), energy drop points (drop),
   hit points (hit), and a **suggested cut density**. Requires librosa (`pip install -r requirements.txt`). When installed as a skill, the script is also under this skill's `scripts/`.
2. **Draw the emotion curve before placing shots**: label the sections "setup → build → burst → space → burst again → ending", and decide each section's shot scale (principle 4).
3. **Write the edit list** (`EDITS` in `project.py`, one row per shot: `start src [offset] [flags]`):
   - `peak` sections: cut points on downbeats (beat snap ≤ 0.08 s), a cut every one or two beats.
   - `low` sections: cut only after a bar or more; prefer close-ups and long shots.
   - `breath` / `drop` points: **no cut**; let the previous shot carry through.
   - In each major section, find **one** place to deliberately not cut on the beat: usually the space on the last beat before a burst, or the first quiet bar after the climax.
   - `hit` (the strongest downbeats): add the `flash` flag or a speed-ramp cut.
4. **Speed-ramp cuts**: slow motion before the downbeat (`setpts=2.5*PTS`), snapping back to normal speed on the hit, so the "moment" of the action (a punch, a head whip, an explosion, a bell strike) lands with the sub-bass.
   Do it by splitting the same clip into two segments: a slow segment before the downbeat + a normal-speed segment after it.
5. **Subtitles are part of the beat too**:
   - Burst sections: words slam in, shake, flash white.
   - Space sections: words fade in slowly, or no words at all.
   - J/L-cut: subtitles early or late, for irony.
6. **Check**: grab frames and look at the "cut distribution":
   - The climax should have the densest cuts; setup and space sections should be clearly sparser.
   - The whole video should have at least 2–3 shots longer than 3 seconds.

## ffmpeg recipes

**Sound-effect pre-roll layer** (mixed under the song track):
```
-i song.mp3 -i sfx_lighter.wav -i sfx_breath.wav -filter_complex
"[1:a]adelay=12400|12400,volume=-6dB[s1];[2:a]adelay=30150|30150,volume=-9dB[s2];
 [0:a][s1][s2]amix=inputs=3:duration=first:normalize=0[a]"
```
(`adelay` is in milliseconds and must use video time: subtract the cut and add the opening card's duration.)

**Pull-back before the space** (duck the music for 0.5 s before the downbeat, leaving only the breath sound):
```
[0:a]volume='if(between(t,29.6,30.1),0.15,1)':eval=frame[a0]
```
Only change the song's own volume with the user's consent; by default touch only the sound-effects layer.

**Speed-ramp cut** (downbeat at 1.2 s into the clip):
```
seg A: -ss 0 -t 1.2 -i clip.mp4 -vf "setpts=2.5*PTS"      → 3.0 s of slow motion
seg B: -ss 1.2 -i clip.mp4 -vf "setpts=PTS"               → bursts out at normal speed
```
When the two are joined, B's first frame must land on the downbeat.

**Stretching a long shot**: when a clip is too short, slow it with `setpts=<factor>*PTS` (a factor ≤ 1.8 still looks natural),
or freeze with `tpad=stop_mode=clone`. Don't freeze on the last 0.35 s of an AI video — it's often noisy.

## Golden rules
- Make sure 80% of cuts are precisely on the beat; leave the other 20% for deliberate off-beat moments.
- Every pause needs a reason: a heavy line just sung, an emotional turn, the inhale before the climax.
- A climax isn't just about cutting the most: keep a steady anchor shot within the rapid cuts (lead-singer close-up, full-band wide) so the audience knows where to look.
- The ending must always be slower than the opening.
