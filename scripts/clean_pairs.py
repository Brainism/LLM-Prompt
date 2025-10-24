import pandas as pd
import sys

p = 'per_item_text_pairs.csv'
try:
    df = pd.read_csv(p, encoding='utf-8-sig', dtype=str, keep_default_na=False)
except Exception as e:
    print("Error reading", p, ":", e)
    sys.exit(1)

if 'id' not in df.columns:
    if df.shape[1] >= 3:
        df = df.iloc[:, :3]
        df.columns = ['id', 'reference', 'prediction']
        print("Header repaired: set columns -> id, reference, prediction")
    else:
        print("Unexpected columns:", df.columns.tolist())
        sys.exit(1)

def norm_cell(x):
    if x is None:
        return ''
    s = str(x).strip()
    if s.lower() in ('nan', 'none'):
        return ''
    return s

df['reference'] = df['reference'].apply(norm_cell)
df['prediction'] = df['prediction'].apply(norm_cell)

df['reference'] = df['reference'].replace({'nan': '', 'NaN': ''})
df['prediction'] = df['prediction'].replace({'nan': '', 'NaN': ''})

df.to_csv(p, index=False, encoding='utf-8-sig')

print('Cleaned', p, 'rows=', len(df))
n_with_ref = (df['reference'] != '').sum()
print('n_with_ref=', n_with_ref)
print('Sample (top 20):')
print(df.head(20).to_string(index=False))