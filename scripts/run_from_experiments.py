import os, sys, subprocess, argparse
try:
    import yaml  # PyYAML
except ImportError:
    print("[ERR] PyYAML is missing. Run: pip install pyyaml")
    sys.exit(1)

def run_cmd(cmd: str):
    print(">>", cmd)
    rc = subprocess.run(cmd, shell=True).returncode
    if rc != 0:
        sys.exit(rc)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/experiments.yaml")
    args = ap.parse_args()

    with open(args.config, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    prompts = cfg.get("prompts", "prompts/main.csv")
    d = cfg.get("defaults", {})
    provider = d.get("provider", "ollama")
    model = d.get("model", "gemma:7b")
    temperature = d.get("temperature", 0.0)

    for run in cfg.get("runs", []):
        mode = run["mode"]
        outdir = run.get("outdir", "results/raw/v2")
        overwrite = run.get("overwrite", False)

        cmd = (
            f'python code\\run_langchain_experiment.py '
            f'--prompt-file {prompts} --mode {mode} --outdir {outdir} '
            f'--provider {provider} --model "{model}" --temperature {temperature}'
        )
        if overwrite:
            cmd += " --overwrite"
        run_cmd(cmd)

if __name__ == "__main__":
    main()