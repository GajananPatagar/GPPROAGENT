from typing import Optional, List, Dict, Any, Callable, Generator, Set, Tuple
"""
GP PRO AGENT — Smart Alert System
Monitors screen continuously, detects events, sends alerts.
Watches for: errors, alarms, software crashes, specific text.
"""
import tkinter as tk
import threading, time, json, re
from pathlib import Path
from datetime import datetime
from collections import deque

class Alert:
    def __init__(self, rule_name, message, severity="INFO"):
        self.rule_name = rule_name
        self.message   = message
        self.severity  = severity  # INFO, WARNING, ERROR, CRITICAL
        self.time      = datetime.now()
        self.id        = f"{rule_name}_{int(time.time())}"

    def to_dict(self):
        return {
            "id":        self.id,
            "rule":      self.rule_name,
            "message":   self.message,
            "severity":  self.severity,
            "time":      self.time.isoformat(),
        }

class WatchRule:
    def __init__(self, name, pattern, severity="WARNING",
                 action=None, enabled=True):
        self.name     = name
        self.pattern  = pattern.lower()
        self.severity = severity
        self.action   = action
        self.enabled  = enabled
        self.triggers = 0
        self.last_triggered = None

    def check(self, text: str) -> bool:
        return self.enabled and self.pattern in text.lower()

    def trigger(self):
        self.triggers += 1
        self.last_triggered = datetime.now()

class AlertSystem:
    def __init__(self, brain_root, colors, fonts,
                 notify_callback=None):
        self.C        = colors
        self.F        = fonts
        self._notify  = notify_callback
        self._path    = Path(brain_root) / "alerts"
        self._path.mkdir(parents=True, exist_ok=True)
        self._rules:  list[WatchRule] = []
        self._alerts: deque[Alert] = deque(maxlen=500)
        self._running = False
        self._win     = None
        self._alert_labels = {}
        self._load_rules()
        self._add_defaults()

    def _add_defaults(self):
        if not self._rules:
            defaults = [
                WatchRule("Error Detected",   "error",   "ERROR"),
                WatchRule("Fault Detected",   "fault",   "ERROR"),
                WatchRule("Alarm Active",     "alarm",   "WARNING"),
                WatchRule("PLC Offline",      "offline", "CRITICAL"),
                WatchRule("Exception Found",  "exception","ERROR"),
                WatchRule("Connection Lost",  "connection lost","CRITICAL"),
                WatchRule("Memory Warning",   "out of memory","CRITICAL"),
                WatchRule("Access Denied",    "access denied","WARNING"),
            ]
            self._rules.extend(defaults)
            self._save_rules()

    def start_monitoring(self):
        self._running = True
        threading.Thread(target=self._monitor_loop,
                        daemon=True).start()
        print("[ALERTS] Monitoring started")

    def stop_monitoring(self):
        self._running = False

    def _monitor_loop(self):
        """Continuously monitor screen for alert conditions."""
        while self._running:
            try:
                text = self._get_screen_text()
                if text:
                    self._check_rules(text)
            except Exception as e:
                pass
            time.sleep(3)  # Check every 3 seconds

    def _get_screen_text(self) -> str:
        """Get current screen text."""
        try:
            import pyautogui
            try:
                import pytesseract
                img  = pyautogui.screenshot()
                text = pytesseract.image_to_string(img)
                return text
            except ImportError:
                return ""
        except ImportError:
            return ""
        except Exception:
            return ""

    def _check_rules(self, screen_text: str):
        """Check all rules against screen text."""
        for rule in self._rules:
            if rule.check(screen_text):
                # Avoid duplicate alerts (same rule within 30s)
                if (rule.last_triggered and
                    (datetime.now()-rule.last_triggered).seconds < 30):
                    continue
                rule.trigger()
                alert = Alert(
                    rule.name,
                    f"Detected '{rule.pattern}' on screen",
                    rule.severity
                )
                self._alerts.append(alert)
                self._save_alert(alert)
                if self._notify:
                    self._notify(
                        f"[ALERT] {rule.severity}: {rule.name}\n"
                        f"Detected on screen at {alert.time.strftime('%H:%M:%S')}")
                self._show_popup(alert)

    def _show_popup(self, alert: Alert):
        """Show non-blocking alert popup."""
        colors = {
            "INFO":     "#00e5ff",
            "WARNING":  "#ffaa00",
            "ERROR":    "#ff4444",
            "CRITICAL": "#ff0000",
        }
        color = colors.get(alert.severity, "#ffffff")

        def _show():
            try:
                popup = tk.Toplevel()
                popup.title(f"GP PRO AGENT — {alert.severity}")
                popup.geometry("350x120+10+40")
                popup.configure(bg=self.C["panel"])
                popup.attributes("-topmost", True)
                popup.overrideredirect(True)

                tk.Frame(popup, bg=color, height=3).pack(fill="x")
                tk.Label(popup,
                        text=f"!! {alert.severity}: {alert.rule_name}",
                        bg=self.C["panel"], fg=color,
                        font=self.F["head"]).pack(padx=12, pady=(8,4))
                tk.Label(popup, text=alert.message,
                        bg=self.C["panel"], fg=self.C["white"],
                        font=self.F["small"],
                        wraplength=320).pack(padx=12)
                tk.Label(popup,
                        text=alert.time.strftime("%H:%M:%S"),
                        bg=self.C["panel"], fg=self.C["dim"],
                        font=self.F["small"]).pack(pady=4)
                tk.Button(popup, text="Dismiss",
                         bg=color, fg=self.C["bg"],
                         font=self.F["small"], relief="flat",
                         command=popup.destroy).pack(pady=(0,8))
                # Auto-dismiss after 8 seconds
                popup.after(8000, lambda: popup.destroy()
                           if popup.winfo_exists() else None)
            except Exception:
                pass

        try:
            if tk._default_root:
                tk._default_root.after(0, _show)
        except: pass

    def add_rule(self, name, pattern,
                 severity="WARNING") -> WatchRule:
        rule = WatchRule(name, pattern, severity)
        self._rules.append(rule)
        self._save_rules()
        return rule

    def remove_rule(self, name):
        self._rules = [r for r in self._rules if r.name != name]
        self._save_rules()

    def toggle_rule(self, name):
        for r in self._rules:
            if r.name == name:
                r.enabled = not r.enabled
                break
        self._save_rules()

    def get_recent_alerts(self, n=20) -> list:
        return list(reversed(list(self._alerts)))[:n]

    def open_window(self, root):
        if self._win and self._win.winfo_exists():
            self._win.lift()
            return
        self._win = tk.Toplevel(root)
        self._win.title("GP PRO AGENT — Alert System")
        self._win.geometry("800x550")
        self._win.configure(bg=self.C["bg"])
        self._build_window()

    def _build_window(self):
        tk.Label(self._win, text=">> SMART ALERT SYSTEM",
                bg=self.C["bg"], fg=self.C["cyan"],
                font=self.F["head"]).pack(anchor="w",
                                          padx=16, pady=(12,4))
        mon_status = "● Monitoring Active" if self._running else "○ Not monitoring"
        mon_color  = self.C["green"] if self._running else self.C["error"]
        tk.Label(self._win, text=mon_status,
                bg=self.C["bg"], fg=mon_color,
                font=self.F["small"]).pack(anchor="w", padx=16)
        tk.Frame(self._win, bg=self.C["border"],
                height=1).pack(fill="x", padx=16, pady=8)

        paned = tk.PanedWindow(self._win, orient="horizontal",
                              bg=self.C["bg"])
        paned.pack(fill="both", expand=True, padx=8, pady=4)

        # Left — Watch Rules
        lf = tk.Frame(paned, bg=self.C["panel"])
        paned.add(lf, width=350)
        tk.Label(lf, text=">> WATCH RULES",
                bg=self.C["panel"], fg=self.C["cyan"],
                font=self.F["head"]).pack(anchor="w", padx=8, pady=6)
        self._rules_frame = tk.Frame(lf, bg=self.C["panel"])
        self._rules_frame.pack(fill="both", expand=True, padx=4)
        self._refresh_rules()

        # Add rule
        af = tk.Frame(lf, bg=self.C["panel"])
        af.pack(fill="x", padx=8, pady=8)
        self._new_pattern = tk.Entry(af, bg=self.C["input_bg"],
                                      fg=self.C["white"],
                                      font=self.F["small"],
                                      width=16)
        self._new_pattern.insert(0, "keyword to watch")
        self._new_pattern.pack(side="left", padx=(0,4))
        tk.Button(af, text="Add Rule",
                 bg=self.C["cyan"], fg=self.C["bg"],
                 font=self.F["small"], relief="flat",
                 command=self._add_rule_from_ui).pack(side="left")

        # Right — Recent Alerts
        rf = tk.Frame(paned, bg=self.C["panel"])
        paned.add(rf)
        tk.Label(rf, text=">> RECENT ALERTS",
                bg=self.C["panel"], fg=self.C["cyan"],
                font=self.F["head"]).pack(anchor="w", padx=8, pady=6)
        self._alerts_text = tk.Text(
            rf, bg=self.C["input_bg"], fg=self.C["white"],
            font=self.F["small"], state="disabled",
            borderwidth=0, highlightthickness=0,
            padx=8, pady=8)
        self._alerts_text.pack(fill="both", expand=True, padx=4, pady=4)
        self._alerts_text.tag_config("critical",foreground=self.C["error"])
        self._alerts_text.tag_config("error",   foreground="#ff6644")
        self._alerts_text.tag_config("warning", foreground=self.C["warning"])
        self._alerts_text.tag_config("info",    foreground=self.C["cyan"])
        self._refresh_alerts_text()
        self._win.after(3000, self._auto_refresh)

    def _refresh_rules(self):
        for w in self._rules_frame.winfo_children():
            w.destroy()
        for rule in self._rules:
            rf = tk.Frame(self._rules_frame, bg=self.C["panel"], pady=2)
            rf.pack(fill="x", padx=4, pady=1)
            c = self.C["green"] if rule.enabled else self.C["dim"]
            tk.Label(rf, text="●", bg=self.C["panel"],
                    fg=c, font=self.F["small"]).pack(side="left")
            sev_colors = {"CRITICAL":"#ff0000","ERROR":self.C["error"],
                         "WARNING":self.C["warning"],"INFO":self.C["cyan"]}
            tk.Label(rf,
                    text=f"[{rule.severity[:4]}]",
                    bg=self.C["panel"],
                    fg=sev_colors.get(rule.severity,self.C["white"]),
                    font=self.F["small"],width=6).pack(side="left")
            tk.Label(rf, text=f"'{rule.pattern}'",
                    bg=self.C["panel"], fg=self.C["white"],
                    font=self.F["small"],
                    anchor="w").pack(side="left", fill="x", expand=True)
            tk.Label(rf, text=f"{rule.triggers}x",
                    bg=self.C["panel"], fg=self.C["dim"],
                    font=self.F["small"]).pack(side="right", padx=2)
            tk.Button(rf,
                     text="On" if rule.enabled else "Off",
                     bg=self.C["button"], fg=self.C["white"],
                     font=("Consolas",7), relief="flat", width=3,
                     command=lambda n=rule.name:
                     [self.toggle_rule(n),
                      self._refresh_rules()]).pack(side="right",padx=1)

    def _refresh_alerts_text(self):
        self._alerts_text.config(state="normal")
        self._alerts_text.delete("1.0","end")
        alerts = self.get_recent_alerts()
        if not alerts:
            self._alerts_text.insert("end",
                "No alerts yet.\nMonitoring screen for issues...\n")
        for alert in alerts:
            tag = alert.severity.lower()
            ts  = alert.time.strftime("%H:%M:%S")
            self._alerts_text.insert("end",
                f"[{ts}] {alert.severity}: {alert.rule_name}\n",tag)
            self._alerts_text.insert("end",
                f"  {alert.message}\n\n")
        self._alerts_text.config(state="disabled")
        self._alerts_text.see("end")

    def _auto_refresh(self):
        if self._win and self._win.winfo_exists():
            self._refresh_alerts_text()
            self._win.after(5000, self._auto_refresh)

    def _add_rule_from_ui(self):
        pattern = self._new_pattern.get().strip()
        if pattern and pattern != "keyword to watch":
            self.add_rule(f"Watch: {pattern}", pattern)
            self._refresh_rules()
            self._new_pattern.delete(0,"end")
            self._new_pattern.insert(0,"keyword to watch")

    def _save_alert(self, alert: Alert):
        log_file = self._path / "alert_log.json"
        try:
            existing = []
            if log_file.exists():
                with open(log_file) as f:
                    existing = json.load(f)
            existing.append(alert.to_dict())
            existing = existing[-1000:]  # Keep last 1000
            with open(log_file,"w") as f:
                json.dump(existing, f, indent=2)
        except: pass

    def _save_rules(self):
        rules_file = self._path / "rules.json"
        data = [{
            "name":     r.name,
            "pattern":  r.pattern,
            "severity": r.severity,
            "enabled":  r.enabled,
        } for r in self._rules]
        with open(rules_file,"w") as f:
            json.dump(data, f, indent=2)

    def _load_rules(self):
        rules_file = self._path / "rules.json"
        try:
            if rules_file.exists():
                with open(rules_file) as f:
                    data = json.load(f)
                self._rules = [WatchRule(
                    d["name"],d["pattern"],
                    d.get("severity","WARNING"),
                    enabled=d.get("enabled",True)
                ) for d in data]
        except:
            self._rules = []
