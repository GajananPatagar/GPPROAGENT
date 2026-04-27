"""
GP PRO AGENT - Predictive Maintenance AI
Analyzes patterns to predict equipment failures
before they happen. Saves downtime and money.
"""
import json, time, math, threading
from pathlib import Path
from datetime import datetime, timedelta
from collections import deque
from typing import Dict, List, Optional

class EquipmentHealth:
    def __init__(self, equipment_id: str, name: str):
        self.id          = equipment_id
        self.name        = name
        self.health_score = 100.0
        self.readings    = deque(maxlen=1440)  # 24h at 1/min
        self.anomalies   = []
        self.predictions = []
        self.last_maintained = None
        self.failure_prob    = 0.0
        self.estimated_failure_days = None

    def add_reading(self, value: float, tag: str = ""):
        self.readings.append({
            "value": value,
            "tag":   tag,
            "time":  datetime.now().isoformat(),
        })

    def to_dict(self):
        return {
            "id":            self.id,
            "name":          self.name,
            "health_score":  round(self.health_score, 1),
            "failure_prob":  round(self.failure_prob * 100, 1),
            "est_failure":   self.estimated_failure_days,
            "anomalies":     len(self.anomalies),
            "reading_count": len(self.readings),
        }


class PredictiveMaintenanceAI:
    """
    Monitors equipment health, detects anomalies,
    predicts when maintenance is needed BEFORE failure.
    """
    def __init__(self, brain_root: str,
                 notify_callback=None):
        self._path      = Path(brain_root) / "predictive_maint"
        self._path.mkdir(parents=True, exist_ok=True)
        self._notify    = notify_callback or print
        self._equipment: Dict[str, EquipmentHealth] = {}
        self._running   = False
        self._thresholds = {
            "vibration_high":    5.0,
            "temp_high":         85.0,
            "current_high":      110.0,  # % of rated
            "speed_deviation":   5.0,    # % deviation
        }
        self._load()
        self._add_defaults()

    def _add_defaults(self):
        defaults = [
            ("MOTOR_001",  "Main Drive Motor"),
            ("PUMP_001",   "Hydraulic Pump"),
            ("CONV_001",   "Conveyor Belt Drive"),
            ("COMP_001",   "Air Compressor"),
        ]
        for eq_id, name in defaults:
            if eq_id not in self._equipment:
                self._equipment[eq_id] = EquipmentHealth(eq_id, name)
        self._save()

    def start_monitoring(self):
        self._running = True
        threading.Thread(target=self._monitor_loop,
                        daemon=True).start()
        print("[PRED-MAINT] Monitoring started")

    def stop_monitoring(self):
        self._running = False

    def _monitor_loop(self):
        """Continuous monitoring and prediction loop."""
        while self._running:
            try:
                for eq_id, eq in self._equipment.items():
                    # Simulate sensor readings
                    reading = self._simulate_reading(eq)
                    eq.add_reading(reading)
                    # Analyze for anomalies
                    anomaly = self._detect_anomaly(eq, reading)
                    if anomaly:
                        eq.anomalies.append(anomaly)
                        self._notify(
                            f"[PRED-MAINT] Anomaly on {eq.name}:\n"
                            f"{anomaly['description']}\n"
                            f"Severity: {anomaly['severity']}")
                    # Update health score
                    self._update_health(eq)
                    # Predict failure
                    self._predict_failure(eq)
                self._save()
            except Exception as e:
                print(f"[PRED-MAINT] Monitor error: {e}")
            time.sleep(60)  # Check every minute

    def _simulate_reading(self, eq: EquipmentHealth) -> float:
        """Simulate realistic sensor data with degradation."""
        import random
        base_values = {
            "MOTOR_001": 1450.0,  # RPM
            "PUMP_001":  4.5,     # Bar
            "CONV_001":  1.2,     # m/s
            "COMP_001":  8.0,     # Bar
        }
        base  = base_values.get(eq.id, 50.0)
        noise = random.gauss(0, base * 0.01)
        degradation = max(0, (100 - eq.health_score) / 100 * base * 0.1)
        return round(base + noise + degradation, 3)

    def _detect_anomaly(self, eq: EquipmentHealth,
                        reading: float) -> Optional[dict]:
        """Detect if reading is anomalous."""
        if len(eq.readings) < 10:
            return None
        readings = [r["value"] for r in list(eq.readings)[-60:]]
        mean  = sum(readings) / len(readings)
        variance = sum((x - mean)**2 for x in readings) / len(readings)
        std   = math.sqrt(variance) if variance > 0 else 0.001
        z_score = abs(reading - mean) / std
        if z_score > 3.0:
            severity = "CRITICAL" if z_score > 5 else "WARNING"
            return {
                "time":        datetime.now().isoformat(),
                "value":       reading,
                "expected":    round(mean, 3),
                "z_score":     round(z_score, 2),
                "severity":    severity,
                "description": (f"Value {reading:.2f} is {z_score:.1f} "
                               f"std deviations from normal {mean:.2f}"),
            }
        return None

    def _update_health(self, eq: EquipmentHealth):
        """Update equipment health score."""
        recent_anomalies = [
            a for a in eq.anomalies
            if (datetime.now() -
                datetime.fromisoformat(a["time"])).days < 7
        ]
        base_health = 100.0
        base_health -= len(recent_anomalies) * 3.0
        if len(eq.readings) > 100:
            readings = [r["value"] for r in list(eq.readings)[-100:]]
            trend    = self._calculate_trend(readings)
            if trend > 0.5:  # Increasing trend (bad for most equipment)
                base_health -= trend * 5
        eq.health_score = max(0, min(100, base_health))

    def _calculate_trend(self, values: List[float]) -> float:
        """Calculate trend slope using linear regression."""
        n  = len(values)
        if n < 2:
            return 0.0
        x_mean = (n - 1) / 2
        y_mean = sum(values) / n
        numerator   = sum((i - x_mean) * (v - y_mean)
                         for i, v in enumerate(values))
        denominator = sum((i - x_mean)**2 for i in range(n))
        if denominator == 0:
            return 0.0
        return numerator / denominator

    def _predict_failure(self, eq: EquipmentHealth):
        """Predict when equipment will fail."""
        if eq.health_score > 80:
            eq.failure_prob = (100 - eq.health_score) / 1000
            eq.estimated_failure_days = None
        elif eq.health_score > 50:
            eq.failure_prob = (100 - eq.health_score) / 100
            eq.estimated_failure_days = int(eq.health_score * 2)
        else:
            eq.failure_prob = 1 - (eq.health_score / 100)
            eq.estimated_failure_days = max(1, int(eq.health_score / 5))
            if eq.health_score < 20:
                self._notify(
                    f"[PRED-MAINT] CRITICAL: {eq.name}\n"
                    f"Predicted failure in {eq.estimated_failure_days} days!\n"
                    f"Health: {eq.health_score:.0f}%\n"
                    f"Schedule maintenance IMMEDIATELY")

    def add_equipment(self, eq_id: str, name: str) -> EquipmentHealth:
        eq = EquipmentHealth(eq_id, name)
        self._equipment[eq_id] = eq
        self._save()
        return eq

    def add_real_reading(self, eq_id: str,
                         value: float, tag: str = ""):
        """Add real sensor reading from PLC."""
        if eq_id in self._equipment:
            self._equipment[eq_id].add_reading(value, tag)
            anomaly = self._detect_anomaly(
                self._equipment[eq_id], value)
            if anomaly:
                self._equipment[eq_id].anomalies.append(anomaly)
            self._update_health(self._equipment[eq_id])
            self._predict_failure(self._equipment[eq_id])

    def get_health_report(self) -> List[dict]:
        return [eq.to_dict() for eq in self._equipment.values()]

    def get_maintenance_schedule(self) -> List[dict]:
        """Get recommended maintenance schedule."""
        schedule = []
        for eq in self._equipment.values():
            if eq.health_score < 80:
                urgency = ("IMMEDIATE" if eq.health_score < 30
                          else "SOON" if eq.health_score < 60
                          else "PLANNED")
                schedule.append({
                    "equipment":    eq.name,
                    "health":       eq.health_score,
                    "urgency":      urgency,
                    "days_until":   eq.estimated_failure_days,
                    "anomalies":    len(eq.anomalies),
                })
        return sorted(schedule, key=lambda x: x["health"])

    def get_equipment(self, eq_id: str) -> Optional[EquipmentHealth]:
        return self._equipment.get(eq_id)

    def _save(self):
        try:
            data = {}
            for eq_id, eq in self._equipment.items():
                data[eq_id] = {
                    "id":           eq.id,
                    "name":         eq.name,
                    "health_score": eq.health_score,
                    "anomalies":    eq.anomalies[-20:],
                    "failure_prob": eq.failure_prob,
                    "est_failure":  eq.estimated_failure_days,
                }
            with open(self._path/"equipment.json","w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"[PRED-MAINT] Save error: {e}")

    def _load(self):
        try:
            path = self._path / "equipment.json"
            if path.exists():
                with open(path) as f:
                    data = json.load(f)
                for eq_id, d in data.items():
                    eq = EquipmentHealth(d["id"], d["name"])
                    eq.health_score     = d.get("health_score", 100)
                    eq.anomalies        = d.get("anomalies", [])
                    eq.failure_prob     = d.get("failure_prob", 0)
                    eq.estimated_failure_days = d.get("est_failure")
                    self._equipment[eq_id] = eq
        except Exception:
            self._equipment = {}
