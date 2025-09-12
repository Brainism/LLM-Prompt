from PIL import Image
import os, glob, sys

ROOT = r"C:\Project\LLM"
FIG_DIR = os.path.join(ROOT, "docs", "paper", "figs")

if not os.path.isdir(FIG_DIR):
    print("FIG_DIR not found:", FIG_DIR)
    sys.exit(1)

patterns = [os.path.join(FIG_DIR, "*_300dpi.png")]

for pat in patterns:
    for p in glob.glob(pat):
        try:
            im = Image.open(p)
            w, h = im.size
            im2 = im.resize((w*2, h*2), Image.LANCZOS)
            base = os.path.splitext(os.path.basename(p))[0]
            out_png = os.path.join(FIG_DIR, base + "_600dpi.png")
            out_pdf = os.path.join(FIG_DIR, base + ".pdf")
            im2.save(out_png, dpi=(600,600))
            im2.convert("RGB").save(out_pdf, "PDF", resolution=600)
            print("WROTE:", out_png, out_pdf)
        except Exception as e:
            print("FAILED:", p, e)