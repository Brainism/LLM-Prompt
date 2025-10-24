import os, csv, textwrap, pathlib, json, sys

ROOT = pathlib.Path(".")
DIRS = [
    "data/manifest",
    "docs",
    "prompts",
    "results/raw",
    "results/quantitative",
    "schema",
    "tables",
    "figs",
]

CANDIDATES = ROOT/"data/candidates.csv"
STUDY = ROOT/"docs/study_scope.md"
ANALYSIS = ROOT/"docs/analysis_plan.md"
ENV = ROOT/"docs/env_table.md"

def ensure_dirs():
    for d in DIRS:
        pathlib.Path(d).mkdir(parents=True, exist_ok=True)

def write_candidates_template():
    if CANDIDATES.exists(): return
    with CANDIDATES.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id","input","reference","domain","lang","len_bin","diff_bin","license","cluster_id"])
        w.writerow(["ko_0001","길이 규칙을 지켜 한 문단으로 요약하세요.","요약 레퍼런스","general","ko","short","easy","CC-BY-4.0","GEN_KO_SHORT_EASY_0001"])

def write_md(path: pathlib.Path, content: str):
    if path.exists(): return
    path.write_text(textwrap.dedent(content).lstrip(), encoding="utf-8")

def main():
    ensure_dirs()
    write_candidates_template()
    write_md(STUDY, """
    # Study Scope (사전등록)
    - 연구질문: Instructed vs General 모델의 **품질-준수-비용** Pareto 우위 여부
    - 도메인/언어/길이/난이도: domain ∈ {general, …}, lang ∈ {ko,en}, len ∈ {short,medium,long}, diff ∈ {easy,medium,hard}
    - 규칙: 길이bin 규칙, 금칙어 파일, JSON 형식 규칙(필요 시)
    - 표본계획: 총 n=50 균형배치(ko=25, en=25; 18셀 기준 14셀×3, 4셀×2)
    - 제외기준: PII/금칙/중복/라이선스 불명확 항목 제외
    """)
    write_md(ANALYSIS, """
    # Analysis Plan (사전등록)
    - 가설(H1~H3): 준수율↑, 품질 동등~소폭↑, CVD 적용 시 추가 개선·비용폭증 없음
    - 1차 지표: 준수율(pass), ROUGE-L, sacreBLEU, chrF; (옵션) BERTScore
    - 2차 지표: 비용/지연(p50,p95), 토큰 사용
    - 통계: paired bootstrap CI(>=10k), Wilcoxon signed-rank, Cohen's dz, BH-FDR
    - 강건성: lang×len×diff 서브그룹 보고
    """)
    write_md(ENV, """
    # Environment Table
    - OS/Python: <작성>
    - Packages: requirements.txt 버전 고정 (pip freeze 별첨)
    - Hardware: GPU/CPU/RAM <작성>
    - Seeds/params: temperature, top-p, max_tokens, random_seed <작성>
    """)
    print("[OK] dataset/doc skeleton ready:", ROOT.resolve())

if __name__ == "__main__":
    main()