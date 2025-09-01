import json
import platform
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def get_gpu_info():
    try:
        import torch

        if torch.cuda.is_available():
            devs = [
                torch.cuda.get_device_name(i) for i in range(torch.cuda.device_count())
            ]
            drv = torch.version.cuda
            return {"backend": "torch", "devices": devs, "cuda": drv}
    except Exception:
        pass
    try:
        if shutil.which("nvidia-smi"):
            q = subprocess.check_output(
                [
                    "nvidia-smi",
                    "--query-gpu=name,driver_version,memory.total",
                    "--format=csv,noheader",
                ],
                text=True,
            )
            g = [
                tuple(x.strip().split(", "))
                for x in q.strip().splitlines()
                if x.strip()
            ]
            return {
                "backend": "nvidia-smi",
                "gpus": [{"name": n, "driver": d, "mem_total": m} for n, d, m in g],
            }
    except Exception:
        pass
    return {"backend": "none", "note": "No CUDA GPU detected"}


def get_pkg_versions():
    try:
        out = subprocess.check_output(
            [sys.executable, "-m", "pip", "freeze"], text=True
        )
        return [line.strip() for line in out.splitlines() if line.strip()]
    except Exception as e:
        return [f"pip-freeze-error: {e}"]


def main(out):
    info = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "os": platform.platform(),
        "python": sys.version.replace("\n", " "),
        "executable": sys.executable,
        "gpu": get_gpu_info(),
        "packages": get_pkg_versions(),
    }
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    md = Path(out)
    lines = []
    lines.append("# 환경표 (env_table)")
    lines.append("")
    lines.append(f"- 생성시각: {info['generated_at']}")
    lines.append(f"- OS: `{info['os']}`")
    lines.append(f"- Python: `{info['python']}`")
    lines.append(f"- Python 실행파일: `{info['executable']}`")
    lines.append(f"- GPU: `{json.dumps(info['gpu'], ensure_ascii=False)}`")
    lines.append("")
    lines.append("## pip freeze")
    lines.append("```")
    lines.extend(info["packages"])
    lines.append("```")
    md.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--out", default="docs/env_table.md")
    args = p.parse_args()
    main(args.out)
