"""
GP PRO AGENT - Digital Twin Simulator
Simulates PLC programs and equipment without real hardware.
Test programs safely before going live.
"""
import json, time, math, threading, random
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable

class PLCSimulator:
    """Simulates a PLC execution environment."""
    def __init__(self, name: str = "SimPLC"):
        self.name     = name
        self._tags    = {}
        self._timers  = {}
        self._counters = {}
        self._running = False
        self._scan_time = 0.010  # 10ms scan
        self._scan_count = 0
        self._callbacks: List[Callable] = []
        self._program_code = ""

    def set_tag(self, name: str, value: Any,
                data_type: str = "BOOL"):
        self._tags[name] = {
            "value":     value,
            "type":      data_type,
            "timestamp": time.time(),
        }

    def get_tag(self, name: str) -> Any:
        tag = self._tags.get(name)
        return tag["value"] if tag else None

    def get_all_tags(self) -> dict:
        return {k: v["value"] for k, v in self._tags.items()}

    def load_program(self, st_code: str):
        self._program_code = st_code
        self._init_tags_from_code(st_code)

    def _init_tags_from_code(self, code: str):
        """Auto-detect tags from ST code."""
        import re
        # Find variable declarations
        for m in re.finditer(
                r'(\w+)\s*:=', code):
            tag = m.group(1)
            if tag not in self._tags:
                # Guess type from name
                if tag.startswith(("x","b","bool")):
                    self.set_tag(tag, False, "BOOL")
                elif tag.startswith(("r","f","real")):
                    self.set_tag(tag, 0.0, "REAL")
                elif tag.startswith(("i","n","int")):
                    self.set_tag(tag, 0, "INT")
                else:
                    self.set_tag(tag, False, "BOOL")

    def start(self):
        self._running = True
        threading.Thread(target=self._scan_loop,
                        daemon=True).start()

    def stop(self):
        self._running = False

    def _scan_loop(self):
        while self._running:
            scan_start = time.time()
            self._execute_scan()
            self._scan_count += 1
            elapsed = time.time() - scan_start
            sleep_time = max(0, self._scan_time - elapsed)
            time.sleep(sleep_time)
            for cb in self._callbacks:
                try:
                    cb(self.get_all_tags())
                except Exception:
                    pass

    def _execute_scan(self):
        """Execute one PLC scan - simulate logic."""
        tags = self._tags
        # Execute timer logic
        for name, timer in self._timers.items():
            if timer["in"] and not timer["done"]:
                elapsed = time.time() - timer["start_time"]
                timer["acc"] = elapsed
                if elapsed >= timer["preset"]:
                    timer["done"] = True
                    timer["q"]    = True
        # Execute simple ST simulation
        self._simulate_program()

    def _simulate_program(self):
        """Basic ST program simulation."""
        code = self._program_code.lower()
        # Simple pattern execution
        if "motor" in code or "run" in code:
            start = self.get_tag("xStartPB") or False
            stop  = self.get_tag("xStopPB")
            fault = self.get_tag("xMotorFault")
            if start and not stop and not fault:
                self.set_tag("xMotorRun", True)
            elif stop or fault:
                self.set_tag("xMotorRun", False)
            run = self.get_tag("xMotorRun") or False
            self.set_tag("xRunLamp", run)

    def add_ton_timer(self, name: str, preset_s: float):
        self._timers[name] = {
            "preset":     preset_s,
            "acc":        0,
            "in":         False,
            "done":       False,
            "q":          False,
            "start_time": 0,
        }

    def set_timer_in(self, name: str, value: bool):
        if name in self._timers:
            timer = self._timers[name]
            if value and not timer["in"]:
                timer["start_time"] = time.time()
                timer["done"]       = False
                timer["q"]          = False
            timer["in"] = value

    def on_scan(self, callback: Callable):
        self._callbacks.append(callback)

    def get_status(self) -> dict:
        return {
            "name":       self.name,
            "running":    self._running,
            "scan_count": self._scan_count,
            "scan_time":  f"{self._scan_time*1000:.0f}ms",
            "tag_count":  len(self._tags),
        }


class DigitalTwin:
    """
    Complete digital twin - simulates the entire system.
    Models equipment, PLC, process, and environment.
    """
    def __init__(self, brain_root: str,
                 notify_callback=None):
        self._path    = Path(brain_root) / "digital_twin"
        self._path.mkdir(parents=True, exist_ok=True)
        self._notify  = notify_callback or print
        self._plc     = PLCSimulator("GP-PRO-SIM-PLC")
        self._process = {}
        self._running = False
        self._history = []
        self._scenarios = {}
        self._load_scenarios()

        # Initialize default process simulation
        self._init_process()

    def _init_process(self):
        """Initialize process simulation tags."""
        defaults = {
            "xStartPB":     (False, "BOOL"),
            "xStopPB":      (False, "BOOL"),
            "xEStop":       (True,  "BOOL"),
            "xMotorFault":  (False, "BOOL"),
            "xMotorRun":    (False, "BOOL"),
            "xRunLamp":     (False, "BOOL"),
            "rTemperature": (25.0,  "REAL"),
            "rPressure":    (0.0,   "REAL"),
            "rFlow":        (0.0,   "REAL"),
            "iCounter":     (0,     "INT"),
        }
        for tag, (val, dtype) in defaults.items():
            self._plc.set_tag(tag, val, dtype)

    def _load_scenarios(self):
        """Load test scenarios."""
        self._scenarios = {
            "normal_start": {
                "name":   "Normal Motor Start",
                "steps":  [
                    {"tag": "xEStop",   "value": True,  "delay": 0.5},
                    {"tag": "xStartPB", "value": True,  "delay": 0.5},
                    {"tag": "xStartPB", "value": False, "delay": 0.5},
                ],
                "expected": {"xMotorRun": True},
            },
            "estop_test": {
                "name":   "E-Stop Test",
                "steps":  [
                    {"tag": "xStartPB", "value": True,  "delay": 0.5},
                    {"tag": "xStartPB", "value": False, "delay": 1.0},
                    {"tag": "xEStop",   "value": False, "delay": 0.5},
                ],
                "expected": {"xMotorRun": False},
            },
            "fault_test": {
                "name":   "Motor Fault Simulation",
                "steps":  [
                    {"tag": "xStartPB",    "value": True,  "delay": 0.5},
                    {"tag": "xStartPB",    "value": False, "delay": 1.0},
                    {"tag": "xMotorFault", "value": True,  "delay": 0.5},
                ],
                "expected": {"xMotorRun": False},
            },
        }

    def start(self):
        """Start digital twin simulation."""
        self._running = True
        self._plc.start()
        threading.Thread(target=self._process_sim_loop,
                        daemon=True).start()
        print("[DIGITAL-TWIN] Simulation started")

    def stop(self):
        self._running = False
        self._plc.stop()

    def _process_sim_loop(self):
        """Simulate physical process."""
        t = 0
        while self._running:
            t += 0.1
            motor_run = self._plc.get_tag("xMotorRun") or False
            if motor_run:
                temp = 25 + 40 * (1 - math.exp(-t/60)) + random.gauss(0, 0.5)
                pres = 4.5 + 0.3 * math.sin(t/5) + random.gauss(0, 0.05)
                flow = 85 + 10 * math.sin(t/8) + random.gauss(0, 1)
            else:
                temp = max(25, self._plc.get_tag("rTemperature") or 25 - 0.5)
                pres = max(0,  self._plc.get_tag("rPressure") or 0 - 0.1)
                flow = 0.0
            self._plc.set_tag("rTemperature", round(temp, 2))
            self._plc.set_tag("rPressure",    round(pres, 3))
            self._plc.set_tag("rFlow",        round(flow, 1))
            time.sleep(0.1)

    def load_plc_program(self, st_code: str):
        """Load PLC program into simulator."""
        self._plc.load_program(st_code)
        self._notify(f"[DIGITAL-TWIN] Program loaded into simulator")

    def run_scenario(self, scenario_id: str) -> dict:
        """Run a predefined test scenario."""
        scenario = self._scenarios.get(scenario_id)
        if not scenario:
            return {"error": f"Scenario '{scenario_id}' not found"}

        self._notify(
            f"[DIGITAL-TWIN] Running: {scenario['name']}")
        results = {"scenario": scenario["name"], "steps": [], "passed": True}

        for step in scenario["steps"]:
            self._plc.set_tag(step["tag"], step["value"])
            results["steps"].append({
                "tag":   step["tag"],
                "value": step["value"],
            })
            time.sleep(step.get("delay", 0.5))

        # Check expected results
        expected = scenario.get("expected", {})
        for tag, exp_val in expected.items():
            actual = self._plc.get_tag(tag)
            passed = actual == exp_val
            results["steps"].append({
                "check":  f"{tag} = {exp_val}",
                "actual": actual,
                "passed": passed,
            })
            if not passed:
                results["passed"] = False

        status = "PASSED" if results["passed"] else "FAILED"
        self._notify(
            f"[DIGITAL-TWIN] Scenario {status}: {scenario['name']}")
        self._history.append({
            "time":     datetime.now().isoformat(),
            "scenario": scenario_id,
            "passed":   results["passed"],
        })
        return results

    def set_input(self, tag: str, value: Any):
        """Set a simulated input value."""
        self._plc.set_tag(tag, value)

    def get_all_values(self) -> dict:
        return self._plc.get_all_tags()

    def get_status(self) -> dict:
        return {
            "plc_status":   self._plc.get_status(),
            "process_tags": self._plc.get_all_tags(),
            "scenarios":    list(self._scenarios.keys()),
            "history":      self._history[-10:],
        }

    def add_scenario(self, name: str, steps: list,
                     expected: dict):
        sc_id = name.lower().replace(" ", "_")
        self._scenarios[sc_id] = {
            "name":     name,
            "steps":    steps,
            "expected": expected,
        }
        return sc_id

    @property
    def is_running(self):
        return self._running
