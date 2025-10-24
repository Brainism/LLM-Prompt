from pathlib import Path
p = Path("scripts/m3_eval.py")
if not p.exists():
    raise SystemExit("scripts/m3_eval.py not found. 작업 경로를 확인하세요.")
orig = p.read_text(encoding='utf-8', errors='replace')
old = 'man = json.loads(Path(args.manifest).read_text(encoding="utf-8"))\n    pid2meta = {m["id"]: m for m in man}\n'
new = '''manifest_content = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    # Support multiple manifest shapes: list, { "items": [...] }, or dict of id->meta
    if isinstance(manifest_content, dict):
        if "items" in manifest_content and isinstance(manifest_content["items"], list):
            man = manifest_content["items"]
        else:
            vals = list(manifest_content.values())
            if vals and isinstance(vals[0], dict) and "id" in vals[0]:
                man = vals
            else:
                raise ValueError(f"Unexpected manifest structure in {args.manifest}: top-level dict without 'items' or id->meta mapping")
    elif isinstance(manifest_content, list):
        man = manifest_content
    else:
        raise ValueError(f"Unexpected manifest JSON type: {type(manifest_content)}")
    pid2meta = {m["id"]: m for m in man}
'''
if old not in orig:
    print("기존 패턴을 찾지 못했습니다. 수동으로 편집하세요.")
else:
    (p.with_suffix('.py.bak')).write_text(orig, encoding='utf-8')
    p.write_text(orig.replace(old, new), encoding='utf-8')
    print("패치 적용 완료. 백업: scripts/m3_eval.py.bak")