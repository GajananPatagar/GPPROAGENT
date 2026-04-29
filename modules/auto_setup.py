"""
GP PRO AGENT - Auto Setup
Downloads and installs everything automatically.
User just opens EXE - nothing manual needed.
"""
from typing import Optional, Callable
import os, sys, time, json, threading, subprocess, urllib.request
from pathlib import Path

OLLAMA_WIN_URL = "https://ollama.com/download/OllamaSetup.exe"
OLLAMA_CHECK   = "http://localhost:11434/api/tags"

class AutoSetup:
    """
    Automatically sets up everything:
    1. Downloads Ollama installer
    2. Installs Ollama silently
    3. Pulls required AI models
    4. Verifies everything works
    """
    def __init__(self, brain_root: str,
                 progress_callback: Optional[Callable] = None,
                 done_callback: Optional[Callable] = None):
        self._root     = Path(brain_root)
        self._root.mkdir(parents=True, exist_ok=True)
        self._progress = progress_callback or print
        self._done     = done_callback or (lambda: None)
        self._setup_file = self._root / "setup_complete.json"
        self._running  = False

    def is_setup_complete(self) -> bool:
        """Check if setup was already done."""
        return self._setup_file.exists() and self._ollama_running()

    def _ollama_running(self) -> bool:
        try:
            with urllib.request.urlopen(OLLAMA_CHECK, timeout=3) as r:
                return r.status == 200
        except Exception:
            return False

    def _ollama_installed(self) -> bool:
        """Check if Ollama is installed."""
        paths = [
            Path(os.environ.get("LOCALAPPDATA","")) / "Programs/Ollama/ollama.exe",
            Path("C:/Program Files/Ollama/ollama.exe"),
            Path(os.environ.get("USERPROFILE","")) / "AppData/Local/Programs/Ollama/ollama.exe",
        ]
        for p in paths:
            if p.exists():
                return True
        try:
            result = subprocess.run(
                ["ollama","--version"],
                capture_output=True, timeout=5)
            return result.returncode == 0
        except Exception:
            return False

    def run_setup(self):
        """Run complete auto-setup in background."""
        self._running = True
        threading.Thread(target=self._setup_loop,
                        daemon=True).start()

    def _setup_loop(self):
        try:
            self._progress("status", "Checking AI engine...", 0)
            # Step 1: Check if Ollama running
            if self._ollama_running():
                self._progress("status","Ollama already running!",20)
                self._pull_models()
                return

            # Step 2: Check if installed but not running
            if self._ollama_installed():
                self._progress("status","Starting Ollama...",10)
                self._start_ollama()
                time.sleep(3)
                if self._ollama_running():
                    self._pull_models()
                    return

            # Step 3: Download and install
            self._progress("status","Downloading AI engine...",5)
            installer = self._download_ollama()
            if installer:
                self._progress("status","Installing AI engine...",30)
                self._install_ollama(installer)
                time.sleep(5)
                self._start_ollama()
                time.sleep(5)
                if self._ollama_running():
                    self._pull_models()
                else:
                    self._progress("error",
                        "Ollama install failed. Run manually: ollama.com",100)
            else:
                self._progress("error",
                    "Download failed. Check internet connection.",100)
        except Exception as e:
            self._progress("error", f"Setup error: {e}", 100)

    def _download_ollama(self) -> Optional[Path]:
        """Download Ollama installer."""
        dest = self._root / "OllamaSetup.exe"
        if dest.exists():
            return dest
        try:
            req = urllib.request.Request(
                OLLAMA_WIN_URL,
                headers={"User-Agent": "GP-PRO-AGENT/4.0"})
            with urllib.request.urlopen(req, timeout=60) as r:
                total = int(r.headers.get("Content-Length",0))
                downloaded = 0
                with open(dest,"wb") as f:
                    while True:
                        chunk = r.read(1024*1024)
                        if not chunk: break
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total:
                            pct = int(downloaded/total*30)
                            self._progress("download",
                                f"Downloading AI engine: {downloaded//1048576}MB",
                                5+pct)
            return dest
        except Exception as e:
            print(f"[SETUP] Download error: {e}")
            return None

    def _install_ollama(self, installer: Path):
        """Install Ollama silently."""
        try:
            subprocess.run(
                [str(installer), "/S"],
                timeout=120, check=False)
            self._progress("status","AI engine installed!",45)
        except Exception as e:
            print(f"[SETUP] Install error: {e}")

    def _start_ollama(self):
        """Start Ollama server."""
        try:
            paths = [
                Path(os.environ.get("LOCALAPPDATA","")) / "Programs/Ollama/ollama.exe",
                Path("C:/Program Files/Ollama/ollama.exe"),
            ]
            for p in paths:
                if p.exists():
                    subprocess.Popen([str(p),"serve"],
                                    creationflags=0x08000000
                                    if sys.platform=="win32" else 0)
                    self._progress("status","AI engine starting...",50)
                    return
            subprocess.Popen(["ollama","serve"],
                            creationflags=0x08000000
                            if sys.platform=="win32" else 0)
        except Exception as e:
            print(f"[SETUP] Start error: {e}")

    def _pull_models(self):
        """Pull required AI models."""
        models = [
            ("phi3",      "Fast Brain - 2.4GB"),
            ("mistral",   "Smart Brain - 4.1GB"),
            ("codellama", "Code Brain - 3.8GB"),
        ]
        base_pct = 55
        step = 15
        for i,(model,desc) in enumerate(models):
            self._progress("model",
                f"Downloading {desc}...", base_pct + i*step)
            try:
                payload = json.dumps({"name":model}).encode()
                req = urllib.request.Request(
                    "http://localhost:11434/api/pull",
                    data=payload,
                    headers={"Content-Type":"application/json"},
                    method="POST")
                with urllib.request.urlopen(req,timeout=600) as r:
                    for line in r:
                        if not line.strip(): continue
                        try:
                            data = json.loads(line.decode())
                            status   = data.get("status","")
                            completed = data.get("completed",0)
                            total    = data.get("total",0)
                            if total:
                                sub_pct = int(completed/total*step)
                                self._progress("model",
                                    f"{model}: {completed//1048576}MB/{total//1048576}MB",
                                    base_pct+i*step+sub_pct)
                            if data.get("status")=="success":
                                break
                        except Exception:
                            pass
                self._progress("model",
                    f"{model} ready!", base_pct+(i+1)*step)
            except Exception as e:
                self._progress("warning",
                    f"{model} failed: {e}",
                    base_pct+(i+1)*step)

        # Save setup complete
        with open(self._setup_file,"w") as f:
            json.dump({
                "completed": time.strftime("%Y-%m-%d %H:%M:%S"),
                "models": [m[0] for m in models],
            }, f)
        self._progress("done",
            "Setup complete! All AI brains ready!", 100)
        self._done()
