import os, sys, platform, json
from pathlib import Path

BASE_DIR = Path(os.path.dirname(os.path.abspath(__file__))).parent
BRAIN_ROOT = Path("C:/GPProAgent") if platform.system()=="Windows" else Path.home()/"GPProAgent"

class Settings:
    def __init__(self):
        self.app_name       = "GP PRO AGENT"
        self.version        = "1.0.0"
        self.brain_root     = BRAIN_ROOT
        self.model_path     = BRAIN_ROOT/"models"
        self.knowledge_path = BRAIN_ROOT/"knowledge"
        self.cache_path     = BRAIN_ROOT/"cache"
        self.log_path       = BRAIN_ROOT/"logs"
        self.ram_limit_mb   = 600
        self.model_ram_mb   = 400
        self.cpu_threads    = os.cpu_count() or 4
        self.context_size   = 4096
        self.max_tokens     = 1024
        self.temperature    = 0.1
        self.ui = {"accent_color":"#00e5ff","font_size":10,"window_title":"GP PRO AGENT v1.0.0"}
        self._load_ui()

    def ensure_dirs(self):
        for p in [self.model_path,self.knowledge_path,self.cache_path,self.log_path]:
            p.mkdir(parents=True,exist_ok=True)

    def is_installed(self):
        return (self.brain_root/"model_router.json").exists()

    def _load_ui(self):
        try:
            p = self.brain_root/"ui_config.json"
            if p.exists():
                with open(p) as f:
                    self.ui.update(json.load(f))
        except: pass

    def save_ui(self):
        try:
            p = self.brain_root/"ui_config.json"
            p.parent.mkdir(parents=True,exist_ok=True)
            with open(p,"w") as f:
                json.dump(self.ui,f,indent=2)
        except: pass
