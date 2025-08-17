from pathlib import Path
from PIL import Image

IN1 = Path("results/figures/cmp_bleu_bar.png")
IN2 = Path("results/figures/cmp_rouge_bar.png")
IN3 = Path("results/figures/compliance_group.png")
IN4 = Path("results/figures/compliance_by_scenario.png")
OUT = Path("results/figures/summary_tile_from_imgs.png")

def main():
    imgs = [Image.open(p) for p in [IN1,IN2,IN3,IN4]]
    W = max(im.width for im in imgs)
    Hs = []
    resized = []
    for im in imgs:
        r = im.resize((W, int(im.height * W / im.width)))
        resized.append(r); Hs.append(r.height)
    Htop = max(resized[0].height, resized[1].height)
    Hbot = max(resized[2].height, resized[3].height)
    canvas = Image.new("RGB", (W*2, Htop+Hbot), "white")
    canvas.paste(resized[0], (0,0))
    canvas.paste(resized[1], (W,0))
    canvas.paste(resized[2], (0,Htop))
    canvas.paste(resized[3], (W,Htop))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(OUT, quality=95)
    print(f"[OK] saved -> {OUT.resolve()}")

if __name__ == "__main__":
    main()