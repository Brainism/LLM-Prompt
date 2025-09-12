import os, sys, argparse
import pandas as pd
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.table import Table

matplotlib.rcParams['font.size'] = 12

def find_col(df, candidates):
    cols_lower = {c.lower(): c for c in df.columns}
    for cand in candidates:
        lc = cand.lower()
        if lc in cols_lower:
            return cols_lower[lc]
    for cand in candidates:
        for c in df.columns:
            if cand.lower() in c.lower():
                return c
    return None

def detect_bleu_columns(df):
    pairs = [
        (['bleu_base','base_bleu','bleu(base)','bleu_sacre_base'], ['bleu_instr','instr_bleu','bleu(instructed)','bleu_sacre_instr']),
        (['base','base_bleu','base_score'], ['instr','instr_bleu','instr_score']),
    ]
    for cand_base, cand_instr in pairs:
        cb = find_col(df, cand_base)
        ci = find_col(df, cand_instr)
        if cb and ci:
            return cb, ci, 'bleu'
    if 'base' in df.columns and 'instr' in df.columns:
        return 'base', 'instr', 'bleu'
    bleu_like = [c for c in df.columns if 'bleu' in c.lower() or 'sacre' in c.lower()]
    if len(bleu_like) >= 2:
        return bleu_like[0], bleu_like[1], 'bleu'
    return None, None, None

def render_table_image(df_table, title, outpath, bbox_inches='tight', dpi=300, fontsize=12):
    df_display = df_table.copy()
    for c in df_display.columns:
        if pd.api.types.is_float_dtype(df_display[c]) or pd.api.types.is_integer_dtype(df_display[c]):
            df_display[c] = df_display[c].apply(lambda v: f"{v:.3f}" if (pd.notnull(v) and not float(v).is_integer()) else (f"{int(v)}" if pd.notnull(v) else ""))
        else:
            df_display[c] = df_display[c].astype(str)

    nrows, ncols = df_display.shape
    cell_w = max(1.2, min(2.5, 12.0 / max(1, ncols)))
    fig_w = max(8, cell_w * ncols)
    fig_h = max(3, 0.45 * nrows + 1.2)
    fig = plt.figure(figsize=(fig_w, fig_h), dpi=dpi)
    ax = fig.add_subplot(111)
    ax.set_axis_off()
    ax.set_title(title, fontsize=fontsize+4, pad=20)
    table = ax.table(cellText=df_display.values,
                     colLabels=df_display.columns,
                     cellLoc='center',
                     loc='center',
                     colLoc='center')
    table.auto_set_font_size(False)
    table.set_fontsize(fontsize)
    table.scale(1, 1.2)
    for (row, col), cell in table.get_celld().items():
        cell.PAD = 0.5
        cell.set_linewidth(1.2)
        if row == 0:
            cell.set_text_props(weight='bold', color='black')
    plt.tight_layout()
    plt.savefig(outpath, bbox_inches=bbox_inches, dpi=dpi)
    plt.close(fig)
    print("Saved:", outpath)

def render_text_image(lines, outpath, dpi=300, width=1600, fontsize=14):
    fig_w = width / dpi
    height = max(200, 20 + len(lines) * (fontsize * 1.2))
    fig_h = height / dpi
    fig = plt.figure(figsize=(fig_w, fig_h), dpi=dpi)
    ax = fig.add_subplot(111)
    ax.set_axis_off()
    text = "\n".join(lines)
    ax.text(0, 1, text, fontfamily='monospace', fontsize=fontsize, va='top')
    plt.savefig(outpath, bbox_inches='tight', dpi=dpi)
    plt.close(fig)
    print("Saved:", outpath)

def main():
    p = argparse.ArgumentParser(description="Generate figures from per-item aggregated metrics")
    p.add_argument('--input', required=True, help='Path to per-item CSV (aggregated metrics)')
    p.add_argument('--stats', required=False, help='Path to stats_summary.v2.csv (optional)')
    p.add_argument('--out', required=True, help='Output directory for PNGs')
    p.add_argument('--id-col', required=False, help='If your CSV uses a different id column name, set it here (e.g. example_id)')
    args = p.parse_args()

    inp = args.input
    stats_csv = args.stats
    outdir = args.out
    id_col_override = args.id_col
    os.makedirs(outdir, exist_ok=True)

    print("Loading:", inp)
    df = pd.read_csv(inp)
    df.columns = [c.strip() for c in df.columns]

    if id_col_override:
        if id_col_override not in df.columns:
            raise RuntimeError(f"Provided --id-col '{id_col_override}' not found in CSV. Available columns: {list(df.columns)[:50]}")
        id_col = id_col_override
    else:
        id_col = find_col(df, ['id','item_id','example_id','example','ex_id','uid','idx','index','Unnamed: 0'])
    if id_col is None:
        raise RuntimeError("Could not detect item id column. Use --id-col to specify it. Available columns: " + ", ".join(list(df.columns)[:80]))
    print("Using id column:", id_col)
    df['__id__'] = df[id_col].astype(str)

    base_col, instr_col, metric_prefix = detect_bleu_columns(df)
    if base_col is None or instr_col is None:
        base_col = find_col(df, ['bleu_base','base_bleu','bleu(base)','bleu_sacre_base','base'])
        instr_col = find_col(df, ['bleu_instr','instr_bleu','bleu(instructed)','bleu_sacre_instr','instr'])
    if base_col is None or instr_col is None:
        numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
        bleu_like = [c for c in numeric_cols if 'bleu' in c.lower() or 'sacre' in c.lower()]
        if len(bleu_like) >= 2:
            base_col, instr_col = bleu_like[:2]
        elif 'base' in df.columns and 'instr' in df.columns:
            base_col, instr_col = 'base', 'instr'
        else:
            raise RuntimeError("Could not auto-detect BLEU base/instr columns. Please provide --id-col and ensure BLEU columns exist.")
    print("Using BLEU columns:", base_col, "and", instr_col)

    df['bleu_base_val'] = pd.to_numeric(df[base_col], errors='coerce')
    df['bleu_instr_val'] = pd.to_numeric(df[instr_col], errors='coerce')
    df['delta_bleu'] = df['bleu_instr_val'] - df['bleu_base_val']

    chrf_base = find_col(df, ['chrf_base','chrF_base','chrf(base)','chrf'])
    chrf_instr = find_col(df, ['chrf_instr','chrF_instr','chrf(instructed)'])
    if chrf_base and chrf_instr:
        df['chrf_base_val'] = pd.to_numeric(df[chrf_base], errors='coerce')
        df['chrf_instr_val'] = pd.to_numeric(df[chrf_instr], errors='coerce')
        df['delta_chrf'] = df['chrf_instr_val'] - df['chrf_base_val']
    else:
        df['chrf_base_val'] = np.nan
        df['chrf_instr_val'] = np.nan
        df['delta_chrf'] = np.nan

    rouge_base = find_col(df, ['rouge_base','rouge'])
    rouge_instr = find_col(df, ['rouge_instr','rouge(instructed)'])
    if rouge_base and rouge_instr:
        df['rouge_base_val'] = pd.to_numeric(df[rouge_base], errors='coerce')
        df['rouge_instr_val'] = pd.to_numeric(df[rouge_instr], errors='coerce')
        df['delta_rouge'] = df['rouge_instr_val'] - df['rouge_base_val']
    else:
        df['rouge_base_val'] = np.nan
        df['rouge_instr_val'] = np.nan
        df['delta_rouge'] = np.nan

    disp = pd.DataFrame({
        'id': df['__id__'],
        'BLEU(base)': df['bleu_base_val'],
        'BLEU(instr)': df['bleu_instr_val'],
        'ΔBLEU': df['delta_bleu'],
        'chrF(base)': df['chrf_base_val'],
        'chrF(instr)': df['chrf_instr_val'],
        'ΔchrF': df['delta_chrf'],
        'ROUGE(base)': df['rouge_base_val'],
        'ROUGE(instr)': df['rouge_instr_val'],
        'ΔROUGE': df['delta_rouge'],
    })
    disp = disp.set_index('id')

    top10 = disp.sort_values(by='ΔBLEU', ascending=False).head(10)
    bottom10 = disp.sort_values(by='ΔBLEU', ascending=True).head(10)

    render_table_image(top10, title="Top 10 ΔBLEU", outpath=os.path.join(outdir, "top10_delta_bleu.png"), fontsize=12)
    render_table_image(bottom10, title="Bottom 10 ΔBLEU", outpath=os.path.join(outdir, "bottom10_delta_bleu.png"), fontsize=12)

    if stats_csv:
        try:
            sstat = pd.read_csv(stats_csv)
            lines = []
            for idx, row in sstat.iterrows():
                metric = str(row.get('metric', ''))
                n = int(row.get('n', 0))
                mean_base = row.get('mean_base', '')
                mean_instr = row.get('mean_instr', '')
                delta = row.get('delta', '')
                p = row.get('p', '')
                lines.append(f"{metric:10s} | n={n:>2d} | base={mean_base:8} | instr={mean_instr:8} | Δ={delta:8} | p={p}")
            render_text_image(lines, outpath=os.path.join(outdir, "metrics_summary_text.png"), dpi=300, width=1600, fontsize=14)
        except Exception as e:
            print("Could not read stats CSV:", e)

    print("All figures written to:", outdir)
    print("Done.")

if __name__ == "__main__":
    main()