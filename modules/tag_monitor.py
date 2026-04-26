"""
GP PRO AGENT — PLC Tag Monitor
Live monitoring of PLC tags with real-time dashboard.
Supports: Modbus TCP, simulated tags for testing.
"""
import tkinter as tk
from tkinter import ttk
import threading, time, json
from pathlib import Path
from datetime import datetime
from collections import deque

class TagValue:
    def __init__(self, name, address, data_type="INT", unit=""):
        self.name      = name
        self.address   = address
        self.data_type = data_type
        self.unit      = unit
        self.value     = None
        self.prev      = None
        self.history   = deque(maxlen=60)
        self.alarm_hi  = None
        self.alarm_lo  = None
        self.in_alarm  = False
        self.last_update = None

    def update(self, value):
        self.prev  = self.value
        self.value = value
        self.history.append((datetime.now(), value))
        self.last_update = datetime.now()
        if self.alarm_hi and value > self.alarm_hi:
            self.in_alarm = True
        elif self.alarm_lo and value < self.alarm_lo:
            self.in_alarm = True
        else:
            self.in_alarm = False

    @property
    def changed(self):
        return self.value != self.prev

    def to_dict(self):
        return {
            "name":    self.name,
            "address": self.address,
            "value":   self.value,
            "unit":    self.unit,
            "alarm":   self.in_alarm,
            "updated": self.last_update.isoformat() if self.last_update else None,
        }


class TagMonitor:
    def __init__(self, brain_root, colors, fonts):
        self.C        = colors
        self.F        = fonts
        self._path    = Path(brain_root) / "tag_monitor"
        self._path.mkdir(parents=True, exist_ok=True)
        self._config  = self._path / "tags.json"
        self._tags    = {}
        self._running = False
        self._client  = None
        self._win     = None
        self._sim     = True  # Simulation mode until real PLC connected
        self._load_tags()

    def _load_tags(self):
        default_tags = [
            TagValue("Motor_Speed",   0, "REAL", "RPM"),
            TagValue("Temperature",   2, "REAL", "°C"),
            TagValue("Pressure",      4, "REAL", "Bar"),
            TagValue("Flow_Rate",     6, "REAL", "L/min"),
            TagValue("Motor_Run",     8, "BOOL", ""),
            TagValue("Fault_Status",  9, "BOOL", ""),
            TagValue("Counter_1",    10, "DINT", ""),
            TagValue("Setpoint",     12, "REAL", "°C"),
        ]
        for t in default_tags:
            self._tags[t.name] = t
        try:
            if self._config.exists():
                with open(self._config) as f:
                    saved = json.load(f)
                for item in saved:
                    t = TagValue(item["name"], item["address"],
                               item.get("data_type","INT"),
                               item.get("unit",""))
                    t.alarm_hi = item.get("alarm_hi")
                    t.alarm_lo = item.get("alarm_lo")
                    self._tags[t.name] = t
        except: pass

    def save_tags(self):
        data = [{
            "name":      t.name,
            "address":   t.address,
            "data_type": t.data_type,
            "unit":      t.unit,
            "alarm_hi":  t.alarm_hi,
            "alarm_lo":  t.alarm_lo,
        } for t in self._tags.values()]
        with open(self._config,"w") as f:
            json.dump(data, f, indent=2)

    def connect_modbus(self, ip, port=502):
        try:
            from pymodbus.client import ModbusTcpClient
            self._client = ModbusTcpClient(ip, port=port)
            if self._client.connect():
                self._sim = False
                return True, f"Connected to {ip}:{port}"
            return False, f"Cannot connect to {ip}"
        except ImportError:
            return False, "Install pymodbus: pip install pymodbus"
        except Exception as e:
            return False, str(e)

    def _read_tags(self):
        """Read all tags from PLC or simulate."""
        import random, math
        t_now = time.time()
        for tag in self._tags.values():
            if self._sim:
                # Realistic simulation
                if tag.data_type == "BOOL":
                    if tag.name == "Motor_Run":
                        val = random.random() > 0.2
                    else:
                        val = random.random() > 0.95
                elif tag.name == "Motor_Speed":
                    val = round(1450 + 50*math.sin(t_now/10) + random.gauss(0,5), 1)
                elif tag.name == "Temperature":
                    val = round(65 + 10*math.sin(t_now/20) + random.gauss(0,0.5), 2)
                elif tag.name == "Pressure":
                    val = round(4.5 + 0.5*math.sin(t_now/15) + random.gauss(0,0.05), 3)
                elif tag.name == "Flow_Rate":
                    val = round(85 + 15*math.sin(t_now/8) + random.gauss(0,1), 1)
                elif tag.name == "Counter_1":
                    val = int(t_now) % 10000
                elif tag.name == "Setpoint":
                    val = 70.0
                else:
                    val = round(random.uniform(0,100), 2)
                tag.update(val)
            else:
                try:
                    result = self._client.read_holding_registers(
                        tag.address, 2, unit=1)
                    if not result.isError():
                        tag.update(result.registers[0])
                except: pass

    def start_monitoring(self, interval=1.0):
        self._running = True
        threading.Thread(target=self._monitor_loop,
                        args=(interval,), daemon=True).start()

    def stop_monitoring(self):
        self._running = False

    def _monitor_loop(self, interval):
        while self._running:
            self._read_tags()
            time.sleep(interval)

    def open_window(self, root):
        if self._win and self._win.winfo_exists():
            self._win.lift()
            return
        self._win = tk.Toplevel(root)
        self._win.title("GP PRO AGENT — PLC Tag Monitor")
        self._win.geometry("900x600")
        self._win.configure(bg=self.C["bg"])
        self._win.resizable(True, True)
        self._build_window()
        self.start_monitoring()
        self._win.protocol("WM_DELETE_WINDOW",
            lambda: [self.stop_monitoring(), self._win.destroy()])

    def _build_window(self):
        # Header
        hdr = tk.Frame(self._win, bg=self.C["panel"],
                      highlightbackground=self.C["border"],
                      highlightthickness=1)
        hdr.pack(fill="x", padx=8, pady=(8,4))
        tk.Label(hdr, text=">> LIVE PLC TAG MONITOR",
                bg=self.C["panel"], fg=self.C["cyan"],
                font=self.F["head"]).pack(side="left", padx=12, pady=8)
        self._sim_lbl = tk.Label(hdr,
            text="● SIMULATION MODE" if self._sim else "● LIVE PLC",
            bg=self.C["panel"],
            fg=self.C["warning"] if self._sim else self.C["green"],
            font=self.F["small"])
        self._sim_lbl.pack(side="left", padx=8)

        # Connect bar
        cf = tk.Frame(hdr, bg=self.C["panel"])
        cf.pack(side="right", padx=8)
        self._ip_entry = tk.Entry(cf, bg=self.C["input_bg"],
                                   fg=self.C["white"],
                                   font=self.F["small"], width=14)
        self._ip_entry.insert(0, "192.168.1.1")
        self._ip_entry.pack(side="left", padx=4)
        tk.Button(cf, text="Connect PLC",
                 bg=self.C["cyan"], fg=self.C["bg"],
                 font=self.F["small"], relief="flat",
                 command=self._connect_plc).pack(side="left")

        # Tag table
        cols = ("Name","Value","Unit","Status","Address","Updated")
        self._tree = ttk.Treeview(self._win, columns=cols,
                                   show="headings", height=15)
        widths = [150, 100, 60, 80, 70, 120]
        for col, w in zip(cols, widths):
            self._tree.heading(col, text=col)
            self._tree.column(col, width=w, anchor="center")

        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview",
            background=self.C["input_bg"],
            foreground=self.C["white"],
            fieldbackground=self.C["input_bg"],
            rowheight=28, font=("Consolas",9))
        style.configure("Treeview.Heading",
            background=self.C["panel"],
            foreground=self.C["cyan"],
            font=("Consolas",9,"bold"))
        style.map("Treeview",
            background=[("selected",self.C["button"])])

        sb = ttk.Scrollbar(self._win, orient="vertical",
                          command=self._tree.yview)
        self._tree.configure(yscrollcommand=sb.set)
        self._tree.pack(side="left", fill="both",
                       expand=True, padx=(8,0), pady=4)
        sb.pack(side="right", fill="y", padx=(0,8), pady=4)

        # Tag colors
        self._tree.tag_configure("alarm",  foreground=self.C["error"])
        self._tree.tag_configure("normal", foreground=self.C["green"])
        self._tree.tag_configure("bool_on",foreground=self.C["cyan"])
        self._tree.tag_configure("bool_off",foreground=self.C["dim"])

        # Bottom bar
        bot = tk.Frame(self._win, bg=self.C["panel"])
        bot.pack(fill="x", padx=8, pady=(0,8))
        self._alarm_lbl = tk.Label(bot, text="No alarms",
                                    bg=self.C["panel"],
                                    fg=self.C["green"],
                                    font=self.F["small"])
        self._alarm_lbl.pack(side="left", padx=12)
        tk.Button(bot, text="Add Tag",
                 bg=self.C["button"], fg=self.C["white"],
                 font=self.F["small"], relief="flat",
                 command=self._add_tag_dialog).pack(side="right", padx=8)
        tk.Button(bot, text="Export CSV",
                 bg=self.C["button"], fg=self.C["white"],
                 font=self.F["small"], relief="flat",
                 command=self._export_csv).pack(side="right", padx=4)

        # Start UI refresh
        self._refresh_table()

    def _refresh_table(self):
        if not self._win or not self._win.winfo_exists():
            return
        # Update all rows
        for item in self._tree.get_children():
            self._tree.delete(item)
        alarms = 0
        for tag in self._tags.values():
            if tag.value is None:
                continue
            if tag.data_type == "BOOL":
                val_str = "ON" if tag.value else "OFF"
                tag_type = "bool_on" if tag.value else "bool_off"
            else:
                val_str = str(tag.value)
                tag_type = "alarm" if tag.in_alarm else "normal"
            if tag.in_alarm:
                alarms += 1
            upd = (tag.last_update.strftime("%H:%M:%S")
                   if tag.last_update else "--")
            self._tree.insert("", "end",
                values=(tag.name, val_str, tag.unit,
                       "!! ALARM" if tag.in_alarm else "OK",
                       tag.address, upd),
                tags=(tag_type,))
        if alarms:
            self._alarm_lbl.config(
                text=f"!! {alarms} ALARM(S) ACTIVE",
                fg=self.C["error"])
        else:
            self._alarm_lbl.config(text="OK No alarms",
                                   fg=self.C["green"])
        self._win.after(1000, self._refresh_table)

    def _connect_plc(self):
        ip = self._ip_entry.get().strip()
        ok, msg = self.connect_modbus(ip)
        if ok:
            self._sim_lbl.config(text="● LIVE PLC",
                                fg=self.C["green"])
        else:
            import tkinter.messagebox as mb
            mb.showwarning("Connection Failed", msg)

    def _add_tag_dialog(self):
        win = tk.Toplevel(self._win)
        win.title("Add Tag")
        win.geometry("350x250")
        win.configure(bg=self.C["bg"])
        fields = [("Tag Name","Motor_Speed_2"),
                  ("Address","14"),
                  ("Data Type","REAL"),
                  ("Unit","RPM"),
                  ("Alarm High",""),
                  ("Alarm Low","")]
        entries = {}
        for lbl, default in fields:
            rf = tk.Frame(win, bg=self.C["bg"])
            rf.pack(fill="x", padx=16, pady=4)
            tk.Label(rf, text=lbl, bg=self.C["bg"],
                    fg=self.C["dim"],
                    font=self.F["small"],
                    width=12, anchor="w").pack(side="left")
            e = tk.Entry(rf, bg=self.C["input_bg"],
                        fg=self.C["white"],
                        font=self.F["small"])
            e.insert(0, default)
            e.pack(side="left", fill="x", expand=True)
            entries[lbl] = e
        def add():
            t = TagValue(
                entries["Tag Name"].get(),
                int(entries["Address"].get() or 0),
                entries["Data Type"].get() or "INT",
                entries["Unit"].get()
            )
            hi = entries["Alarm High"].get()
            lo = entries["Alarm Low"].get()
            if hi: t.alarm_hi = float(hi)
            if lo: t.alarm_lo = float(lo)
            self._tags[t.name] = t
            self.save_tags()
            win.destroy()
        tk.Button(win, text="Add Tag",
                 bg=self.C["cyan"], fg=self.C["bg"],
                 font=self.F["head"], relief="flat",
                 command=add).pack(pady=12)

    def _export_csv(self):
        import csv
        path = self._path / f"tags_{int(time.time())}.csv"
        with open(path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["Name","Value","Unit","Alarm","Address","Updated"])
            for t in self._tags.values():
                d = t.to_dict()
                w.writerow([d["name"],d["value"],d["unit"],
                           d["alarm"],d["address"],d["updated"]])
        import tkinter.messagebox as mb
        mb.showinfo("Exported", f"Saved to:\n{path}")

    def get_all_values(self):
        return {n: t.to_dict() for n,t in self._tags.items()}
