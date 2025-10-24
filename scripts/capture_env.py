import os, platform, subprocess, json, shutil, datetime, re

OUT = "docs/env_table.md"

def get(cmd):
    try:
        return subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return ""

def git_info():
    sha = get("git rev-parse --short HEAD")
    br  = get("git rev-parse --abbrev-ref HEAD")
    return sha, br

def pkg_ver(name):
    try:
        import importlib.metadata as md
        return md.version(name)
    except Exception:
        return "n/a"

def gpu_info():
    nvidia = get('nvidia-smi --query-gpu=name,memory.total --format=csv,noheader')
    if nvidia:
        return nvidia.replace("\n", "; ")
    return "CPU only / unknown"

def cpu_info():
    try:
        import psutil
        info = f"{platform.processor()} / {psutil.cpu_count(logical=True)} threads"
        return info
    except Exception:
        return platform.processor() or "unknown CPU"

def ram_gb():
    try:
        import psutil
        return round(psutil.virtual_memory().total / (1024**3))
    except Exception:
        return "n/a"

def render(tpl, mapping):
    for k,v in mapping.items():
        tpl = tpl.replace(f"{{{{{k}}}}}", str(v))
    return tpl

def main():
    sha, br = git_info()
    tpl = open(OUT, "r", encoding="utf-8").read() if os.path.exists(OUT) else """# Environment Table

## OS & Hardware
- OS: {{OS_NAME}} ({{OS_VERSION}})
- CPU: {{CPU_INFO}}
- RAM: {{RAM_GB}} GB
- GPU: {{GPU_INFO}}

## Python
- Python: {{PY_VER}}
- venv: ./.venv
- Locale/Encoding: UTF-8

## Key Packages
- sacrebleu: {{PKG_SACREBLEU}}
- rouge-score: {{PKG_ROUGE}}
- numpy: {{PKG_NUMPY}}
- scipy: {{PKG_SCIPY}}
- pandas: {{PKG_PANDAS}}

## Reproducibility
- Commit: {{GIT_SHA}}
- Branch: {{GIT_BRANCH}}
- Run command: `run_all.bat`
"""
    m = {
        "OS_NAME": platform.system(),
        "OS_VERSION": platform.version(),
        "CPU_INFO": cpu_info(),
        "RAM_GB": ram_gb(),
        "GPU_INFO": gpu_info(),
        "PY_VER": platform.python_version(),
        "PKG_SACREBLEU": pkg_ver("sacrebleu"),
        "PKG_ROUGE": pkg_ver("rouge-score"),
        "PKG_NUMPY": pkg_ver("numpy"),
        "PKG_SCIPY": pkg_ver("scipy"),
        "PKG_PANDAS": pkg_ver("pandas"),
        "GIT_SHA": sha,
        "GIT_BRANCH": br,
    }
    text = render(tpl, m)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"[OK] wrote {OUT}")

if __name__ == "__main__":
    main()