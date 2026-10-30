"""Variable font -> static instance with its own family name, for libass.

libass (ffmpeg's subtitles filter) only renders the default instance of a variable font, so "Black" weight requests
silently come out Regular/Light. Cut a static instance and give it a unique family name that the ASS refers to.

usage: python mvkit/make_static_font.py NotoSerifTC-VF.ttf 900 "PS Serif Black" PROJECT_DIR/fonts/PSSerifBlack.ttf
Then set TYPO font="PS Serif Black", font_file="fonts/PSSerifBlack.ttf". Check the font's licence before
redistributing the output (Noto fonts are SIL OFL: renaming a modified font is what OFL asks for).
"""
import sys
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

src, wght, family, out = sys.argv[1], float(sys.argv[2]), sys.argv[3], sys.argv[4]
f = TTFont(src)
print("axes", [(a.axisTag, a.minValue, a.maxValue) for a in f["fvar"].axes])
inst = instantiateVariableFont(f, {"wght": wght})
for rec in inst["name"].names:
    if rec.nameID in (1, 4, 16):
        rec.string = family
    elif rec.nameID == 6:
        rec.string = family.replace(" ", "")
    elif rec.nameID in (2, 17):
        rec.string = "Regular"
inst["OS/2"].usWeightClass = 400  # registered as Regular so no synthetic bold is applied on top
inst.save(out)
print("saved", out)
