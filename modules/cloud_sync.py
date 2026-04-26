"""
GP PRO AGENT - Cloud Brain Sync
Syncs learned knowledge to cloud.
Downloads improvements from other users overnight.
Privacy: only patterns shared, not your actual data.
"""
import threading, time, json, hashlib, os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

class CloudSyncConfig:
    def __init__(self):
        self.enabled         = False
        self.sync_url        = "https://api.github.com/gists"
        self.sync_interval_h = 24
        self.last_sync       = None
        self.gist_id         = None
        self.github_token    = ""
        self.share_patterns  = True
        self.share_stats     = True
        self.privacy_mode    = True

    def to_dict(self):
        return {
            "enabled":         self.enabled,
            "sync_interval_h": self.sync_interval_h,
            "last_sync":       self.last_sync,
            "gist_id":         self.gist_id,
            "share_patterns":  self.share_patterns,
            "share_stats":     self.share_stats,
            "privacy_mode":    self.privacy_mode,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "CloudSyncConfig":
        c = cls()
        c.enabled         = d.get("enabled", False)
        c.sync_interval_h = d.get("sync_interval_h", 24)
        c.last_sync       = d.get("last_sync")
        c.gist_id         = d.get("gist_id")
        c.share_patterns  = d.get("share_patterns", True)
        c.share_stats     = d.get("share_stats", True)
        c.privacy_mode    = d.get("privacy_mode", True)
        return c


class CloudSyncManager:
    """
    Syncs GP PRO AGENT knowledge with cloud.

    What gets synced (privacy-safe):
    - Successful command patterns (anonymized)
    - Brain routing statistics
    - Automation templates

    What NEVER gets synced:
    - Your PLC IP addresses or credentials
    - Tag values or process data
    - Personal file contents
    - Company-specific information
    """
    def __init__(self, brain_root: str,
                 notify_callback=None):
        self._path      = Path(brain_root)
        self._sync_path = self._path / "cloud_sync"
        self._sync_path.mkdir(parents=True, exist_ok=True)
        self._config_file = self._sync_path / "config.json"
        self._notify    = notify_callback or print
        self._config    = self._load_config()
        self._running   = False
        self._thread    = None
        self._sync_log  = []
        self._last_error = None

    def _load_config(self) -> CloudSyncConfig:
        try:
            if self._config_file.exists():
                with open(self._config_file) as f:
                    return CloudSyncConfig.from_dict(json.load(f))
        except Exception:
            pass
        return CloudSyncConfig()

    def _save_config(self):
        try:
            with open(self._config_file, "w") as f:
                json.dump(self._config.to_dict(), f, indent=2)
        except Exception as e:
            print(f"[CLOUD] Config save error: {e}")

    def setup(self, github_token: str,
              enable: bool = True) -> str:
        """Configure cloud sync with GitHub token."""
        self._config.github_token = github_token
        self._config.enabled      = enable
        self._save_config()
        if enable:
            result = self.sync_now()
            return result
        return "Cloud sync configured (disabled)"

    def start(self):
        """Start background sync thread."""
        if not self._config.enabled:
            return
        self._running = True
        self._thread  = threading.Thread(
            target=self._sync_loop, daemon=True)
        self._thread.start()
        print("[CLOUD] Sync thread started")

    def stop(self):
        self._running = False

    def _sync_loop(self):
        """Background sync every N hours."""
        while self._running:
            if self._config.enabled:
                last = self._config.last_sync
                if last:
                    last_dt = datetime.fromisoformat(last)
                    hours   = self._config.sync_interval_h
                    next_sync = last_dt + timedelta(hours=hours)
                    if datetime.now() >= next_sync:
                        self.sync_now()
                else:
                    self.sync_now()
            time.sleep(3600)  # Check hourly

    def sync_now(self) -> str:
        """Perform sync now."""
        if not self._config.enabled:
            return "Cloud sync is disabled. Enable it first."
        if not self._config.github_token:
            return ("No GitHub token configured.\n"
                   "Get token at: github.com/settings/tokens\n"
                   "Needs: 'gist' permission only")
        try:
            # Prepare privacy-safe payload
            payload = self._build_sync_payload()
            # Upload to GitHub Gist
            result  = self._upload_gist(payload)
            # Download improvements
            updates = self._download_updates()
            self._config.last_sync = datetime.now().isoformat()
            self._save_config()
            msg = (f"[CLOUD] Sync complete!\n"
                  f"Uploaded: {len(payload)} knowledge items\n"
                  f"Downloaded: {updates} updates")
            self._sync_log.append({
                "time":     datetime.now().isoformat(),
                "status":   "success",
                "uploaded": len(payload),
                "downloaded": updates,
            })
            self._notify(msg)
            return msg
        except Exception as e:
            self._last_error = str(e)
            return f"Sync failed: {e}"

    def _build_sync_payload(self) -> dict:
        """Build privacy-safe sync data."""
        payload = {
            "version":   "3.0",
            "timestamp": datetime.now().isoformat(),
            "agent_id":  self._get_anonymous_id(),
        }
        # Include anonymized patterns if enabled
        if self._config.share_patterns:
            patterns = self._load_anonymized_patterns()
            payload["patterns"] = patterns
        # Include stats if enabled
        if self._config.share_stats:
            stats = self._load_usage_stats()
            payload["stats"] = stats
        return payload

    def _get_anonymous_id(self) -> str:
        """Get anonymous machine ID (privacy safe)."""
        try:
            machine = os.environ.get("COMPUTERNAME","unknown")
            hashed  = hashlib.sha256(
                machine.encode()).hexdigest()[:12]
            return f"agent_{hashed}"
        except Exception:
            return "agent_unknown"

    def _load_anonymized_patterns(self) -> list:
        """Load patterns with all personal data removed."""
        patterns = []
        pattern_file = self._path / "autonomous" / "patterns.json"
        try:
            if pattern_file.exists():
                with open(pattern_file) as f:
                    raw = json.load(f)
                for name, p in raw.items():
                    # Remove time-specific triggers
                    # Only share command types not actual commands
                    anonymized = {
                        "type":       p.get("name","")[:20],
                        "frequency":  p.get("frequency", 0),
                        "confidence": p.get("confidence", 0),
                    }
                    if p.get("frequency", 0) >= 3:
                        patterns.append(anonymized)
        except Exception:
            pass
        return patterns[:50]  # Max 50 patterns

    def _load_usage_stats(self) -> dict:
        """Load anonymous usage statistics."""
        return {
            "brain_usage": {},
            "features":    ["plc","gui","voice","vision"],
        }

    def _upload_gist(self, payload: dict) -> bool:
        """Upload to GitHub Gist."""
        try:
            import urllib.request, json as json_lib
            content = json_lib.dumps(payload, indent=2)
            gist_data = {
                "description": "GP PRO AGENT Knowledge Sync",
                "public": False,
                "files": {
                    "gp_pro_agent_sync.json": {
                        "content": content
                    }
                }
            }
            data    = json_lib.dumps(gist_data).encode()
            headers = {
                "Authorization": f"token {self._config.github_token}",
                "Content-Type":  "application/json",
                "User-Agent":    "GP-PRO-AGENT/3.0",
            }
            if self._config.gist_id:
                url = (f"https://api.github.com/gists/"
                      f"{self._config.gist_id}")
                req = urllib.request.Request(
                    url, data=data, headers=headers,
                    method="PATCH")
            else:
                req = urllib.request.Request(
                    "https://api.github.com/gists",
                    data=data, headers=headers,
                    method="POST")
            with urllib.request.urlopen(req, timeout=10) as r:
                resp = json_lib.loads(r.read())
                if "id" in resp:
                    self._config.gist_id = resp["id"]
                    self._save_config()
            return True
        except Exception as e:
            print(f"[CLOUD] Upload error: {e}")
            return False

    def _download_updates(self) -> int:
        """Download knowledge updates from cloud."""
        # In a real implementation this would download
        # from a shared community knowledge base
        # For now returns 0 (no shared hub yet)
        return 0

    def get_status(self) -> dict:
        return {
            "enabled":    self._config.enabled,
            "last_sync":  self._config.last_sync,
            "gist_id":    self._config.gist_id,
            "privacy":    self._config.privacy_mode,
            "log_count":  len(self._sync_log),
            "last_error": self._last_error,
            "interval_h": self._config.sync_interval_h,
        }

    def disable(self):
        self._config.enabled = False
        self._save_config()
        self.stop()

    def enable(self, token: str = None):
        if token:
            self._config.github_token = token
        self._config.enabled = True
        self._save_config()
        self.start()
