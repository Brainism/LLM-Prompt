import os, json, argparse, time
from tqdm import tqdm

def load_manifest(path):
    with open(path,'r',encoding='utf-8') as f:
        s=f.read().strip()
    try:
        j=json.loads(s)
        if isinstance(j, dict) and "items" in j:
            return j["items"]
        if isinstance(j, list):
            return j
    except:
        items=[]
        with open(path,'r',encoding='utf-8') as f:
            for line in f:
                line=line.strip()
                if not line: continue
                try:
                    items.append(json.loads(line))
                except:
                    continue
        return items
    return []

def hf_inference_call(model_id, prompt, hf_token, max_new_tokens=256):
    import requests
    url = f"https://api-inference.huggingface.co/models/{model_id}"
    headers = {"Authorization": f"Bearer {hf_token}"}
    payload = {"inputs": prompt, "parameters": {"max_new_tokens": max_new_tokens}, "options":{"wait_for_model":True}}
    r = requests.post(url, headers=headers, json=payload, timeout=120)
    r.raise_for_status()
    return r.json()

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--manifest', required=True)
    p.add_argument('--model', required=True, help='HF model id or local path')
    p.add_argument('--out', default='results/raw/outputs.jsonl')
    p.add_argument('--max_new_tokens', type=int, default=256)
    p.add_argument('--hf_token_env', default='HF_TOKEN', help='env var name for HF token (if using HF Inference API)')
    args = p.parse_args()

    items = load_manifest(args.manifest)
    print(f"Manifest items: {len(items)}")

    os.makedirs(os.path.dirname(args.out) or '.', exist_ok=True)

    can_local = False
    gen_fn = None
    try:
        from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
        import torch
        print("Transformers available. Trying to load model (may OOM if model is large)...")
        tokenizer = AutoTokenizer.from_pretrained(args.model, use_fast=True, trust_remote_code=True)
        model = AutoModelForCausalLM.from_pretrained(args.model, device_map="auto", torch_dtype=torch.float16, trust_remote_code=True)
        gen = pipeline("text-generation", model=model, tokenizer=tokenizer, device_map="auto")
        def gen_local(prompt):
            out = gen(prompt, max_new_tokens=args.max_new_tokens, do_sample=False, return_full_text=False)
            if isinstance(out, list) and len(out)>0:
                return out[0].get('generated_text') or out[0].get('text') or str(out[0])
            return str(out)
        gen_fn = gen_local
        can_local = True
        print("Local model load OK.")
    except Exception as e:
        print("Local transformers generation failed:", e)

    hf_token = os.environ.get(args.hf_token_env)
    if (not can_local) and not hf_token:
        print("No local generator and no HF token found. Exiting.")
        raise SystemExit(2)

    if not can_local:
        print("Using Hugging Face Inference API fallback with model:", args.model)

    with open(args.out, 'w', encoding='utf-8') as fo:
        for it in tqdm(items, desc="generating"):
            id_ = it.get("id") or it.get("example_id") or it.get("input_id") or it.get("item_id")
            prompt = it.get("input") or it.get("prompt") or it.get("question") or ""
            if not prompt:
                prompt = json.dumps(it, ensure_ascii=False)
            text = ""
            try:
                if can_local and gen_fn:
                    text = gen_fn(prompt)
                else:
                    res = hf_inference_call(args.model, prompt, hf_token, args.max_new_tokens)
                    if isinstance(res, list) and len(res)>0:
                        el = res[0]
                        if isinstance(el, dict):
                            text = el.get("generated_text") or el.get("text") or json.dumps(el, ensure_ascii=False)
                        else:
                            text = str(el)
                    elif isinstance(res, dict):
                        text = res.get("generated_text") or res.get("text") or json.dumps(res, ensure_ascii=False)
                    else:
                        text = str(res)
                text = text.replace("\\n", "\n")
            except Exception as e:
                print("Generation error for", id_, ":", e)
                text = ""
            fo.write(json.dumps({"id": id_, "prediction": text}, ensure_ascii=False) + "\\n")
            time.sleep(0.1)

    print("Wrote outputs to", args.out)

if __name__=='__main__':
    main()