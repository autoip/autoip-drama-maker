"""Demo episode: the structure of a one-minute vertical short drama, with no story in it.

Every story element is a placeholder in <angle brackets>: the cast (A lead, B opponent, C the one who turns it),
the sets, the lines and the actions. The shots, kinds, references and the edit are real and show every field.
Copy the folder to projects/<series>/s1e01_<title>/ (projects/ stays out of git) and write your own story there.
Supply yourself: cast pictures (or let `make_jobs.py P refs` draw them from `prompt`), voice recordings, music, sound
effects, fonts (see docs/en/SETUP.md). Times in EDITS are seconds of each clip; the episode timeline follows from them.
"""

NAME = "demo_s1e01"                # output file stem
TITLE = "<劇名>"                   # series title (title card)
EPISODE = 1
ASPECT = "9:16"                    # vertical short drama; "16:9" for landscape

# ---------------------------------------------------------------- look
STYLE = "cinematic still from a modern live-action drama, natural light, clean tones, shallow depth of field, photorealistic"
MOTION_PREFIX = "Modern live-action drama, cinematic, natural light, clean image."  # art style only, in English
SFX = "No music, only ambience and the sounds of the action."   # I2V / K shots; music is added in the edit
NEG = "text, letters, words, logo, watermark, subtitles, extra fingers, deformed hands, nude, nsfw, childlike"

# ---------------------------------------------------------------- cast (fixed looks; one costume per arc)
# file: the reference picture (yours, or drawn from `prompt` by make_jobs.py P refs) - keep one look per character
# voice: the voice sample sent with every line this character speaks (voices.py cuts it from voice_src)
# title: the role line on the character intro card; color: optional subtitle colour for this speaker
CAST = {
    "A": dict(name="<A 的名字>", file="cast/A.png", title="<A 揭露後的身分>",          # lead: pushed down, then rises
              desc="<A's look in English: age, hair, face, one outfit>", prompt="neutral expression",
              voice="voices/A.wav", voice_src="voices/raw/a.m4a"),
    "B": dict(name="<B 的名字>", file="cast/B.png", title="<B 的身分>",                # opponent: does the pushing
              desc="<B's look in English: age, hair, face, one outfit>", prompt="confident expression",
              voice="voices/B.wav", voice_src="voices/raw/b.m4a"),
    "C": dict(name="<C 的名字>", file="cast/C.png", title="<C 的身分>",                # the one whose arrival turns it
              desc="<C's look in English: age, hair, face, one outfit>", prompt="calm expression",
              voice="voices/C.wav", voice_src="voices/raw/c.m4a"),
}
# sets: one approved plate per location (make_jobs.py P refs draws it from `prompt` / `desc`); name = how prompts call it
SETS = {
    "ROOM": dict(name="<室內場景>", file="sets/ROOM.png", desc="<the main interior in English: room, furniture, light, time of day>"),
    "EXT": dict(name="<外景>", file="sets/EXT.png", desc="<the exterior in English: building or place, time of day>"),
}
PROPS = {
    "ITEM": dict(file="props/ITEM.png", desc="<the one object the conflict turns on, in English, with no writing on it>"),
}

# ---------------------------------------------------------------- script
# scenes: (id, set, heading). The set is in every multi-reference shot of the scene (and named in every SHOT line).
SCENES = [
    ("S1", "EXT", "<日／夜>，<外景>"),
    ("S2", "ROOM", "<日／夜>，<室內場景>"),
]

# shots, in story order. kind:
#   M   (default) multi-reference video: references (speaker, cast, @KEYs in act, props, the set) -> video with the
#       line spoken in the speaker's voice. One speaker per shot; 5-10 s; about 4 characters a second.
#   LS  lip-sync: still kf/<id>.png (from `still`) + your recording lines/<id>.wav. Long or exact lines.
#   I2V image-to-video from still kf/<id>.png: inserts, establishing shots, no dialogue.
#   K   keyframe video from kf/<id>.png to kf/<to>.png: doors, transitions, A -> B moments (6 / 10 / 15 s).
# say = (speaker, line, delivery); act = action and camera; @KEY = that reference; secs = clip length.
# act and delivery in English, no he / she (name them with @KEY): the model speaks Chinese narration with the line.
SHOTS = [
    dict(id="S1_01", scene="S1", kind="I2V", still="<the exterior as an establishing shot, in English>",
         act="Static camera, <how what is already in the frame moves>."),
    dict(id="S2_01", scene="S2", cast=["A"], props=["ITEM"], say=("B", "<B 當眾發難的第一句>", "<delivery>"),
         act="@B <confronts @A, using @ITEM>, medium shot."),                          # the hook
    dict(id="S2_02", scene="S2", say=("A", "<A 平靜的回應>", "<delivery>"),
         act="@A <reacts and moves after hearing it out>, close-up, steady camera."),
    dict(id="S2_03", scene="S2", say=("B", "<B 加壓的一句>", "<delivery>"),
         act="@B <closes in>, close-up, steady camera."),
    dict(id="S2_04", scene="S2", cast=["A"], act="@A <a silent reaction hinting at a trump card>, extreme close-up, steady camera."),
    dict(id="S2_05", scene="S2", kind="K", to="S2_06", secs=6,
         still="<where C comes in, before C appears, in English>",
         act="<the change before C appears, e.g. the door is pushed open>."),
    dict(id="S2_06", scene="S2", kind="I2V", cast=["C"],
         still="<C entering, medium shot, in English>",
         act="@C <walks in>, the camera slowly pulls back."),
    dict(id="S2_07", scene="S2", cast=["C"], say=("B", "<B 看到 C 之後態度一變的一句>", "<delivery>"),
         act="@B <goes to meet @C>, medium shot."),
    dict(id="S2_08", scene="S2", cast=["B", "A"], say=("C", "<C 揭露 A 身分的那一句>", "<delivery>"),
         act="@C <walks past @B toward @A>, @B frozen in the background, medium shot."),            # the payoff
    dict(id="S2_09", scene="S2", act="@B <the face of someone just proven wrong>, extreme close-up, steady camera."),
    dict(id="S2_10", scene="S2", kind="LS", say=("A", "<A 留下懸念的最後一句>", "<delivery>"),
         still="<A's last look before the cliffhanger, medium close-up, in English>"),  # the cliffhanger
]

# ---------------------------------------------------------------- edit
# rows: "src [in|auto] [dur] [flags]"   cutaway: "^src [in] [dur] @at" (picture only, `at` s into the row above;
# negative = before its end). A bare id is `auto`: trimmed to its line from speech.json (run speech.py first).
# flags: flash  black  zoom[=1.15]  mute  title  end[=text]  freeze=S  sfx=name  intro=KEY  label=text
EDITS = {
    "main": dict(shots="""
        S2_01 auto flash intro=B            # cold open: the conflict is the hook (first 3 s decide the swipe)
        S2_02                               # the answer
        S2_03 auto zoom
        ^S2_04 0.8 1.0 @-1.0                # L cut: A's silent reaction over the end of B's line
        S1_01 0.5 1.6 title                 # title card over the exterior
        S2_05 0 2.6 sfx=door                # the change: the keyframe clip cuts to its last frame around 65 %
        S2_06 0.4 2.2 intro=C
        S2_07
        S2_08 auto zoom sfx=hit             # the payoff
        ^S2_09 0.3 0.9 @-0.9                # B's face as the line lands
        S2_10 auto intro=A freeze=1.6 end   # the last line, freeze, 未完待續
    """),
}
# music cues: (file in music/, from row, to row (None = the end), gain dB). Ducked under the dialogue automatically.
MUSIC = [
    ("tension", "S2_01", "S2_05", -18),
    ("reveal", "S2_08", None, -15),
]

# ---------------------------------------------------------------- render
RENDER = dict(
    fps=25,
    pad=(0.15, 0.35),              # auto rows: seconds kept before / after the line
    hold=2.0,                      # auto rows without a line: seconds used
    lang="zh-TW",                  # SRT language suffix
    lufs=-16,                      # loudness of the mix
)

# ---------------------------------------------------------------- subtitles and cards (dramakit/subs.py)
TYPO = dict(
    font="DK Sans Black", font_scale=1.45,     # see make_static_font.py (libass needs a static weight)
    size=54, max_chars=14,
    end_text="未完待續",
    accent="F2C55C",
)
