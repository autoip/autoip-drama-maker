"""A/B/C covers for the demo episode. Frames come from the clips (the render has subtitles burned in):
    ffmpeg -ss 1.2 -i clips/S2_08.mp4 -frames:v 1 thumb_src/S2_08_1.2.png
usage: python examples/demo/covers.py PROJECT_DIR          -> PROJECT_DIR/covers/cover_*.jpg (1080x1920)
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "dramakit"))
import thumbkit as tk

D = sys.argv[1]
src = lambda n: os.path.join(D, "thumb_src", n)
out = os.path.join(D, "covers")
os.makedirs(out, exist_ok=True)
font = next(p for p in (os.path.join(D, "fonts", "DKSansBlack.ttf"), os.path.join(D, "..", "fonts", "DKSansBlack.ttf")) if os.path.exists(p))
tk.setup(font)

# A: the reveal - the hook line over the face that says it
im = tk.shade(tk.frame(src("S2_08_1.2.png"), 1.05, 0.5, 0.45), "bottom", width=0.4)
im = tk.shade(im, "top", strength=170, width=0.25)
tk.hook(im, (540, 250), "鉤子文案", 110)
tk.title(im, (540, 1480), "劇名", 140, 0.08)
tk.badge(im, "第1集")
tk.grain(im).save(os.path.join(out, "cover_A_reveal.jpg"), quality=95)

# B: before / after - the push-down on top, the face-slap below
im = tk.split(tk.frame(src("S2_01_1.0.png"), 1.1, 0.5, 0.4), tk.frame(src("S2_09_1.0.png"), 1.1, 0.5, 0.4))
tk.text(im, (60, 300), "被壓的那句", 96)
tk.text(im, (60, 1260), "反轉的那句", 96, edge=tk.RED)
tk.banner(im, 540, 1500, "類型標籤", 64)
tk.badge(im, "第1集")
tk.grain(im).save(os.path.join(out, "cover_B_turn.jpg"), quality=95)

# C: the lead alone, the title and the series tag
im = tk.shade(tk.frame(src("S2_04_1.5.png"), 1.12, 0.5, 0.42), "bottom", strength=225, width=0.45)
tk.title(im, (540, 1400), "劇名", 150, 0.08)
tk.rule(im, 540, 1490, 600)
tk.banner(im, 300, 140, "全集更新中", 50)
tk.grain(im).save(os.path.join(out, "cover_C_heroine.jpg"), quality=95)
print(sorted(os.listdir(out)))
