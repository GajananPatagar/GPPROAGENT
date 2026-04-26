"""
GP PRO AGENT — Personal Learning Memory
Remembers everything. Gets smarter every use.
Saves to C:\GPProAgent\memory\
"""
import json, time, hashlib, threading
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

class MemoryDB:
    def __init__(self, brain_root):
        self._path    = Path(brain_root) / "memory"
        self._path.mkdir(parents=True, exist_ok=True)
        self._db_file = self._path / "memory.json"
        self._lock    = threading.Lock()
        self._mem: List[Dict] = []
        self._load()
        print(f"[MEMORY] Loaded {len(self._mem)} memories")

    def remember(self, query: str, answer: str,
                 brain: str, success: bool=True):
        """Store a query-answer pair."""
        entry = {
            "id":       hashlib.md5(f"{query}{time.time()}".encode()).hexdigest()[:8],
            "query":    query,
            "answer":   answer,
            "brain":    brain,
            "success":  success,
            "time":     datetime.now().isoformat(),
            "uses":     1,
        }
        with self._lock:
            # Check for duplicate
            for existing in self._mem:
                if self._similarity(existing["query"], query) > 0.85:
                    existing["uses"] += 1
                    existing["answer"] = answer
                    self._save()
                    return
            self._mem.append(entry)
            # Keep last 10000 memories
            if len(self._mem) > 10000:
                self._mem = self._mem[-10000:]
        self._save()

    def recall(self, query: str,
               threshold: float=0.75) -> Optional[Dict]:
        """Find best matching memory for a query."""
        best_score  = 0
        best_memory = None
        q_words     = set(query.lower().split())
        with self._lock:
            for mem in self._mem:
                if not mem.get("success", True):
                    continue
                score = self._similarity(mem["query"], query)
                if score > best_score and score >= threshold:
                    best_score  = score
                    best_memory = mem
        return best_memory

    def get_recent(self, n: int=10) -> List[Dict]:
        with self._lock:
            return list(reversed(self._mem[-n:]))

    def get_stats(self) -> Dict:
        with self._lock:
            total   = len(self._mem)
            brains  = {}
            for m in self._mem:
                b = m.get("brain","?")
                brains[b] = brains.get(b, 0) + 1
            top = sorted(brains.items(), key=lambda x:x[1], reverse=True)[:5]
        return {
            "total":     total,
            "top_brains": top,
            "memory_path": str(self._db_file),
        }

    def _similarity(self, a: str, b: str) -> float:
        """Simple word overlap similarity."""
        wa = set(a.lower().split())
        wb = set(b.lower().split())
        if not wa or not wb:
            return 0.0
        intersection = wa & wb
        union        = wa | wb
        return len(intersection) / len(union)

    def _save(self):
        try:
            with open(self._db_file, "w", encoding="utf-8") as f:
                json.dump(self._mem, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[MEMORY] Save error: {e}")

    def _load(self):
        try:
            if self._db_file.exists():
                with open(self._db_file, encoding="utf-8") as f:
                    self._mem = json.load(f)
        except Exception:
            self._mem = []
