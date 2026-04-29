"""
GP PRO AGENT - Auto Setup Window
Shows while downloading and installing Ollama + models.
User sees progress - no manual steps needed.
"""
from typing import Optional, Callable
import tkinter as tk
from tkinter import ttk
import threading, sys, os
from pathlib import Path

BASE = Path(__file__).parent.parent
sys.path.insert(0, str(BASE))

from config.settings import Settings
from modules.auto_setup import AutoSetup

class SetupWindow:
    """
    Professional setup window that:
    1. Downloads Ollama automatically
    2. Installs silently
    3. Pulls AI models
    4. Shows progress
    5. Launches main app when done
    """
    def __init__(self):
        self.settings = Settings()
        self.settings.ensure_dirs()
        self._done    = False
        self._setup   = AutoSetup(
            str(self.settings.brain_root),
            progress_callback=self._on_progress,
            done_callback=self._on_done)
        self._setup_root()
        self._build()

    def _setup_root(self):
        self.root = tk.Tk()
        self.root.title("GP PRO AGENT - Auto Setup")
        self.root.geometry("750x520")
        self.root.resizable(False,False)
        self.root.configure(bg="#0a0f1a")
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth()-750)//2
        y = (self.root.winfo_screenheight()-520)//2
        self.root.geometry(f"750x520+{x}+{y}")
        self.root.protocol("WM_DELETE_WINDOW",
                          self._on_close)

    def _build(self):
        BG    = "#0a0f1a"
        PANEL = "#0d1526"
        CYAN  = "#00e5ff"
        GREEN = "#00ff88"
        DIM   = "#3a5a7a"
        WHITE = "#d0e8ff"

        # Left panel
        left = tk.Frame(self.root, bg="#050c18", width=240)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)
        tk.Label(left, text="[GP]", bg="#050c18", fg=CYAN,
                font=("Consolas",40,"bold")).pack(pady=(60,10))
        tk.Label(left, text="GP PRO\nAGENT",
                bg="#050c18", fg=WHITE,
                font=("Consolas",20,"bold"),
                justify="center").pack()
        tk.Label(left, text="v4.0",
                bg="#050c18", fg=DIM,
                font=("Consolas",10)).pack(pady=(4,30))
        features = [
            "Real AI Engine",
            "11 Brain Models",
            "PLC Engineering",
            "GUI Automation",
            "Predictive Maint",
            "Digital Twin",
            "Auto Setup",
            "100% Offline",
        ]
        for f in features:
            tk.Label(left, text=f"OK {f}",
                    bg="#050c18", fg=GREEN,
                    font=("Consolas",9),
                    anchor="w").pack(fill="x", padx=20, pady=1)
        tk.Label(left, text="IHTM Department",
                bg="#050c18", fg=DIM,
                font=("Consolas",8)).pack(side="bottom", pady=16)

        # Right panel
        right = tk.Frame(self.root, bg=BG)
        right.pack(side="right", fill="both", expand=True)

        tk.Label(right, text="Auto Setup",
                bg=BG, fg=WHITE,
                font=("Consolas",18,"bold")).pack(
                anchor="w", padx=24, pady=(28,4))
        tk.Label(right,
                text="Setting up AI engine automatically.\nNo manual steps required.",
                bg=BG, fg=DIM,
                font=("Consolas",9),
                justify="left").pack(anchor="w", padx=24)

        tk.Frame(right, bg="#1a3a5c",
                height=1).pack(fill="x", padx=24, pady=12)

        # Status label
        self.status_lbl = tk.Label(right,
            text="Initializing...",
            bg=BG, fg=CYAN,
            font=("Consolas",10,"bold"),
            anchor="w")
        self.status_lbl.pack(fill="x", padx=24)

        self.detail_lbl = tk.Label(right,
            text="",
            bg=BG, fg=DIM,
            font=("Consolas",9),
            anchor="w")
        self.detail_lbl.pack(fill="x", padx=24, pady=(2,8))

        # Main progress bar
        bar_f = tk.Frame(right, bg="#1a3a5c", height=18)
        bar_f.pack(fill="x", padx=24, pady=(0,12))
        bar_f.pack_propagate(False)
        self.main_bar = tk.Frame(bar_f, bg=CYAN, width=0)
        self.main_bar.pack(side="left", fill="y")
        self.pct_lbl = tk.Label(right, text="0%",
                                 bg=BG, fg=DIM,
                                 font=("Consolas",9),
                                 anchor="w")
        self.pct_lbl.pack(fill="x", padx=24)

        # Steps list
        tk.Label(right, text="Setup Steps:",
                bg=BG, fg=DIM,
                font=("Consolas",9),
                anchor="w").pack(fill="x", padx=24, pady=(12,4))

        steps_data = [
            ("check",    "Checking existing installation"),
            ("download", "Downloading Ollama AI engine"),
            ("install",  "Installing AI engine silently"),
            ("start",    "Starting AI server"),
            ("phi3",     "Downloading Phi-3 Brain (2.4GB)"),
            ("mistral",  "Downloading Mistral Brain (4.1GB)"),
            ("codellama","Downloading CodeLlama Brain (3.8GB)"),
            ("verify",   "Verifying all systems"),
        ]
        self.step_labels = {}
        for step_id, desc in steps_data:
            rf = tk.Frame(right, bg=PANEL, pady=3)
            rf.pack(fill="x", padx=24, pady=1)
            dot = tk.Label(rf, text="o", bg=PANEL,
                          fg=DIM, font=("Consolas",9))
            dot.pack(side="left", padx=6)
            tk.Label(rf, text=desc,
                    bg=PANEL, fg=WHITE,
                    font=("Consolas",9),
                    anchor="w").pack(side="left",fill="x",expand=True)
            self.step_labels[step_id] = dot

        # Launch button (hidden until done)
        self.launch_btn = tk.Button(right,
            text="> LAUNCH GP PRO AGENT",
            bg=CYAN, fg=BG,
            font=("Consolas",12,"bold"),
            relief="flat", cursor="hand2",
            command=self._launch)
        # Note: packed when ready

        # Skip button
        tk.Button(right,
                 text="Skip setup (use if Ollama already installed)",
                 bg="#0a2a4a", fg=DIM,
                 font=("Consolas",8), relief="flat",
                 cursor="hand2",
                 command=self._skip).pack(
                 side="bottom", pady=8)

    def _on_progress(self, ptype: str, message: str,
                     pct: int):
        """Update progress from setup thread."""
        def _update():
            safe = message.encode('ascii','replace').decode('ascii')
            self.status_lbl.config(text=safe[:60])
            self.pct_lbl.config(text=f"{pct}%")
            # Update progress bar
            bar_w = max(4, int(480 * pct/100))
            self.main_bar.config(width=bar_w)
            # Update step indicators
            step_map = {
                "status":    "check",
                "download":  "download",
                "model":     self._current_model(message),
                "done":      "verify",
                "error":     "verify",
                "warning":   "verify",
            }
            step = step_map.get(ptype, "check")
            if step in self.step_labels:
                color = "#ff4444" if ptype=="error" else "#00e5ff"
                sym   = "X" if ptype=="error" else "~"
                self.step_labels[step].config(
                    text=sym, fg=color)
            if pct >= 100:
                self.detail_lbl.config(text=safe[:70])

        self.root.after(0, _update)

    def _current_model(self, message: str) -> str:
        msg = message.lower()
        if "phi3"      in msg or "phi-3"    in msg: return "phi3"
        if "mistral"   in msg:                       return "mistral"
        if "codellama" in msg or "code"     in msg:  return "codellama"
        return "check"

    def _on_done(self):
        """Called when setup complete."""
        self._done = True
        def _show():
            self.status_lbl.config(
                text="Setup Complete! All AI brains ready!")
            for lbl in self.step_labels.values():
                lbl.config(text="*", fg="#00ff88")
            self.launch_btn.pack(fill="x", padx=24,
                                pady=12, ipady=8)
        self.root.after(0, _show)

    def _launch(self):
        """Launch main app."""
        self.root.destroy()
        from gui.main_window import MainWindow
        MainWindow().run()

    def _skip(self):
        """Skip setup and launch directly."""
        self.root.destroy()
        from gui.main_window import MainWindow
        MainWindow().run()

    def _on_close(self):
        if self._done:
            self.root.destroy()
        else:
            import tkinter.messagebox as mb
            if mb.askyesno("Exit?",
                "Setup is in progress.\nQuit anyway?"):
                self.root.destroy()

    def run(self):
        self._setup.run_setup()
        self.root.mainloop()
