import pandas as pd,sys 
p_in = r'prompts\\main.csv' 
p_out = r'prompts\\main.utf8.csv' 
encodings = ['utf-8','utf-8-sig','cp949'] 
for e in encodings: 
    try: 
        df = pd.read_csv(p_in, encoding=e) 
        df.to_csv(p_out, index=False, encoding='utf-8-sig') 
        print('Success: read %s with %s - %s' % (p_in,e,p_out)) 
        sys.exit(0) 
    except Exception as ex: 
        print('Failed with', e, ex) 
print('All attempts failed') 
