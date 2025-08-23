.ONESHELL:
SHELL := bash
PYTHON ?= python

SEED ?= 42
TEMP ?= 0.2
TOP_P ?= 1.0
MAX_TOKENS ?= 1024

.PHONY: all baseline env params tag-baseline verify clean

all: baseline

env:
	$(PYTHON) scripts/capture_env.py --out docs/env_table.md

params:
	mkdir -p configs
	$(PYTHON) scripts/record_params.py \
	  --seed $(SEED) --temperature $(TEMP) --top_p $(TOP_P) --max_tokens $(MAX_TOKENS) \
	  --out configs/baseline_params.yaml

baseline: env params verify

verify:
	$(PYTHON) scripts/verify_baseline.py \
	  --results_dir results \
	  --params configs/baseline_params.yaml \
	  --out_md docs/baseline_repro_log.md

tag-baseline:
	DATE=$$(date +%Y%m%d-%H%M%S); \
	git tag -a "v0.3-baseline-$$DATE" -m "Freeze baseline (env/params/results snapshot)"; \
	git push origin --tags

clean:
	rm -f docs/baseline_repro_log.md