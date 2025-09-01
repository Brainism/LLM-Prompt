import sys
import subprocess
from pathlib import Path

def main():
    sacre = Path("code") / "sacre_eval.py"
    if sacre.exists():
        print("[run] sacre_eval.py ...")
        subprocess.run([sys.executable, str(sacre)], check=False)
    else:
        print("[note] code/sacre_eval.py not found; skipping.")

if __name__ == "__main__":
    main()
