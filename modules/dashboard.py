"""
GP PRO AGENT — Live Dashboard
Real-time charts, RAM graph, brain activity, response times.
"""
import tkinter as tk
from tkinter import ttk
import threading, time, os, collections
from pathlib import Path

class LiveDashboard:
    def __init__(self, parent_root, colors, fonts, settings):
        self._root    = parent_root
        self.C        = colors
        self.F        = fonts
        self.settings = settings
        self._win     = None
        self._running = False

        # Data collections
        self._ram_history    = collections.deque(maxlen=60)
        self._time_history   = collections.deque(maxlen=20)
        self._brain_counts   = {}
        self._query_log      = collections.deque(maxlen=100)
        self._total_queries  = 0
        self._total_time     = 0.0

    def open(self):
        if self._win and self._win.winfo_exists():
            self._win.lift()
            return
        self._win    = tk.Toplevel(self._root)
        self._win.title("GP PRO AGENT — Live Dashboard")
        self._win.geometry("900x650")
        self._win.configure(bg=self.C["bg"])
        self._win.resizable(True, True)
        self._running = True
        self._build()
        threading.Thread(target=self._update_loop,
                        daemon=True).start()
        self._win.protocol("WM_DELETE_WINDOW", self._close)

    def _build(self):
        # Title
        tk.Label(self._win,
                 text=">> GP PRO AGENT — LIVE DASHBOARD",
                 bg=self.C["bg"], fg=self.C["cyan"],
                 font=self.F["title"]).pack(anchor="w", padx=16, pady=(12,4))

        # Top row — stats cards
        top = tk.Frame(self._win, bg=self.C["bg"])
        top.pack(fill="x", padx=16, pady=(0,8))
        self._stat_labels = {}
        stats = [
            ("RAM",     "-- MB",  self.C["green"]),
            ("QUERIES", "0",      self.C["cyan"]),
            ("AVG TIME","--s",    self.C["orange"]),
            ("MODELS",  "0/11",   self.C["purple"]),
            ("STATUS",  "ONLINE", self.C["green"]),
        ]
        for label, val, color in stats:
            card = tk.Frame(top, bg=self.C["panel"],
                           highlightbackground=self.C["border"],
                           highlightthickness=1)
            card.pack(side="left", padx=4, fill="x", expand=True)
            tk.Label(card, text=label, bg=self.C["panel"],
                    fg=self.C["dim"],
                    font=self.F["small"]).pack(pady=(8,2))
            lbl = tk.Label(card, text=val, bg=self.C["panel"],
                          fg=color, font=("Consolas",14,"bold"))
            lbl.pack(pady=(0,8))
            self._stat_labels[label] = lbl

        # Middle row — RAM chart + Brain usage
        mid = tk.Frame(self._win, bg=self.C["bg"])
        mid.pack(fill="both", expand=True, padx=16, pady=4)
        mid.grid_columnconfigure(0, weight=2)
        mid.grid_columnconfigure(1, weight=1)
        mid.grid_rowconfigure(0, weight=1)

        # RAM chart canvas
        ram_f = tk.Frame(mid, bg=self.C["panel"],
                        highlightbackground=self.C["border"],
                        highlightthickness=1)
        ram_f.grid(row=0, column=0, sticky="nsew", padx=(0,4))
        tk.Label(ram_f, text=">> RAM USAGE (60s)",
                bg=self.C["panel"], fg=self.C["cyan"],
                font=self.F["head"]).pack(anchor="w", padx=8, pady=4)
        self._ram_canvas = tk.Canvas(
            ram_f, bg=self.C["input_bg"],
            highlightthickness=0, height=180)
        self._ram_canvas.pack(fill="both", expand=True,
                              padx=8, pady=(0,8))

        # Brain usage panel
        brain_f = tk.Frame(mid, bg=self.C["panel"],
                          highlightbackground=self.C["border"],
                          highlightthickness=1)
        brain_f.grid(row=0, column=1, sticky="nsew", padx=(4,0))
        tk.Label(brain_f, text=">> BRAIN USAGE",
                bg=self.C["panel"], fg=self.C["cyan"],
                font=self.F["head"]).pack(anchor="w", padx=8, pady=4)
        self._brain_frame = tk.Frame(brain_f, bg=self.C["panel"])
        self._brain_frame.pack(fill="both", expand=True, padx=8)
        self._brain_bars = {}

        # Response time chart
        bot_f = tk.Frame(self._win, bg=self.C["panel"],
                        highlightbackground=self.C["border"],
                        highlightthickness=1)
        bot_f.pack(fill="x", padx=16, pady=(4,8))
        tk.Label(bot_f, text=">> RESPONSE TIMES (last 20 queries)",
                bg=self.C["panel"], fg=self.C["cyan"],
                font=self.F["head"]).pack(anchor="w", padx=8, pady=4)
        self._time_canvas = tk.Canvas(
            bot_f, bg=self.C["input_bg"],
            highlightthickness=0, height=80)
        self._time_canvas.pack(fill="both", expand=True,
                               padx=8, pady=(0,8))

    def _update_loop(self):
        while self._running and self._win:
            try:
                self._win.after(0, self._refresh_ui)
            except: pass
            time.sleep(2)

    def _refresh_ui(self):
        if not self._win or not self._win.winfo_exists():
            return
        try:
            # RAM
            try:
                import psutil
                mb = psutil.Process(os.getpid()).memory_info().rss/(1024**2)
            except: mb = 0
            self._ram_history.append(mb)

            # Update stat cards
            ready = sum(
                1 for m in __import__('config.models',
                    fromlist=['MODELS']).MODELS.values()
                if (Path(self.settings.model_path)/m["file"]).exists()
            )
            total = len(__import__('config.models',
                fromlist=['MODELS']).MODELS)
            self._stat_labels["RAM"].config(text=f"{mb:.0f}MB")
            self._stat_labels["QUERIES"].config(
                text=str(self._total_queries))
            if self._total_queries > 0:
                avg = self._total_time/self._total_queries
                self._stat_labels["AVG TIME"].config(
                    text=f"{avg:.1f}s")
            self._stat_labels["MODELS"].config(
                text=f"{ready}/{total}")

            # Draw RAM chart
            self._draw_ram_chart()
            # Draw time chart
            self._draw_time_chart()
            # Update brain bars
            self._update_brain_bars()
        except Exception as e:
            pass

    def _draw_ram_chart(self):
        c = self._ram_canvas
        c.delete("all")
        try:
            w = c.winfo_width()
            h = c.winfo_height()
            if w < 10 or h < 10:
                return
            data = list(self._ram_history)
            if len(data) < 2:
                return
            max_val = max(max(data), self.settings.ram_limit_mb*0.9)
            limit_y = h - (self.settings.ram_limit_mb/max_val)*(h-20) - 10

            # Grid lines
            for pct in [25,50,75,100]:
                y = h - (pct/100)*(h-20) - 10
                c.create_line(0,y,w,y,fill=self.C["border"],dash=(2,4))
                c.create_text(4, y-8, text=f"{int(max_val*pct/100)}MB",
                             fill=self.C["dim"],
                             font=("Consolas",7), anchor="w")

            # RAM limit line
            c.create_line(0,limit_y,w,limit_y,
                         fill=self.C["error"],width=1,dash=(4,2))
            c.create_text(w-4, limit_y-8, text="LIMIT",
                         fill=self.C["error"],
                         font=("Consolas",7), anchor="e")

            # Draw filled area
            step = w / max(len(data)-1, 1)
            pts  = []
            for i, val in enumerate(data):
                x = i * step
                y = h - (val/max_val)*(h-20) - 10
                pts.extend([x,y])

            if len(pts) >= 4:
                area = [pts[0],h] + pts + [pts[-2],h]
                c.create_polygon(area, fill=self.C["cyan"]+"33",
                                outline="")
                c.create_line(pts, fill=self.C["cyan"],
                             width=2, smooth=True)

            # Current value dot
            lx = pts[-2]
            ly = pts[-1]
            c.create_oval(lx-4,ly-4,lx+4,ly+4,
                         fill=self.C["cyan"], outline="")
        except Exception:
            pass

    def _draw_time_chart(self):
        c = self._time_canvas
        c.delete("all")
        try:
            w = c.winfo_width()
            h = c.winfo_height()
            if w < 10 or h < 10:
                return
            data = list(self._time_history)
            if not data:
                c.create_text(w//2, h//2,
                             text="No queries yet",
                             fill=self.C["dim"],
                             font=self.F["small"])
                return
            max_t = max(max(data), 1)
            step  = w / max(len(data), 1)
            for i, val in enumerate(data):
                x1 = i * step + 2
                x2 = x1 + step - 4
                bh = (val/max_t) * (h-20)
                y1 = h - bh - 5
                y2 = h - 5
                color = (self.C["green"] if val < 2
                        else self.C["warning"] if val < 5
                        else self.C["error"])
                c.create_rectangle(x1,y1,x2,y2,
                                  fill=color,outline="")
                c.create_text((x1+x2)//2, y1-6,
                             text=f"{val:.1f}s",
                             fill=self.C["dim"],
                             font=("Consolas",7))
        except Exception:
            pass

    def _update_brain_bars(self):
        try:
            for w in self._brain_frame.winfo_children():
                w.destroy()
            total = sum(self._brain_counts.values()) or 1
            for brain, count in sorted(
                    self._brain_counts.items(),
                    key=lambda x:x[1], reverse=True):
                pct = int(count/total*100)
                row = tk.Frame(self._brain_frame,
                              bg=self.C["panel"])
                row.pack(fill="x", pady=1)
                tk.Label(row, text=f"[{brain}]",
                        bg=self.C["panel"],
                        fg=self.C["orange"],
                        font=self.F["small"],
                        width=9).pack(side="left")
                bar_f = tk.Frame(row, bg=self.C["border"],
                                height=12)
                bar_f.pack(side="left", fill="x",
                          expand=True, padx=4)
                bar_f.pack_propagate(False)
                fill_w = max(int(pct/100*150), 2)
                tk.Frame(bar_f, bg=self.C["cyan"],
                        width=fill_w).pack(
                        side="left", fill="y")
                tk.Label(row, text=f"{count}x {pct}%",
                        bg=self.C["panel"],
                        fg=self.C["dim"],
                        font=self.F["small"]).pack(side="right")
        except Exception:
            pass

    def record_query(self, brain: str, duration: float):
        """Called after each query to update dashboard."""
        self._total_queries += 1
        self._total_time    += duration
        self._brain_counts[brain] = self._brain_counts.get(brain,0)+1
        self._time_history.append(duration)

    def _close(self):
        self._running = False
        if self._win:
            self._win.destroy()

    def toggle(self):
        if self._win and self._win.winfo_exists():
            self._close()
        else:
            self.open()
