import os, platform
from pathlib import Path

if platform.system() == "Windows":
    BRAIN_ROOT = Path("C:/GPProAgent")
else:
    BRAIN_ROOT = Path.home() / "GPProAgent"

class Settings:
    def __init__(self):
        self.app_name       = "GP PRO AGENT"
        self.version        = "1.0.0"
        self.brain_root     = BRAIN_ROOT
        self.model_path     = BRAIN_ROOT / "models"
        self.knowledge_path = BRAIN_ROOT / "knowledge"
        self.cache_path     = BRAIN_ROOT / "cache"
        self.log_path       = BRAIN_ROOT / "logs"
        self.ram_limit_mb   = 600
        self.model_ram_mb   = 400
        self.cpu_threads    = os.cpu_count() or 4
        self.context_size   = 4096
        self.max_tokens     = 1024
        self.temperature    = 0.1
        self.offline_mode   = True

    def ensure_dirs(self):
        for p in [self.model_path, self.knowledge_path,
                  self.cache_path, self.log_path]:
            p.mkdir(parents=True, exist_ok=True)
