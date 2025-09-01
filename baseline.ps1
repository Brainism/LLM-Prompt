param([int]$Seed=42,[double]$Temp=0.2,[double]$TopP=1.0,[int]$MaxTokens=1024)
$ErrorActionPreference="Stop"; $py="python"
& $py scripts/capture_env.py --out docs/env_table.md
New-Item -ItemType Directory -Force -Path configs | Out-Null
& $py scripts/record_params.py --seed $Seed --temperature $Temp --top_p $TopP --max_tokens $MaxTokens --out configs/baseline_params.yaml
& $py scripts/verify_baseline.py --results_dir results --params configs/baseline_params.yaml --out_md docs/baseline_repro_log.md
Write-Host "`n[Done] env_table.md / baseline_params.yaml / baseline_repro_log.md"
