import os
from PIL import Image
import glob

def ensure_dir(p):
    if not os.path.exists(p):
        os.makedirs(p, exist_ok=True)

def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--in_dir", default="figs", help="Input PNG dir")
    p.add_argument("--out_dir", default="figs_highres", help="Output highres dir")
    p.add_argument("--scale", type=float, default=2.0, help="Upscale factor")
    p.add_argument("--dpi", type=int, default=300, help="DPI for saved images")
    args = p.parse_args()

    ensure_dir(args.out_dir)
    files = glob.glob(os.path.join(args.in_dir, "*.png"))
    if not files:
        print("No PNG files found in", args.in_dir)
        return
    for f in files:
        bn = os.path.basename(f)
        outp = os.path.join(args.out_dir, bn)
        try:
            im = Image.open(f)
            w,h = im.size
            new_size = (int(w*args.scale), int(h*args.scale))
            im2 = im.resize(new_size, resample=Image.LANCZOS)
            im2.save(outp, dpi=(args.dpi,args.dpi))
            print("Saved highres:", outp, "size:", new_size)
        except Exception as e:
            print("Failed:", f, e)

if __name__ == "__main__":
    main()