from typing import Optional, List, Dict, Any, Callable, Generator, Set, Tuple
"""
GP PRO AGENT - Autonomous Agent Mode
Watches screen 24/7, learns workflows, acts automatically.
"""
import threading, time, json, hashlib
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict, deque

class WorkflowPattern:
    def __init__(self, name):
        self.name       = name
        self.steps      = []
        self.triggers   = []
        self.frequency  = 0
        self.last_seen  = None
        self.confidence = 0.0
        self.enabled    = False

    def to_dict(self):
        return {
            "name":       self.name,
            "steps":      self.steps,
            "triggers":   self.triggers,
            "frequency":  self.frequency,
            "confidence": self.confidence,
            "enabled":    self.enabled,
        }

    @classmethod
    def from_dict(cls, d):
        p = cls(d["name"])
        p.steps      = d.get("steps", [])
        p.triggers   = d.get("triggers", [])
        p.frequency  = d.get("frequency", 0)
        p.confidence = d.get("confidence", 0.0)
        p.enabled    = d.get("enabled", False)
        return p


class AutonomousAgent:
    """
    Watches everything. Learns patterns. Acts automatically.
    Like a real engineer sitting next to you 24/7.
    """
    def __init__(self, brain_root, execute_callback, notify_callback):
        self._path      = Path(brain_root) / "autonomous"
        self._path.mkdir(parents=True, exist_ok=True)
        self._execute   = execute_callback
        self._notify    = notify_callback
        self._patterns  = {}
        self._activity_log = deque(maxlen=1000)
        self._time_patterns = defaultdict(list)
        self._running   = False
        self._learning  = True
        self._acting    = False
        self._thread    = None
        self._load()
        self._add_default_patterns()

    def _add_default_patterns(self):
        defaults = [
            {
                "name": "Morning Startup",
                "triggers": ["09:00", "09:01", "09:02"],
                "steps": ["Show system status", "Check PLC alarms"],
                "enabled": False,
                "confidence": 1.0,
                "frequency": 0,
            },
            {
                "name": "PLC Backup",
                "triggers": ["17:00", "17:01"],
                "steps": ["Take a screenshot", "Save PLC project"],
                "enabled": False,
                "confidence": 1.0,
                "frequency": 0,
            },
            {
                "name": "Fault Monitor",
                "triggers": ["continuous"],
                "steps": ["Check PLC software for any alarms or faults"],
                "enabled": False,
                "confidence": 1.0,
                "frequency": 0,
            },
        ]
        for d in defaults:
            if d["name"] not in self._patterns:
                p = WorkflowPattern.from_dict(d)
                self._patterns[p.name] = p
        self._save()

    def start(self):
        self._running = True
        self._thread  = threading.Thread(
            target=self._agent_loop, daemon=True)
        self._thread.start()
        print("[AUTO-AGENT] Started — watching and learning")

    def stop(self):
        self._running = False

    def record_activity(self, action: str, context: str = ""):
        """Record user action for pattern learning."""
        now = datetime.now()
        entry = {
            "action":  action,
            "context": context,
            "time":    now.isoformat(),
            "hour":    now.hour,
            "minute":  now.minute,
            "weekday": now.weekday(),
        }
        self._activity_log.append(entry)
        time_key = f"{now.hour:02d}:{now.minute:02d}"
        self._time_patterns[time_key].append(action)
        self._learn_pattern(action, time_key)

    def _learn_pattern(self, action: str, time_key: str):
        """Learn from repeated actions at same time."""
        actions_at_time = self._time_patterns.get(time_key, [])
        if len(actions_at_time) >= 3:
            pattern_name = f"Auto: {action[:30]} at {time_key}"
            if pattern_name not in self._patterns:
                p = WorkflowPattern(pattern_name)
                p.triggers   = [time_key]
                p.steps      = [action]
                p.frequency  = len(actions_at_time)
                p.confidence = min(len(actions_at_time) / 5, 1.0)
                p.enabled    = False
                self._patterns[pattern_name] = p
                self._notify(
                    f"[AUTO-AGENT] Learned pattern: '{pattern_name}'\n"
                    f"Seen {p.frequency}x at {time_key}\n"
                    f"Enable it in Autonomous panel to automate!")
                self._save()

    def _agent_loop(self):
        """Main autonomous loop."""
        while self._running:
            try:
                now     = datetime.now()
                time_key = f"{now.hour:02d}:{now.minute:02d}"
                for name, pattern in list(self._patterns.items()):
                    if not pattern.enabled:
                        continue
                    if "continuous" in pattern.triggers:
                        self._execute_pattern(pattern)
                    elif time_key in pattern.triggers:
                        last = getattr(pattern, '_last_run', None)
                        if (last is None or
                            (now - last).total_seconds() > 60):
                            pattern._last_run = now
                            self._execute_pattern(pattern)
            except Exception as e:
                print(f"[AUTO-AGENT] Loop error: {e}")
            time.sleep(30)

    def _execute_pattern(self, pattern: WorkflowPattern):
        """Execute an automated pattern."""
        self._notify(
            f"[AUTO-AGENT] Running: {pattern.name}")
        for step in pattern.steps:
            try:
                self._execute(f"[AUTO] {step}")
                time.sleep(2)
            except Exception as e:
                print(f"[AUTO-AGENT] Step error: {e}")
        pattern.frequency += 1
        self._save()

    def enable_pattern(self, name: str, enabled: bool):
        if name in self._patterns:
            self._patterns[name].enabled = enabled
            self._save()

    def add_pattern(self, name: str, triggers: list,
                    steps: list):
        p = WorkflowPattern(name)
        p.triggers   = triggers
        p.steps      = steps
        p.confidence = 1.0
        p.enabled    = False
        self._patterns[name] = p
        self._save()
        return p

    def get_patterns(self):
        return list(self._patterns.values())

    def get_activity_log(self, n=20):
        return list(reversed(list(self._activity_log)))[:n]

    def _save(self):
        try:
            data = {k: v.to_dict()
                    for k, v in self._patterns.items()}
            with open(self._path/"patterns.json","w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"[AUTO-AGENT] Save error: {e}")

    def _load(self):
        try:
            path = self._path / "patterns.json"
            if path.exists():
                with open(path) as f:
                    data = json.load(f)
                self._patterns = {
                    k: WorkflowPattern.from_dict(v)
                    for k, v in data.items()}
                print(f"[AUTO-AGENT] Loaded {len(self._patterns)} patterns")
        except Exception:
            self._patterns = {}

    @property
    def is_running(self):
        return self._running

    @property
    def pattern_count(self):
        return len(self._patterns)

    @property
    def enabled_count(self):
        return sum(1 for p in self._patterns.values() if p.enabled)
