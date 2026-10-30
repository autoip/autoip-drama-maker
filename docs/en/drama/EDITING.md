# Short-drama editing principles

[中文](../../zh-TW/drama/EDITING.md) | English

Viewers of a vertical short drama keep a thumb on the screen and can swipe away at any moment. The edit has one job: **make the next second more watchable than this one**. This page is what to go by when cutting `EDITS`; the syntax is in [PROJECT_FORMAT.md](PROJECT_FORMAT.md#edit-list-edits).

## 1. The first 3 seconds: start in the middle of the conflict

- **The first row is the most intense moment**: a hand slammed on the table, a slap, an engagement broken off in public, a vicious line. Don't open on an empty shot, the title or someone walking in.
- The opening can be told out of order: first 2 seconds of the episode's climax, then 「三小時前」 ("Three hours earlier", `label=三小時前`).
- Put the title card (`title`) **after** the first conflict, over an empty shot or a transition; don't let the title block the opening.
- The first line must come within 3 s. An `auto` row already trims the silence before a line to 0.15 s.

## 2. Dialogue: shot/reverse shot

One person speaks per shot; the conversation is built in the cut:

```
S2_01 auto            # he says
S2_02 auto            # she replies
S2_03 auto zoom       # he closes in (push in)
```

- **Show whoever is speaking.** That's the default; the exception is the reaction shot below.
- Keep the gap between two lines under 0.3 s. In a quarrel, the lines crowd each other: trim the previous row's `dur` so it cuts the moment the last word ends, and move the next row's `in` to just before the speaker opens their mouth. Base rows play one after another, so the sound of two lines never truly overlaps; to hear one person while seeing the other, use a cutaway row (see section 3).
- When the same person speaks two lines in a row, cut to the other person's reaction in between; don't stay on the same face.
- Shot size follows the emotion: medium shots normally, close shots and close-ups for pressure, threats and guilt.

## 3. Reaction shots: the audience wants to see the one getting face-slapped

In a payoff drama, half the thrill is the person speaking and half is the person listening. Use a cutaway row (`^`) to put the listener's face over the speaker's voice:

```
S2_08 auto zoom sfx=hit         # C says the reveal line
^S2_09 0.3 0.9 @-0.9            # B's expression freezes (the sound is still C's line)
```

- **L cut**: cut to the listener before the line is finished (the cutaway row sits on the tail of the previous row, `@-0.9`).
- **J cut**: the next line is heard first, and the picture cuts over a little later (the cutaway row runs from the tail of the previous row into the start of the next one).
- 0.6–1.5 s is enough for a reaction shot; any longer and it turns into staring.
- The most important line in a scene gets at least one reaction shot.

## 4. Pacing

- 1.5–3 s per shot on average. A shot over 4 s needs a reason: one complete vicious speech, an expression the audience must see clearly.
- **Cut every "walks over", "sits down", "turns around"**, and go straight to the result.
- Every 15–20 s there must be new information or a new conflict; if there isn't, cut it.
- Only one place in an episode may go slow: the beat right after the reveal (freeze frame, slow push-in, reactions).

## 5. The payoff (爽點): reveal, comeback, face-slap (打臉)

At least one per episode. This moment must hit hard:

- `zoom`: push in within 0.25 s and hold for the whole row. Works for the line that reveals and for a shocked face.
- `sfx=hit`: a heavy hit, a heartbeat, breaking glass, a low boom. Sound lands more directly than picture.
- `flash`: a white flash, for the strongest hit only, once or twice an episode.
- **Change the music** at the payoff (`MUSIC` starts a new piece from this row), or cut the music dead one beat before the payoff and bring it back on the payoff.
- Right after the reveal, show the identity card: add `intro=A` to that row; the title on the card comes from `CAST["A"]["title"]` (the identity after the reveal). The card is part of the reveal, not an introduction.

## 6. The cliffhanger (卡點): stop on a question

- The last row stops on **the moment that has no answer yet**: someone turning around, a sentence cut off halfway, a door opening on someone we can't see, the other person's expression.
- `freeze=1.6 end`: freeze frame, desaturate, 「未完待續」 ("To be continued"). Freeze on a face, not on a frame blurred by motion.
- The line before the cliffhanger works best as a question or a threat, so the audience swipes to the next episode carrying the question.
- Keep the cliffhanger's form the same every episode (the same freeze, the same text, the same sound effect); the audience comes to recognise it as the series' signature.

## 7. Subtitles and cards

- Most vertical short dramas are watched muted: **every line needs a subtitle**, and the subtitle must never be later than the sound.
- One subtitle chunk is 14 characters or fewer, split at punctuation; never show two chunks at once.
- Character intro cards appear only at a character's first appearance or when an identity is revealed; three or four per episode at most.
- Keep text off the mouth: in a shot where the face sits low, raise `TYPO.sub_y` or use a shot with a different framing.

## 8. Sound

- Dialogue is loudest, music sits back. The music drops automatically when there is dialogue (ducking), but its own level still has to be set in `MUSIC`: mostly −14 to −20 dB.
- Generated clips come with their own ambience, which jumps at each cut. Covering a whole scene with one piece of music makes the jumps less noticeable.
- 3–6 sound effects per episode is enough; adding them everywhere gets noisy.

## 9. Checklist

- [ ] A conflict within the first 3 s, and the first line has already come
- [ ] The title card doesn't block the opening
- [ ] No gap longer than 0.3 s between two lines
- [ ] The most important line has a reaction shot
- [ ] At least one payoff (push-in, sound effect, music change)
- [ ] The last frame stops on a question, with 「未完待續」 over the freeze frame
- [ ] No `WARN` from the render
- [ ] Every line has a subtitle, and no subtitle covers a mouth
