from PIL import Image
import os, glob

src = r"C:\Project\LLM\figs"
dst = r"C:\Project\LLM\figs_highres"
os.makedirs(dst, exist_ok=True)

for p in glob.glob(os.path.join(src,"*.png")):
    img = Image.open(p)
    w,h = img.size
    new = img.resize((w*3, h*3), Image.LANCZOS)
    fname = os.path.basename(p)
    new.save(os.path.join(dst, fname), dpi=(600,600))
    print("Saved", fname)