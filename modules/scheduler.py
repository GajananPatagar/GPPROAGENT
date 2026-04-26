"""
GP PRO AGENT — Auto Task Scheduler
Schedule tasks to run automatically. 24/7 background operation.
"""
import json, time, threading
from pathlib import Path
from datetime import datetime, timedelta
from typing import Callable, List, Dict, Optional

class ScheduledTask:
    def __init__(self, name: str, command: str,
                 schedule: str, enabled: bool=True):
        self.name     = name
        self.command  = command
        self.schedule = schedule  # "daily 09:00", "hourly", "every 30m"
        self.enabled  = enabled
        self.last_run: Optional[datetime] = None
        self.run_count = 0
        self.next_run  = self._calc_next()

    def _calc_next(self) -> datetime:
        now = datetime.now()
        s   = self.schedule.lower().strip()
        if s == "hourly":
            return now + timedelta(hours=1)
        if s.startswith("every "):
            # "every 30m" or "every 2h"
            part = s.replace("every ","")
            if part.endswith("m"):
                mins = int(part[:-1])
                return now + timedelta(minutes=mins)
            if part.endswith("h"):
                hrs = int(part[:-1])
                return now + timedelta(hours=hrs)
        if s.startswith("daily "):
            # "daily 09:00"
            t = s.replace("daily ","").strip()
            h, m = map(int, t.split(":"))
            target = now.replace(hour=h, minute=m,
                                second=0, microsecond=0)
            if target <= now:
                target += timedelta(days=1)
            return target
        if s == "startup":
            return now + timedelta(seconds=5)
        return now + timedelta(hours=1)

    def is_due(self) -> bool:
        return self.enabled and datetime.now() >= self.next_run

    def mark_ran(self):
        self.last_run  = datetime.now()
        self.run_count += 1
        self.next_run   = self._calc_next()

    def to_dict(self) -> Dict:
        return {
            "name":      self.name,
            "command":   self.command,
            "schedule":  self.schedule,
            "enabled":   self.enabled,
            "run_count": self.run_count,
            "last_run":  self.last_run.isoformat() if self.last_run else None,
        }

    @classmethod
    def from_dict(cls, d: Dict) -> "ScheduledTask":
        t = cls(d["name"], d["command"],
                d["schedule"], d.get("enabled", True))
        t.run_count = d.get("run_count", 0)
        if d.get("last_run"):
            t.last_run = datetime.fromisoformat(d["last_run"])
        return t


class TaskScheduler:
    def __init__(self, brain_root: str,
                 execute_callback: Callable):
        self._path     = Path(brain_root) / "scheduler"
        self._path.mkdir(parents=True, exist_ok=True)
        self._file     = self._path / "tasks.json"
        self._execute  = execute_callback
        self._tasks: List[ScheduledTask] = []
        self._running  = False
        self._thread   = None
        self._lock     = threading.Lock()
        self._load()
        self._add_defaults()

    def _add_defaults(self):
        """Add default useful tasks if none exist."""
        if not self._tasks:
            defaults = [
                ScheduledTask(
                    "Morning Status Check",
                    "Show system status and ready brain models",
                    "daily 09:00",
                    enabled=False
                ),
                ScheduledTask(
                    "Hourly Screenshot",
                    "Take a screenshot and save it",
                    "hourly",
                    enabled=False
                ),
                ScheduledTask(
                    "PLC Alarm Check",
                    "Check PLC software for any alarms or faults",
                    "every 30m",
                    enabled=False
                ),
            ]
            self._tasks.extend(defaults)
            self._save()

    def start(self):
        self._running = True
        self._thread  = threading.Thread(
            target=self._loop, daemon=True)
        self._thread.start()
        print("[SCHEDULER] Started")

    def stop(self):
        self._running = False

    def _loop(self):
        while self._running:
            with self._lock:
                for task in self._tasks:
                    if task.is_due():
                        print(f"[SCHEDULER] Running: {task.name}")
                        threading.Thread(
                            target=self._run_task,
                            args=(task,), daemon=True
                        ).start()
                        task.mark_ran()
                        self._save()
            time.sleep(30)  # Check every 30 seconds

    def _run_task(self, task: ScheduledTask):
        try:
            self._execute(f"[SCHEDULED: {task.name}] {task.command}")
        except Exception as e:
            print(f"[SCHEDULER] Task error: {e}")

    def add_task(self, name: str, command: str,
                 schedule: str) -> ScheduledTask:
        task = ScheduledTask(name, command, schedule)
        with self._lock:
            self._tasks.append(task)
        self._save()
        return task

    def remove_task(self, name: str):
        with self._lock:
            self._tasks = [t for t in self._tasks
                          if t.name != name]
        self._save()

    def toggle_task(self, name: str):
        with self._lock:
            for t in self._tasks:
                if t.name == name:
                    t.enabled = not t.enabled
                    break
        self._save()

    def get_tasks(self) -> List[ScheduledTask]:
        with self._lock:
            return list(self._tasks)

    def _save(self):
        try:
            data = [t.to_dict() for t in self._tasks]
            with open(self._file,"w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"[SCHEDULER] Save error: {e}")

    def _load(self):
        try:
            if self._file.exists():
                with open(self._file) as f:
                    data = json.load(f)
                self._tasks = [ScheduledTask.from_dict(d)
                              for d in data]
                print(f"[SCHEDULER] Loaded {len(self._tasks)} tasks")
        except Exception:
            self._tasks = []
