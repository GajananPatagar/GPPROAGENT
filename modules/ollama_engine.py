"""
GP PRO AGENT - Ollama AI Engine
REAL AI using Ollama local server.
Actually uses the brain models - not fake hardcoded answers.
Supports: phi3, mistral, llama3, codellama, gemma, qwen2
"""
import json, time, threading, subprocess, sys, os
import urllib.request, urllib.error
from typing import Optional, Callable, Generator

OLLAMA_URL  = "http://localhost:11434"
OLLAMA_API  = f"{OLLAMA_URL}/api"

# Brain to Ollama model mapping
BRAIN_MODELS = {
    "master":  "mistral",      # Best reasoning
    "reflex":  "phi3",         # Fastest
    "plc":     "mistral",      # PLC expert
    "coder":   "codellama",    # Code expert
    "screen":  "phi3",         # Fast screen tasks
    "safety":  "mistral",      # Safety critical
    "memory":  "phi3",         # Fast memory
    "docs":    "mistral",      # Documentation
    "learner": "phi3",         # Learning tasks
    "ocr":     "phi3",         # OCR tasks
    "math":    "phi3",         # Math calculations
}

BRAIN_PROMPTS = {
    "master": (
        "You are GP PRO AGENT - a senior engineering AI assistant. "
        "Give precise, professional, detailed answers. "
        "Be accurate and actionable."
    ),
    "reflex": (
        "You are GP PRO AGENT. Give short, direct, accurate answers. "
        "Maximum 3 sentences unless more detail is needed."
    ),
    "plc": (
        "You are GP PRO AGENT - a PLC and industrial automation expert. "
        "You have deep knowledge of Allen Bradley Studio 5000, Siemens TIA Portal, "
        "ladder logic, SCADA, Modbus TCP/RTU, Profibus, EtherNet/IP, and IEC 61131-3. "
        "Give expert, professional engineering answers with specific details."
    ),
    "coder": (
        "You are GP PRO AGENT - an expert programmer. "
        "Write clean, efficient, well-commented code. "
        "Always explain what the code does and include error handling."
    ),
    "screen": (
        "You are GP PRO AGENT - a GUI automation expert. "
        "Give precise step-by-step instructions for screen automation using pyautogui. "
        "Include actual code examples."
    ),
    "safety": (
        "You are GP PRO AGENT - an industrial safety engineer. "
        "ALWAYS prioritize safety above everything else. "
        "Reference standards: IEC 61508, ISO 13849, IEC 62061, SIL levels, LOTO. "
        "Give clear, professional safety procedures."
    ),
    "docs": (
        "You are GP PRO AGENT - a technical writer. "
        "Write clear, professional, well-structured technical documentation. "
        "Use proper formatting and clear language."
    ),
    "learner": (
        "You are GP PRO AGENT - a software operation expert. "
        "Give clear step-by-step instructions to operate software. "
        "Be specific and beginner-friendly."
    ),
    "math": (
        "You are GP PRO AGENT - an engineering calculator. "
        "Solve math problems and engineering calculations precisely. "
        "Show all steps and units clearly."
    ),
    "memory": (
        "You are GP PRO AGENT - a knowledge assistant. "
        "Recall and present information accurately and clearly."
    ),
    "ocr": (
        "You are GP PRO AGENT - a vision and text extraction expert. "
        "Help analyze and extract information from screen content."
    ),
}


class OllamaEngine:
    """
    REAL AI engine using Ollama.
    Actually runs brain models locally.
    No fake hardcoded answers.
    """
    def __init__(self, notify_callback=None):
        self._notify      = notify_callback or print
        self._available   = False
        self._models      = {}
        self._active_gen  = None
        self._lock        = threading.Lock()
        threading.Thread(target=self._check_ollama,
                        daemon=True).start()

    def _check_ollama(self):
        """Check if Ollama is running and get available models."""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                req = urllib.request.Request(
                    f"{OLLAMA_API}/tags",
                    headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=5) as r:
                    data    = json.loads(r.read())
                    models  = [m["name"].split(":")[0]
                               for m in data.get("models", [])]
                    self._models    = {m: True for m in models}
                    self._available = True
                    print(f"[OLLAMA] Connected! Models: {models}")
                    if self._notify:
                        self._notify(
                            f"[AI ENGINE] Ollama connected!\n"
                            f"Available models: {', '.join(models)}\n"
                            f"Real AI responses now active!")
                    return
            except Exception as e:
                print(f"[OLLAMA] Attempt {attempt+1}: {e}")
                time.sleep(2)

        print("[OLLAMA] Not available - start Ollama first")
        if self._notify:
            self._notify(
                "[AI ENGINE] Ollama not found!\n"
                "Install from: ollama.com\n"
                "Then run: ollama pull phi3\n"
                "Using expert knowledge mode until then.")

    def is_available(self) -> bool:
        return self._available

    def get_model_for_brain(self, brain: str) -> str:
        """Get best available model for brain."""
        preferred = BRAIN_MODELS.get(brain, "phi3")
        # Try preferred first
        if preferred in self._models:
            return preferred
        # Fallback order
        fallbacks = ["phi3", "mistral", "llama3",
                    "llama2", "gemma", "qwen2"]
        for model in fallbacks:
            if model in self._models:
                return model
        # Return any available model
        if self._models:
            return list(self._models.keys())[0]
        return "phi3"

    def ask(self, brain: str, query: str,
            stream_callback: Optional[Callable] = None,
            context: str = "") -> str:
        """
        Ask a brain model - REAL AI response.
        Supports streaming for live output.
        """
        if not self._available:
            return self._knowledge_fallback(brain, query)

        model      = self.get_model_for_brain(brain)
        sys_prompt = BRAIN_PROMPTS.get(brain, BRAIN_PROMPTS["master"])

        # Build messages
        messages = [
            {"role": "system",    "content": sys_prompt},
        ]
        if context:
            messages.append({
                "role":    "system",
                "content": f"Context: {context}"
            })
        messages.append({"role": "user", "content": query})

        try:
            if stream_callback:
                return self._stream_response(
                    model, messages, stream_callback)
            else:
                return self._sync_response(model, messages)
        except Exception as e:
            print(f"[OLLAMA] Error: {e}")
            return self._knowledge_fallback(brain, query)

    def _sync_response(self, model: str,
                       messages: list) -> str:
        """Get complete response synchronously."""
        payload = json.dumps({
            "model":    model,
            "messages": messages,
            "stream":   False,
            "options":  {
                "temperature": 0.1,
                "num_predict": 800,
                "top_p":       0.9,
            }
        }).encode()

        req = urllib.request.Request(
            f"{OLLAMA_API}/chat",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST")

        with urllib.request.urlopen(req, timeout=120) as r:
            data   = json.loads(r.read())
            result = data.get("message", {}).get("content", "")
            return result.strip()

    def _stream_response(self, model: str,
                         messages: list,
                         callback: Callable) -> str:
        """Stream response token by token for live output."""
        payload = json.dumps({
            "model":    model,
            "messages": messages,
            "stream":   True,
            "options":  {
                "temperature": 0.1,
                "num_predict": 800,
            }
        }).encode()

        req = urllib.request.Request(
            f"{OLLAMA_API}/chat",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST")

        full_response = ""
        with urllib.request.urlopen(req, timeout=120) as r:
            for line in r:
                if not line.strip():
                    continue
                try:
                    data    = json.loads(line.decode())
                    token   = data.get("message", {}).get("content", "")
                    if token:
                        full_response += token
                        callback(token)
                    if data.get("done", False):
                        break
                except json.JSONDecodeError:
                    continue
        return full_response.strip()

    def generate_code(self, description: str,
                      language: str = "python") -> str:
        """Generate real code using codellama."""
        brain = "coder"
        query = (f"Write a complete {language} program for:\n"
                f"{description}\n\n"
                f"Include: imports, main function, "
                f"error handling, comments.")
        return self.ask(brain, query)

    def explain(self, topic: str, level: str = "expert") -> str:
        """Explain any topic at specified level."""
        query = (f"Explain '{topic}' at {level} level. "
                f"Be thorough and include examples.")
        return self.ask("master", query)

    def review_code(self, code: str) -> str:
        """Review and improve code."""
        query = (f"Review this code and provide:\n"
                f"1. Issues found\n"
                f"2. Improvements\n"
                f"3. Fixed version\n\n"
                f"Code:\n{code}")
        return self.ask("coder", query)

    def translate_plc(self, description: str,
                      from_brand: str = "allen_bradley",
                      to_brand: str = "siemens") -> str:
        """Translate PLC logic between brands."""
        query = (f"Translate this PLC logic from "
                f"{from_brand} to {to_brand}:\n{description}\n\n"
                f"Show equivalent instructions and any differences.")
        return self.ask("plc", query)

    def safety_check(self, design: str) -> str:
        """Safety check any design."""
        query = (f"Perform a safety review of:\n{design}\n\n"
                f"Identify: hazards, SIL requirements, "
                f"missing safety measures, recommendations.")
        return self.ask("safety", query)

    def _knowledge_fallback(self, brain: str,
                            query: str) -> str:
        """Fallback when Ollama unavailable."""
        q = query.lower()
        if any(w in q for w in ["plc","ladder","rung"]):
            return ("PLC Expert Mode (Ollama offline):\n"
                   "XIC=Examine If Closed | XIO=Examine If Open\n"
                   "OTE=Output Energize | OTL=Latch | OTU=Unlatch\n"
                   "TON=On-Delay Timer | TOF=Off-Delay | CTU=Count Up\n\n"
                   "Start Ollama for full AI: ollama pull mistral")
        if any(w in q for w in ["python","code"]):
            return ("Code Expert Mode (Ollama offline):\n"
                   "Install Ollama for real code generation.\n"
                   "Run: ollama pull codellama")
        return (f"GP PRO AGENT [{brain}]:\n"
               f"Ollama not running. Start it for real AI.\n"
               f"Install: ollama.com | Run: ollama pull phi3")

    def install_model(self, model: str,
                      progress_callback: Optional[Callable]=None) -> bool:
        """Pull/install a model via Ollama."""
        try:
            payload = json.dumps({"name": model}).encode()
            req = urllib.request.Request(
                f"{OLLAMA_API}/pull",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST")
            with urllib.request.urlopen(req, timeout=600) as r:
                for line in r:
                    if not line.strip():
                        continue
                    try:
                        data = json.loads(line.decode())
                        if progress_callback:
                            status    = data.get("status","")
                            completed = data.get("completed", 0)
                            total     = data.get("total", 0)
                            progress_callback(status, completed, total)
                        if data.get("status") == "success":
                            self._models[model] = True
                            return True
                    except Exception:
                        pass
            return True
        except Exception as e:
            print(f"[OLLAMA] Install error: {e}")
            return False

    def get_status(self) -> dict:
        """Get Ollama engine status."""
        return {
            "available":    self._available,
            "models":       list(self._models.keys()),
            "url":          OLLAMA_URL,
            "brain_map":    BRAIN_MODELS,
        }

    def list_available_models(self) -> list:
        """List all available models."""
        try:
            req = urllib.request.Request(f"{OLLAMA_API}/tags")
            with urllib.request.urlopen(req, timeout=5) as r:
                data = json.loads(r.read())
                return data.get("models", [])
        except Exception:
            return []
