"""A/B/C thumbnails for the demo project. Frames come from the finished MV:
    ffmpeg -ss 45.2 -i out/night_theatre_MV.mp4 -frames:v 1 thumb_src/LS03_45.2.png
usage: python examples/mv/demo/thumbs.py PROJECT_DIR
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "mv"))
import thumbkit as tk

D = sys.argv[1]
src = lambda n: os.path.join(D, "thumb_src", n)
out = os.path.join(D, "thumbnails")
os.makedirs(out, exist_ok=True)
tk.setup(os.path.join(D, "fonts", "PSSerifBlack.ttf"), os.path.join(D, "fonts", "NotoSerif-Bold.ttf"))

# A: the two singers face off across a blood seam
im = tk.split(tk.frame(src("LS04_45.0.png"), 1.15, 0.62, 0.42), tk.frame(src("LS03_41.0.png"), 1.15, 0.40, 0.40))
im = tk.shade(im, "bottom", width=0.42)
tk.title(im, (640, 560), "夜之劇場", 150, 0.12)
tk.caps(im, (640, 690), "GOTHIC METAL DUET", 30, spacing=9)
tk.banner(im, 330, 60, "嘶吼 × 女高音", 36)
tk.badge(im)
tk.grain(im).save(os.path.join(out, "thumb_A_duet.jpg"), quality=95)

# B: the punchline, first half struck through
im = tk.shade(tk.frame(src("B03_2.0.png"), 1.05), "left", width=0.55)
im = tk.shade(im, "bottom", strength=200, width=0.3)
tk.text(im, (48, 150), "淚水是道具", 92)
tk.strike(im, 40, 520, 150)
tk.text(im, (48, 290), "掌聲是謊言", 92, edge=tk.BLOOD)
tk.title(im, (320, 570), "夜之劇場", 130, 0.1)
tk.caps(im, (320, 690), "NIGHT THEATRE", 28, spacing=12)
tk.badge(im)
tk.grain(im).save(os.path.join(out, "thumb_B_punchline.jpg"), quality=95)

# C: the band in the burning theatre
im = tk.shade(tk.frame(src("W1_1.0.png"), 1.08, 0.5, 0.42), "bottom", strength=225, width=0.45)
tk.title(im, (640, 575), "夜之劇場", 140, 0.12)
tk.rule(im, 640, 655, 520)
tk.banner(im, 300, 56, "交響哥德金屬", 34)
tk.badge(im)
tk.grain(im).save(os.path.join(out, "thumb_C_band.jpg"), quality=95)
print(sorted(os.listdir(out)))
