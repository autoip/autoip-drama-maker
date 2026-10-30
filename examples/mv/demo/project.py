"""Demo project: a fictional 70-second gothic metal duet, 《夜之劇場 NIGHT THEATRE》.

This file is the single source of truth for one MV. Everything else (storyboard.json, shots.json, job files, the
render) is generated from it. Copy the folder, replace the song, the character images and this file.
Times are song seconds. Supply yourself: song.mp3, chars/*.png, fonts/ (see docs/en/SETUP.md).
"""

NAME = "night_theatre_MV"          # output file stem
SONG = "song.mp3"

# ---------------------------------------------------------------- look
STYLE = ("dark gothic symphonic metal music video still, gothic opera house, candlelight, storm, "
         "cold blue moonlight with amber firelight and blood crimson accents, drifting smoke and embers, cinematic lighting, "
         "photorealistic, highly detailed, wide 16:9")
MOTION_PREFIX = "史詩交響哥德金屬 MV，暗黑電影感，燭火、煙霧、雷雨，節奏強烈。"  # prepended to every image-to-video prompt
BAND_STAGE = "member of a gothic metal band performing on a gothic opera house stage"
NO_FACES = "no visible human faces, faces hidden by porcelain masks or shadow"  # for B-roll extras: keeps the cast fixed

# ---------------------------------------------------------------- cast (fixed line-up)
# kind: vocal -> lip-sync (the pad is cropped around the face); band -> whole image is the reference
# role: (english, native) name plate shown in the interlude when the cut lands on this player
CHARS = {
    "FV": dict(file="chars/soprano.png", name="主唱・女高音", kind="vocal", role=("SOPRANO", "女高音"),
               desc="female singer with very long silver-white hair, silver circlet, pale skin, white lace gown"),
    "MV": dict(file="chars/growl.png", name="主唱・嘶吼", kind="vocal", role=("VOCALS", "嘶吼"),
               desc="male singer with slicked-back long black hair, heavy black eyeliner, black high-collar coat with silver embroidery"),
    "DR": dict(file="chars/drummer.png", name="鼓手", kind="band", role=("DRUMS", "鼓手"),
               desc="muscular male drummer with a high black braid, sleeveless black leather vest, black double-bass drum kit"),
    "GT": dict(file="chars/guitarist.png", name="吉他手", kind="band", role=("GUITAR", "吉他"),
               desc="male guitarist with spiky black hair and one silver streak, black leather long coat, black flying-V guitar"),
}

# lip-sync scenes: (id, char, scene prompt, motion prompt (zh), caption)
LS_SCENES = [
    ("L_FV_stage", "FV", "singing with mouth open on a gothic opera house stage in a single cold moonlight spotlight, white smoke at her feet",
     "在冷白月光聚光燈下的舞台高歌，白霧在腳邊流動，長髮輕揚", "月光聚光燈下的女高音"),
    ("L_MV_fire", "MV", "gripping a microphone stand and screaming, close-up, flames and sparks exploding behind him on a dark stage",
     "緊握麥克風架嘶吼，背後火焰與火花爆開，頭髮被熱風吹動", "火焰前嘶吼"),
]

# band shots: (id, char or [chars], caption, prompt, motion). A list = group shot (see group_still.py).
BAND = [
    ("D1", "DR", "鼓手雙踏狂擊", "the drummer pounding the double-bass drum kit at full speed, drumsticks blurred, smoke and backlight, medium shot",
     "鼓手全速擊鼓，鼓棒快到模糊，汗水飛濺，鈸片閃光"),
    ("G1", "GT", "吉他手 solo", "the guitarist shredding a solo at the edge of the stage, leaning back, fire columns behind him",
     "吉他手在舞台邊緣狂飆 solo，身體後仰甩頭，火柱在身後噴發"),
    ("W1", ["MV", "FV", "GT", "DR"], "樂團合照", "", "四位成員肩並肩的腰上中景，鏡頭緩慢推近，身後火光與煙霧"),
]
# only used when a group shot has no approved still: multi-subject prompt, @圖片 N = Nth member above
MULTI_PROMPT = {
    "W1": ("哥德金屬樂團在燭光與煙霧籠罩的歌劇院舞台上演出，近距離合照式中景，成員都是高挑修長的成年人。"
           "@圖片 1 在正中央嘶吼；@圖片 2 在他右側高歌；@圖片 3 在左側彈吉他；@圖片 4 在後方高台打鼓。\n"
           "MUSIC & SFX: 沉重的交響金屬，沒有對白。\n"
           "SHOT 1: 腰部以上的中景，臉都很大很清楚，略為仰角，鏡頭緩慢推近。不要全身，不要遠景。"),
}

# story B-roll (text-to-image -> image-to-video): (id, caption, prompt, motion)
BROLL = [
    ("B01", "暴風雨中的劇院", "a colossal gothic opera house on a cliff in a violent thunderstorm at night, lightning",
     "閃電劈落劇院尖塔，烏雲翻滾，鏡頭緩慢推近"),
    ("B02", "紅幕緩緩拉開", "a giant blood-red velvet theatre curtain slowly parting, a single spotlight beam, smoke",
     "巨大紅絨布幕緩緩拉開，聚光燈打下，煙霧翻湧"),
    ("B03", "面具流下一滴淚", f"extreme close-up of a white porcelain theatre mask with a single glass tear rolling down, {NO_FACES}",
     "瓷面具流下一滴玻璃淚，燭光閃爍"),
    ("B04", "包廂紅酒乾杯", f"crystal glasses of red wine clinking in a gilded private opera box, candlelight, wine splashing, {NO_FACES}",
     "鍍金包廂裡水晶杯紅酒碰杯，酒液飛濺"),
    ("B05", "水晶吊燈墜落", "a giant crystal chandelier crashing down in a burning opera house, sparks and glass shards",
     "巨大水晶吊燈從天花板墜落，玻璃與火花炸開"),
    ("B06", "黎明廢墟", "the smoking ruins of a burned opera house at dawn, pale light through the broken roof, ash falling",
     "黎明的冷光照進燒毀劇院，灰燼飄落，鏡頭緩慢拉遠"),
]

# lip-sync takes: (LS id, scene, a0, dur, voice). a0/dur in song seconds (max ~30 s per take);
# voice = which isolated vocal track drives the mouth (AUDIO["voices"])
LIPSYNC = [
    ("LS01", "L_FV_stage", 11.8, 29.0, "F"),
    ("LS02", "L_MV_fire", 11.8, 29.0, "M"),
    ("LS03", "L_FV_stage", 39.8, 22.0, "F"),
    ("LS04", "L_MV_fire", 39.8, 22.0, "M"),
]

# sections: (name, (a, b), typography note, lines [(t, text, voice)], shot ids)
# name = "<key>：<subtitle>"; the key selects the act label and set pieces in TYPO
SECTIONS = [
    ("序曲：暴風雨中的劇院", (0.0, 12.0), "片名從黑暗中燒出", [], ["B01", "B02"]),
    ("主歌：燭火與面具", (12.0, 28.0), "女聲滑入、男聲砸入", [
        (12.0, "燭火照亮空蕩的舞台", "F"), (16.0, "面具背後藏著誰的謊言", "M"),
        (20.0, "掌聲響起又落下", "F"), (24.0, "黃金鋪滿通往王座的路", "M")], ["LS01", "LS02", "B03"]),
    ("間奏：樂團登場", (28.0, 40.0), "樂手名牌", [], ["D1", "G1", "W1"]),
    ("副歌：夜之劇場", (40.0, 56.0), "片名巨型字幕＋布幕", [
        (40.0, "夜之劇場，今夜為誰開幕", "F"), (44.0, "淚水是最昂貴的道具", "M"),
        (48.0, "舉杯乾杯，敬這場謊", "M"), (52.0, "幕落之前一切都會爆炸", "M")], ["LS03", "LS04", "B04", "B05"]),
    ("尾聲：灰燼", (56.0, 70.0), "片名淡出", [], ["B06"]),
]

# ---------------------------------------------------------------- audio (paths relative to this folder)
AUDIO = dict(beats="audio/beats.json", vocals="audio/vocals.wav", words="audio/words.json",
             voices={"F": "audio/vocals_F.wav", "M": "audio/vocals_M.wav"})
VOICE_SPANS = {"F": [(12.0, 16.0), (20.0, 24.0), (40.0, 44.0)]}  # from voice_probe.py; "M" gets the rest

# ---------------------------------------------------------------- edits
# rows: "start src [offset] [flash]"; '|' or newline separated; '#' comments; "@short" pastes another edit's rows.
# Lip-sync rows need no offset (it comes from align.json). Cuts within 0.08 s of a beat snap onto it.
EDITS = {
    "short": dict(cut=38.0, end=58.0, open_s=2, end_s=3, suffix="_short", shots="""
        38.0 W1 0 flash | 40.0 LS03 0 flash | 42.4 B04 | 44.0 LS04 | 46.0 D1 1 | 47.0 LS04
        48.0 B04 1.5 flash | 49.6 LS03 | 51.2 G1 | 52.0 LS04 0 flash | 54.0 B05 0 flash | 56.0 B06
    """),
    "full": dict(cut=0.0, end=70.0, open_s=4, end_s=6, shots="""
        0.0 B01 | 6.0 B02                                   # prologue: long shots, let the title breathe
        12.0 LS01 0 flash | 14.0 B03 | 16.0 LS02 | 18.4 LS01 | 20.0 LS01 | 22.0 B03 2 | 24.0 LS02 | 26.0 D1
        28.0 D1 1 flash | 31.0 G1 0 flash | 34.0 W1 0 flash   # interlude: one player per cut, name plates
        @short
        62.0 B06 2                                          # epilogue: slowest shot last
    """),
}

# ---------------------------------------------------------------- render
RENDER = dict(
    fps=25,
    crop={},                       # e.g. {"LS03": "crop=1024:576:180:0"} for a clip with burned-in captions
    open_card="cards/open.jpg",    # optional promo / title cards; missing files are skipped
    end_card="cards/end.jpg",
    lang="zh-TW",                  # SRT language suffix
)

# ---------------------------------------------------------------- kinetic typography (mv/epic.py)
TYPO = dict(
    font="PS Serif Black", font_file="fonts/PSSerifBlack.ttf", font_scale=1.45,  # see make_static_font.py
    latin="Noto Serif",
    title="夜之劇場", title_en="NIGHT THEATRE", tagline="a gothic metal duet", genre="交響哥德金屬",
    acts={"序曲": "PROLOGUE", "主歌": "ACT I", "間奏": "INTERMISSION", "副歌": "ACT II", "尾聲": "EPILOGUE"},
    specials={"序曲": "intro", "間奏": "plates", "尾聲": "outro"},  # also "finale": title card over an instrumental climax
    band_plate=("THE BAND", "樂團"),
    readings={"道具": "dào-jù", "開幕": "kāi-mù"},  # romanized reading under rhyme words at the end of a line
    gags=[
        dict(type="title_line", match="夜之劇場"),
        dict(type="color", match="黃金", chars="黃金", color="F2C55C"),
        dict(type="coins", match="黃金"),
        dict(type="clap", match="掌聲", char="聲", word="CLAP"),
        dict(type="tear", match="淚水", char="淚"),
        dict(type="clink", match="乾杯", char="杯"),
        dict(type="explode", match="爆炸"),
    ],
)
