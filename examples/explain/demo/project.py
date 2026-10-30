# Demo explainer for the explain line (說・解說影片): a shortened episode about the MV "Luo River" (洛川,
# https://youtu.be/OlIQYvfwZhA), with every project.py field in use. Paths are relative to this folder.
# narration.py, make_images.py and render.py read it; mv/youtube_upload.py reads NAME, EDITS, RENDER and YouTube_SEO.txt.
LINE = "explain"                      # the library serves the folder as plain files
NAME = "demo_luoshen"                 # out/demo_luoshen.mp4
RENDER = {"lang": "zh-TW"}            # subtitle language (out/NAME.zh-TW.srt)
EDITS = {"full": {"suffix": ""}}      # for mv/youtube_upload.py
SCRIPT = "script.md"                  # narration under "## 旁白" (or "## Narration"), one "### chapter" each
VOICE = "voices/NARRATOR.wav"         # 5-15 s of one narrator you have the rights to (docs: make one with text-to-video)

# What the voice reads differs from the subtitles where a word tends to be misread: same length, same sound.
SAY = [("挾天子", "協天子")]           # 挾 is read xié

# Optional: what render.py plays when a part was cut or an ending re-read (default: jobs/voice_jobs.json in order)
# NARRATION = [dict(audio="voice/part1.flac", job="part1"),
#              dict(audio="voice/part2_cut.flac", job="part2", stop_at="the first words that were cut off"),
#              dict(audio="voice/patch1.flac", job="patch1")]

TITLE = ("洛神是誰？", "〈洛神賦〉與感甄說")      # comes up after the first chapter
ENDCARD = "本集畫面與旁白皆由 AI 生成"
FONT = ("Explainer Serif", "fonts")   # family name, folder (here or one up): make_static_font.py NotoSerifTC-VF.ttf 600
MUSIC = "music/luochuan_inst.flac"    # the MV without vocals: python -m demucs --two-stems=vocals -n htdemucs song.wav
MUSIC_DB = -27                        # each section's RMS before ducking
# chapter heading prefix -> second in MUSIC ("Luo River": 0-10 intro, 18-28 interlude, 36-64 quiet verse, 114- chorus);
# the ending starts where the MV clip starts, so picture and music match
CH_MUSIC = {"開場": 3.0, "一": 28.0, "結尾": 8.5}
MV_CLIP = "music/luochuan_mv.mp4"     # the MV itself, for "MV:<second>" shots (shown in a gold frame)
# GAPS = dict(lead=1.6, chapter=1.4, title=3.4, part=0.4, end=5.5, xfade=0.9)

# ---------------------------------------------------------------- pictures (make_images.py)
# AutoIP text-to-image v4 is MOSS-Image: a caption is cohesive English prose (subject and action, appearance, setting,
# framing, medium, light, palette, mood), no strings of quality tags; a Layout dict puts text and figures in pixel boxes.
LOOKS = {"S": ("Painted in Chinese gongbi style with fine gold-leaf linework: blue-green mineral-pigment mountains "
               "outlined in gold, drifting mist and a sea of clouds, ribbons of golden cloud and a few floating golden "
               "motes, under a night-blue sky with a large luminous full moon. Jade green, moon white and gold, lit "
               "like a film still, in a wide 16:9 frame.")}
NEG = "letters or calligraphy that were not asked for, seal stamps, watermark, signature, extra fingers, deformed hands, modern clothing, photograph, 3d render"
CAO_ZHI = ("Cao Zhi, a handsome young poet prince with porcelain skin, long black hair in a topknot under a white jade "
           "crown, in layered white and pale celadon robes")
LUOSHEN = ("the Goddess of the Luo River, a young woman with porcelain skin, an ornate golden crown with pearls, tassels "
           "and a small red jewel, a red mark between her brows, in translucent white and celadon silk with long ribbons")
IMAGES = [
    ("O1", "開場", "巨月下洛神凌波而來", f"{LUOSHEN} glides towards the viewer across a moonlit river, her ribbons streaming "
     "behind her and the full moon rising at her back, a faint water dragon coiling in the mist; framed from the knees up, "
     "a little to the right of centre.", "S"),
    ("O2", "開場", "案上攤開的賦卷", "An unrolled silk scroll lies across a dark wooden desk beside a brush resting on an "
     "inkstone and a single candle; the scroll carries only soft washes of painted mountains and no writing, and "
     "moonlight falls through a lattice window behind it. A close, low view along the desk.", "S"),
    ("O3", "開場", "曹植在洛水邊回望", f"{CAO_ZHI} stands on a riverbank at night and looks back over his shoulder with "
     "quiet longing, the wide river and the enormous moon behind him; seen from behind at mid distance.", "S"),
    ("O4", "開場", "珠簾後宮裝女子的側影", "The silhouette of a court lady in profile behind a curtain of hanging pearl "
     "strands, her face lost in shadow, gold hairpins catching the warm light of a candle on a stand beside her.", "S"),
    ("A1", "一、曹家兄弟", "曹操坐鎮軍帳", "Cao Cao, a stern warlord in his fifties with a short black beard, sits in a "
     "great war tent at night in a black-and-gold robe over dark armour, generals standing behind him; behind them hangs "
     "a blank golden scroll and the light comes from bronze braziers.", "S"),
    ("A2", "一、曹家兄弟", "少年曹丕與曹植並立", "Two teenage princes stand side by side in a moonlit palace courtyard: the "
     "elder in a dark crimson robe with a cold, proud look, the younger in white with a bright, open smile.", "S"),
    ("A3", "一、曹家兄弟", "銅雀台落成", "The newly finished Bronze Sparrow Terrace rises in tiers to a great bronze sparrow "
     "on its roof; guests climb its stairs to a banquet while, at a low table in front, a young poet writes as a crowd "
     "gathers to watch. Seen from a distance, like a handscroll scene.", "S"),
    ("A4", "一、曹家兄弟", "曹植醉中駕車闖宮門", "A drunk young prince in white drives a horse-drawn chariot at full speed "
     "through a huge palace gate at night, guards leaping aside and lanterns swinging in the wind.", "S"),
    ("A5", "一、曹家兄弟", "曹丕受冊為太子", "In a vast hall of red pillars, a prince in a black-and-crimson robe kneels "
     "before the throne to receive a jade seal, rows of officials on both sides; seen from behind him, solemn and still.", "S"),
    # a cover painted with its title by the model itself: a Layout on the 1312x736 canvas v4 returns for 960x540
    ("COVER", "封面", "帶標題的封面", {
        "width": 1312, "height": 736, "bbox_coord_space": "abs", "bbox_format": "xyxy",
        "summary": {"canvas": "single", "meta": ["YouTube thumbnail", "gongbi painting"],
                    "caption": "A YouTube cover in gongbi style with gold-leaf linework: the Goddess of the Luo River "
                               "before a huge golden full moon on the right, night-blue sky and blue-green mountains, "
                               "and a large title on the darker left side."},
        "items": [
            {"label": "character", "caption": f"{LUOSHEN}, looking at the viewer with a faint smile, framed from the "
                                              "waist up.", "bbox": [700, 40, 1272, 736]},
            {"label": "text", "caption": "Huge Chinese brush lettering, the first line gold and the second white, each "
                                         "with a thick dark outline, no backing panel.",
             "text": "洛神\n是他嫂嫂？", "bbox": [64, 170, 680, 540]},
        ]}, None),
]

# ---------------------------------------------------------------- timeline (render.py)
# (picture, the words it comes in on, move, focus): in / out zoom to or from focus (x, y in 0..1), left / right pan,
# frame = the whole picture in a gold frame, scroll = a handscroll on white panned right to left, "MV:8.5" = MV_CLIP
SHOTS = [
    ("O1", None, "in", (0.6, 0.32)), ("O2", "這八個字", "right", None), ("O3", "寫下她的", "in", (0.6, 0.4)),
    ("O4", "但一千多年來", "out", (0.42, 0.42)),
    ("A1", "東漢末年", "in", (0.4, 0.5)), ("A2", "他有二十幾個兒子", "out", None), ("A3", "曹植從小就會寫文章", "right", None),
    ("A4", "曹操一度想立他", "in", None), ("A5", "西元二一七年", "out", None),
    ("MV:8.5", "我們的 MV", None, None),
]
