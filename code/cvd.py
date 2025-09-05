import re, time, json, random, requests
from dataclasses import dataclass
from typing import Dict, Any, List, Tuple, Optional
from jsonschema import Draft7Validator

@dataclass
class VerifyConfig:
    forbidden_path: str
    output_schema_path: str
    min_len: int = 1
    max_items: int = 10
    regex_must_match: Optional[str] = None

class Verifier:
    def __init__(self, cfg: VerifyConfig):
        with open(cfg.forbidden_path, "r", encoding="utf-8") as f:
            self.forbidden = [ln.strip() for ln in f if ln.strip()]
        with open(cfg.output_schema_path, "r", encoding="utf-8") as f:
            self.schema = json.load(f)
        self.validator = Draft7Validator(self.schema)
        self.cfg = cfg

    def _json_try(self, text: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
        try:
            obj = json.loads(text)
            return True, obj
        except Exception:
            return False, None

    def check(self, output_text: str) -> Tuple[bool, List[str]]:
        reasons = []

        low = output_text.lower()
        for term in self.forbidden:
            if term and term.lower() in low:
                reasons.append(f"forbidden:{term}")

        if len(output_text.strip()) < self.cfg.min_len:
            reasons.append("too_short")

        if self.cfg.regex_must_match:
            if not re.fullmatch(self.cfg.regex_must_match, output_text.strip(), flags=re.DOTALL):
                reasons.append("regex_mismatch")

        ok_json, obj = self._json_try(output_text)
        if ok_json and obj is not None:
            errs = sorted(self.validator.iter_errors(obj), key=lambda e: e.path)
            if errs:
                reasons.append("jsonschema_invalid")
        else:
            pass

        return (len(reasons) == 0), reasons

class ModelClient:
    def __init__(self, backend="ollama", model_name="llama3", temperature=0.2):
        self.backend = backend
        self.model_name = model_name
        self.temperature = float(temperature)

    def generate(self, prompt: str, system: Optional[str]=None, max_tokens: int=512, timeout_s=120) -> str:
        if self.backend == "ollama":
            payload = {
                "model": self.model_name,
                "prompt": (system + "\n\n" + prompt) if system else prompt,
                "options": {"temperature": self.temperature},
                "stream": False
            }
            r = requests.post("http://localhost:11434/api/generate", json=payload, timeout=timeout_s)
            r.raise_for_status()
            data = r.json()
            return data.get("response", "").strip()
        elif self.backend == "openai":
            raise NotImplementedError("OpenAI backend not implemented in this snippet.")
        else:
            return f"[DRY-RUN OUTPUT] {prompt[:120]}..."

@dataclass
class CVDConfig:
    constrained: bool = False
    use_verifier: bool = False
    self_correct: int = 0

class CVDRunner:
    def __init__(self, model: ModelClient, verifier: Optional[Verifier], cvd_cfg: CVDConfig):
        self.model = model
        self.verifier = verifier
        self.cvd_cfg = cvd_cfg

    def run_once(self, prompt: str, system: Optional[str]) -> Dict[str, Any]:
        t0 = time.time()
        out = self.model.generate(prompt, system=system)
        latency_ms = int((time.time() - t0) * 1000)
        tokens = max(1, len(out.split()))
        result = {"text": out, "latency_ms": latency_ms, "tokens": tokens}

        if self.cvd_cfg.use_verifier and self.verifier:
            ok, reasons = self.verifier.check(out)
            result["pass"] = ok
            result["reasons"] = reasons
        return result

    def run_with_correction(self, prompt: str, system: Optional[str]) -> Dict[str, Any]:
        res = self.run_once(prompt, system)
        if not self.cvd_cfg.use_verifier or not self.verifier:
            return res

        if res.get("pass", True):
            return res

        attempt = 0
        cur = res
        while attempt < self.cvd_cfg.self_correct and not cur["pass"]:
            attempt += 1
            reason = "; ".join(cur.get("reasons", [])) or "violation"
            repair_inst = f"\n\n[Repair hint] The output failed: {reason}. Fix and re-output. Keep it concise."
            next_out = self.run_once(prompt + repair_inst, system)
            cur = next_out
        return cur