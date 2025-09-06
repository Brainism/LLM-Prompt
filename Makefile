SHELL := cmd
.SHELLFLAGS := /C
.ONESHELL:
.PHONY: all run tables env clean-garbage

all: run tables env

run:
	@if not exist .venv ( py -m venv .venv )
	call .\.venv\Scripts\activate
	run_all.bat

tables:
	call .\.venv\Scripts\activate
	python scripts\export_tables_and_figs.py

env:
	call .\.venv\Scripts\activate
	python scripts\capture_env.py

clean-garbage:
	powershell -NoP -C "Get-ChildItem -File -Recurse | Where-Object { $_.Name -match '^(0|1)$' -or $_.Name -match '\[' -or $_.Name -in @('bool','int','float','str','None','Dict','Tuple','np.ndarray','List[Path]','List[str]') } | Remove-Item -Force"