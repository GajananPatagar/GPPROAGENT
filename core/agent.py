import os, gc, time, json, threading
from typing import List, Dict, Tuple, Any
from pathlib import Path
from config.settings import Settings
from config.models import MODELS

PROMPTS = {
    "master":  "You are GP PRO AGENT — Senior Engineering AI. Give precise professional answers.",
    "reflex":  "You are GP PRO AGENT. Give instant direct answers. Max 3 sentences.",
    "plc":     "You are GP PRO AGENT — PLC Expert. Specialize in ladder logic Allen Bradley Siemens SCADA.",
    "coder":   "You are GP PRO AGENT — Code Expert. Write clean efficient well-commented code.",
    "screen":  "You are GP PRO AGENT — GUI Expert. Give precise steps for screen and GUI operations.",
    "safety":  "You are GP PRO AGENT — Safety Engineer. Prioritize safety. Give clear safety procedures.",
    "memory":  "You are GP PRO AGENT — Memory System. Recall and search information accurately.",
    "docs":    "You are GP PRO AGENT — Documentation Expert. Write professional technical documentation.",
    "learner": "You are GP PRO AGENT — Software Expert. Teach software operations step by step.",
    "ocr":     "You are GP PRO AGENT — Vision Expert. Extract and read text accurately.",
    "math":    "You are GP PRO AGENT — Engineering Calculator. Solve math precisely.",
}

class QueryResult:
    def __init__(self, answer, model_used, duration_s, confidence):
        self.answer     = answer
        self.model_used = model_used
        self.duration_s = duration_s
        self.confidence = confidence
        self.timestamp  = time.time()

class GPProAgent:
    def __init__(self):
        self.settings    = Settings()
        self.settings.ensure_dirs()
        self._lock       = threading.Lock()
        self._active_llm = None
        self._active_key = None
        self._history    = []
        self._learn_map  = {}
        self._load_learn()
        print(f"[GP PRO] Initialized. RAM budget: {self.settings.ram_limit_mb}MB")

    def query(self, user_input: str, priority: str = "balanced") -> QueryResult:
        start  = time.time()
        scores = self._score_models(user_input, priority)
        best   = scores[0][0]
        model  = MODELS[best]
        print(f"[GP PRO] → {model['name']} | {model['speed_s']}s | {model['accuracy']}%")
        answer   = self._ask_model(best, user_input)
        duration = round(time.time() - start, 2)
        result   = QueryResult(answer, best, duration, model["accuracy"]/100)
        self._learn(user_input, result)
        return result

    def _score_models(self, query: str, priority: str) -> List[Tuple[str,float]]:
        q = query.lower()
        scores = {}
        for key, model in MODELS.items():
            score = 0.0
            triggers = model.get("triggers", [])
            matched  = sum(1 for t in triggers if t in q)
            score   += (matched / max(len(triggers),1)) * 50
            score   += (model["accuracy"] / 100) * 30
            score   += (1 / max(model["speed_s"],0.1)) * 20
            if model["ram_mb"] > self.settings.model_ram_mb:
                score *= 0.7
            if priority == "speed":
                score += (1 / max(model["speed_s"],0.1)) * 30
            elif priority == "accuracy":
                score += (model["accuracy"] / 100) * 30
            prefs = self._learn_map.get("preferred", {})
            if key in prefs:
                score += prefs[key] * 5
            dest = self.settings.model_path / model["file"]
            if not dest.exists():
                score *= 0.1
            scores[key] = score
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        print(f"[GP PRO] Top 3: {[(k,round(v,1)) for k,v in ranked[:3]]}")
        return ranked

    def _ask_model(self, key: str, query: str) -> str:
        model = MODELS[key]
        dest  = self.settings.model_path / model["file"]
        if not dest.exists():
            return self._fallback(query)
        try:
            return self._infer(str(dest), key, query)
        except Exception as e:
            print(f"[GP PRO] Model error: {e}")
            return self._fallback(query)

    def _infer(self, model_file: str, key: str, query: str) -> str:
        try:
            from llama_cpp import Llama
            with self._lock:
                if self._active_key != key:
                    if self._active_llm:
                        del self._active_llm
                        gc.collect()
                    self._active_llm = Llama(
                        model_path   = model_file,
                        n_ctx        = self.settings.context_size,
                        n_threads    = self.settings.cpu_threads,
                        n_gpu_layers = 0,
                        verbose      = False,
                        use_mmap     = True,
                    )
                    self._active_key = key
                sys_p = PROMPTS.get(key, PROMPTS["master"])
                prompt = f"<|system|>{sys_p}<|end|>\n<|user|>{query}<|end|>\n<|assistant|>"
                resp = self._active_llm(
                    prompt,
                    max_tokens  = self.settings.max_tokens,
                    temperature = self.settings.temperature,
                    stop        = ["<|end|>","<|user|>"],
                    echo        = False,
                )
                return resp["choices"][0]["text"].strip()
        except ImportError:
            return self._fallback(query)

    def _fallback(self, query: str) -> str:
        q = query.lower()
        if any(w in q for w in ["ladder","plc","rung","coil"]):
            return "PLC: NO Contact→NC Contact→Output Coil. Timer TON=On-delay TOF=Off-delay. Counter CTU=Up CTD=Down. Check scan cycle and I/O mapping."
        if any(w in q for w in ["safety","estop","emergency"]):
            return "Safety: 1.Verify E-stop NC hardwired. 2.Check safety relay. 3.Confirm interlocks. 4.Follow LOTO. SIL rating must match risk assessment."
        if any(w in q for w in ["python","code","script"]):
            return "Python: Use modular design. Handle exceptions with try/except. Use type hints. Write docstrings. Follow PEP8."
        if any(w in q for w in ["click","screen","gui"]):
            return "GUI: 1.Identify element. 2.Get coordinates. 3.Verify visible. 4.Execute click. 5.Verify result."
        if any(w in q for w in ["calculate","math","formula"]):
            return "Math: Please provide the specific formula or values to calculate."
        return f"GP PRO AGENT: Install AI models for full intelligence. Run: python main.py --install"

    def _learn(self, query: str, result: QueryResult):
        self._history.append({"query":query,"model":result.model_used,"duration":result.duration_s})
        prefs = self._learn_map.setdefault("preferred", {})
        if result.duration_s < MODELS[result.model_used]["speed_s"] * 1.2:
            prefs[result.model_used] = prefs.get(result.model_used, 0) + 1
        if len(self._history) % 10 == 0:
            self._save_learn()

    def _save_learn(self):
        try:
            path = self.settings.cache_path / "learn_map.json"
            with open(path,"w") as f:
                json.dump(self._learn_map, f, indent=2)
        except: pass

    def _load_learn(self):
        try:
            path = self.settings.cache_path / "learn_map.json"
            if path.exists():
                with open(path) as f:
                    self._learn_map = json.load(f)
        except:
            self._learn_map = {}

    def run_cli(self):
        print("\n╔══════════════════════════════════╗")
        print("║    GP PRO AGENT — CLI Mode      ║")
        print("║  Type exit to quit              ║")
        print("╚══════════════════════════════════╝\n")
        while True:
            try:
                inp = input("GP PRO> ").strip()
                if not inp: continue
                if inp.lower() in ("exit","quit"): break
                if inp.lower() == "status":
                    self.print_status()
                    continue
                r = self.query(inp)
                print(f"\n[{r.model_used.upper()} | {r.duration_s}s | {r.confidence*100:.0f}%]")
                print(r.answer, "\n")
            except (KeyboardInterrupt, EOFError):
                break

    def print_status(self):
        from config.models import TOTAL_GB
        print("═"*55)
        print("  GP PRO AGENT — STATUS")
        print("═"*55)
        print(f"  Brain Path : {self.settings.brain_root}")
        print(f"  RAM Budget : {self.settings.ram_limit_mb}MB")
        print(f"  Models     : {len(MODELS)}")
        print(f"  Brain Size : ~{TOTAL_GB:.1f}GB")
        print("─"*55)
        for key, model in MODELS.items():
            p = self.settings.model_path / model["file"]
            s = "✓ Ready" if p.exists() else "✗ Not installed"
            print(f"  [{key:8s}] {s:14s} | {model['speed_s']}s | {model['accuracy']}% | {model['size_gb']}GB")
        print("═"*55)
