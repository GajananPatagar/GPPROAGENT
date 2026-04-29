"""
GP PRO AGENT v4.0 - Main Window
REAL AI using Ollama engine.
All 11 brains actually work now.
20 real working features.
"""
import tkinter as tk
from tkinter import ttk, scrolledtext
import threading, time, sys, os, json, gc, subprocess, shutil, re
from pathlib import Path

BASE = Path(__file__).parent.parent
sys.path.insert(0, str(BASE))

from config.settings import Settings
from config.models   import MODELS, CHAT_MODELS
from modules.ollama_engine   import OllamaEngine, BRAIN_MODELS
from modules.memory_db       import MemoryDB
from modules.scheduler       import TaskScheduler
from modules.dashboard       import LiveDashboard
from modules.alert_system    import AlertSystem
from modules.autonomous_agent import AutonomousAgent
from modules.knowledge_graph  import KnowledgeGraph
from modules.predictive_maintenance import PredictiveMaintenanceAI
from modules.digital_twin    import DigitalTwin
from modules.nl_plc          import NLPLCCompiler
from modules.report_generator import ReportGenerator
from modules.auto_documentation import AutoDocumentation
from modules.file_manager    import SmartFileManager
from modules.web_server      import WebServer
from modules.self_healing    import SelfHealingSystem
from modules.features_20     import FeatureHub

SW_MAP = {
    "notepad":      ("notepad.exe",   "Notepad"),
    "calculator":   ("calc.exe",      "Calculator"),
    "paint":        ("mspaint.exe",   "Paint"),
    "explorer":     ("explorer.exe",  "File Explorer"),
    "task manager": ("taskmgr.exe",   "Task Manager"),
    "cmd":          ("cmd.exe",       "Command Prompt"),
    "word":         ("winword.exe",   "Microsoft Word"),
    "excel":        ("excel.exe",     "Microsoft Excel"),
    "chrome":       ("chrome.exe",    "Chrome"),
    "edge":         ("msedge.exe",    "Edge"),
    "vs code":      ("code.exe",      "VS Code"),
    "vscode":       ("code.exe",      "VS Code"),
    "pcwin":        ("PCWin.exe",     "PCWin"),
    "studio 5000":  ("Studio5000Launcher.exe", "Studio 5000"),
    "rslogix":      ("Studio5000Launcher.exe", "RSLogix"),
    "tia portal":   ("TIA Portal.exe","TIA Portal"),
}


class MainWindow:
    def __init__(self):
        self.settings   = Settings()
        self.settings.ensure_dirs()
        self._busy      = False
        self._cancel    = threading.Event()
        self._qcount    = 0
        self._ttime     = 0.0
        self._minimized = False
        self._mini_win  = None
        self._dl_win    = None
        self._stream_buffer = ""

        self.C = {
            "bg":      "#0a0f1a",
            "panel":   "#0d1526",
            "border":  "#1a3a5c",
            "cyan":    self.settings.ui.get("accent_color","#00e5ff"),
            "green":   "#00ff88",
            "orange":  "#ff6b2b",
            "purple":  "#bf5fff",
            "white":   "#d0e8ff",
            "dim":     "#3a5a7a",
            "input_bg":"#071020",
            "button":  "#0a2a4a",
            "error":   "#ff4444",
            "warning": "#ffaa00",
        }
        self.F = {
            "title":("Consolas",16,"bold"),
            "head": ("Consolas",11,"bold"),
            "body": ("Consolas",self.settings.ui.get("font_size",10)),
            "small":("Consolas",9),
            "input":("Consolas",11),
        }

        # Init AI engine FIRST
        self.ai = OllamaEngine(notify_callback=self._msg_system)

        # Init all modules
        # Feature hub - 20 extra features
        self.memory    = MemoryDB(self.settings.brain_root)
        self.features  = FeatureHub(
            str(self.settings.brain_root),
            self.ai.ask,
            self._msg_system)
        self.healer    = SelfHealingSystem(
            str(self.settings.brain_root), self._msg_system)
        self.pred_maint = PredictiveMaintenanceAI(
            str(self.settings.brain_root), self._msg_system)
        self.twin      = DigitalTwin(
            str(self.settings.brain_root), self._msg_system)
        self.nl_plc    = NLPLCCompiler(
            str(self.settings.brain_root), self.ai.ask)
        self.reporter  = ReportGenerator(
            str(self.settings.brain_root), self._msg_system)
        self.auto_doc  = AutoDocumentation(
            str(self.settings.brain_root), self.ai.ask, self._msg_system)
        self.files     = SmartFileManager(str(self.settings.brain_root))
        self.graph     = KnowledgeGraph(
            str(self.settings.brain_root), self.C, self.F)
        self.web       = WebServer(self._web_handler, port=5000)
        self.alerts    = AlertSystem(
            str(self.settings.brain_root), self.C, self.F,
            self._msg_system)
        self.auto_agent = AutonomousAgent(
            str(self.settings.brain_root),
            self._auto_execute, self._msg_system)
        self.dashboard  = LiveDashboard(
            None, self.C, self.F, self.settings)
        self.scheduler  = TaskScheduler(
            str(self.settings.brain_root), self._auto_execute)

        # Build UI
        self._setup_root()
        self.dashboard._root = self.root
        self._build_ui()

        # Start background services
        threading.Thread(target=self._start_services,
                        daemon=True).start()

    def _setup_root(self):
        self.root = tk.Tk()
        self.root.title("GP PRO AGENT v4.0 - Real AI")
        self.root.geometry("1350x900")
        self.root.minsize(1000,650)
        self.root.configure(bg=self.C["bg"])
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.root.geometry(f"1350x900+{(sw-1350)//2}+{(sh-900)//2}")

    def _start_services(self):
        time.sleep(1)
        self.healer.start()
        self.pred_maint.start_monitoring()
        self.twin.start()
        self.web.start()
        self.alerts.start_monitoring()
        self.auto_agent.start()
        self.scheduler.start()
        self._startup_check()

    # =========================================================
    # UI BUILDING
    # =========================================================

    def _build_ui(self):
        m = tk.Frame(self.root, bg=self.C["bg"])
        m.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)
        m.grid_rowconfigure(1, weight=1)
        m.grid_columnconfigure(0, weight=3)
        m.grid_columnconfigure(1, weight=1)
        self._main = m
        self._build_header(m)
        self._build_chat(m)
        self._build_sidebar(m)
        self._build_input(m)
        self._welcome()

    def _build_header(self, p):
        h = tk.Frame(p, bg=self.C["panel"],
                    highlightbackground=self.C["border"],
                    highlightthickness=1)
        h.grid(row=0, column=0, columnspan=2,
               sticky="ew", pady=(0,4))

        tk.Label(h, text="[GP] GP PRO AGENT v4.0",
                bg=self.C["panel"], fg=self.C["cyan"],
                font=self.F["title"]).pack(side="left", padx=12, pady=8)

        self.ai_lbl = tk.Label(h, text="AI: Checking...",
                               bg=self.C["panel"],
                               fg=self.C["warning"],
                               font=self.F["small"])
        self.ai_lbl.pack(side="left", padx=8)

        self.ram_lbl = tk.Label(h, text="RAM:--",
                                bg=self.C["panel"],
                                fg=self.C["green"],
                                font=self.F["small"])
        self.ram_lbl.pack(side="left", padx=8)

        # Priority selector
        self.priority = tk.StringVar(value="balanced")
        pf = tk.Frame(h, bg=self.C["panel"])
        pf.pack(side="left", padx=8)
        tk.Label(pf, text="Mode:", bg=self.C["panel"],
                fg=self.C["dim"], font=self.F["small"]).pack(side="left")
        for v, l in [("speed","Fast"),
                     ("balanced","Balance"),
                     ("accuracy","Accurate")]:
            tk.Radiobutton(pf, text=l, variable=self.priority,
                          value=v, bg=self.C["panel"],
                          fg=self.C["white"],
                          selectcolor=self.C["button"],
                          activebackground=self.C["panel"],
                          font=self.F["small"]).pack(side="left",padx=2)

        # Feature buttons
        btns = [
            ("[MINI]",  self._enter_mini),
            ("[DASH]",  self.dashboard.toggle),
            ("[MODELS]",self._model_manager),
            ("[WEB]",   self._web_info),
            ("[GRAPH]", lambda: self.graph.open_window(self.root)),
            ("[TWIN]",  self._twin_panel),
            ("[MAINT]", self._maint_panel),
            ("[DOCS]",  self._docs_panel),
            ("[ALERTS]",lambda: self.alerts.open_window(self.root)),
            ("[SCHED]", self._scheduler_panel),
        ]
        for txt, cmd in btns:
            tk.Button(h, text=txt, bg=self.C["button"],
                     fg=self.C["white"],
                     font=("Consolas",8), relief="flat",
                     cursor="hand2",
                     command=cmd).pack(side="right", padx=1, pady=4)

    def _build_chat(self, p):
        f = tk.Frame(p, bg=self.C["panel"],
                    highlightbackground=self.C["border"],
                    highlightthickness=1)
        f.grid(row=1, column=0, sticky="nsew",
               padx=(0,4), pady=4)
        f.grid_rowconfigure(1, weight=1)
        f.grid_columnconfigure(0, weight=1)

        hdr = tk.Frame(f, bg=self.C["panel"])
        hdr.grid(row=0, column=0, sticky="ew", padx=8, pady=4)
        tk.Label(hdr, text=">> CONVERSATION",
                bg=self.C["panel"], fg=self.C["cyan"],
                font=self.F["head"]).pack(side="left")
        self.brain_lbl = tk.Label(hdr, text="Brain: --",
                                   bg=self.C["panel"],
                                   fg=self.C["orange"],
                                   font=self.F["small"])
        self.brain_lbl.pack(side="right")

        self.chat = scrolledtext.ScrolledText(
            f, bg=self.C["input_bg"],
            fg=self.C["white"],
            font=self.F["body"],
            wrap=tk.WORD, state="disabled",
            borderwidth=0, highlightthickness=0,
            padx=12, pady=10)
        self.chat.grid(row=1, column=0, sticky="nsew",
                       padx=6, pady=(0,6))

        # Text tags
        self.chat.tag_config("user",
            foreground=self.C["cyan"],
            font=("Consolas",10,"bold"))
        self.chat.tag_config("agent",
            foreground=self.C["green"])
        self.chat.tag_config("stream",
            foreground="#aaffcc")
        self.chat.tag_config("model",
            foreground=self.C["orange"])
        self.chat.tag_config("system",
            foreground=self.C["dim"])
        self.chat.tag_config("error",
            foreground=self.C["error"])
        self.chat.tag_config("action",
            foreground=self.C["warning"])
        self.chat.tag_config("code",
            foreground="#88ffaa",
            font=("Consolas",9))

    def _build_sidebar(self, p):
        f = tk.Frame(p, bg=self.C["panel"],
                    highlightbackground=self.C["border"],
                    highlightthickness=1)
        f.grid(row=1, column=1, sticky="nsew",
               padx=(4,0), pady=4)
        f.grid_columnconfigure(0, weight=1)

        # Brain status
        tk.Label(f, text=">> BRAIN STATUS",
                bg=self.C["panel"], fg=self.C["cyan"],
                font=self.F["head"]).grid(
                row=0, column=0, sticky="w", padx=10, pady=6)

        canvas = tk.Canvas(f, bg=self.C["panel"],
                          highlightthickness=0, height=180)
        sb = ttk.Scrollbar(f, orient="vertical",
                          command=canvas.yview)
        mf = tk.Frame(canvas, bg=self.C["panel"])
        canvas.configure(yscrollcommand=sb.set)
        canvas.grid(row=1, column=0, sticky="nsew", padx=4)
        sb.grid(row=1, column=1, sticky="ns")
        f.grid_rowconfigure(1, weight=1)
        cw = canvas.create_window((0,0), window=mf, anchor="nw")
        mf.bind("<Configure>", lambda e: canvas.configure(
            scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(
            cw, width=e.width))

        self.dots = {}
        for key, model in MODELS.items():
            row = tk.Frame(mf, bg=self.C["panel"], pady=1)
            row.pack(fill="x", padx=4)
            dot = tk.Label(row, text="*", bg=self.C["panel"],
                          fg=self.C["dim"], font=self.F["small"])
            dot.pack(side="left")
            ollama_model = BRAIN_MODELS.get(key,"phi3")
            tk.Label(row, text=f"[{key}]",
                    bg=self.C["panel"], fg=self.C["orange"],
                    font=self.F["small"], width=8,
                    anchor="w").pack(side="left")
            tk.Label(row, text=f"-> {ollama_model}",
                    bg=self.C["panel"], fg=self.C["dim"],
                    font=self.F["small"]).pack(side="left")
            self.dots[key] = dot

        sep = lambda r: tk.Frame(f, bg=self.C["border"],
                                 height=1).grid(row=r, column=0,
                                 columnspan=2, sticky="ew",
                                 padx=8, pady=3)
        sep(2)

        tk.Label(f, text=">> ACTIVE BRAIN",
                bg=self.C["panel"], fg=self.C["cyan"],
                font=self.F["head"]).grid(
                row=3, column=0, sticky="w", padx=10, pady=(4,2))
        self.active_lbl = tk.Label(f, text="Waiting...",
                                    bg=self.C["panel"],
                                    fg=self.C["orange"],
                                    font=self.F["small"],
                                    justify="left",
                                    wraplength=190)
        self.active_lbl.grid(row=4, column=0, sticky="w",
                             padx=10, pady=2)
        sep(5)

        tk.Label(f, text=">> MEMORY",
                bg=self.C["panel"], fg=self.C["cyan"],
                font=self.F["head"]).grid(
                row=6, column=0, sticky="w", padx=10, pady=(4,2))
        self.mem_lbl = tk.Label(f, text="Entries: 0",
                                 bg=self.C["panel"],
                                 fg=self.C["white"],
                                 font=self.F["small"])
        self.mem_lbl.grid(row=7, column=0, sticky="w",
                          padx=10, pady=2)
        sep(8)

        tk.Label(f, text=">> SESSION",
                bg=self.C["panel"], fg=self.C["cyan"],
                font=self.F["head"]).grid(
                row=9, column=0, sticky="w", padx=10, pady=(4,2))
        self.stats_lbl = tk.Label(
            f, text="Queries : 0\nAvg time: --\nLast    : --",
            bg=self.C["panel"], fg=self.C["white"],
            font=self.F["small"], justify="left")
        self.stats_lbl.grid(row=10, column=0, sticky="w",
                            padx=10, pady=2)
        sep(11)

        tk.Label(f, text=">> QUICK ACTIONS",
                bg=self.C["panel"], fg=self.C["cyan"],
                font=self.F["head"]).grid(
                row=12, column=0, sticky="w", padx=10, pady=(4,2))

        quick_actions = [
            ("PLC Ladder Logic",   "Explain PLC ladder logic all elements and instructions in detail"),
            ("Safety SIL LOTO",    "Explain industrial safety SIL levels LOTO estop procedures"),
            ("Write Python Code",  "Show Python code examples for industrial automation"),
            ("GUI Automation",     "How to automate GUI with pyautogui give examples"),
            ("Modbus TCP Python",  "Write Python Modbus TCP client to read PLC registers"),
            ("PLC Troubleshoot",   "How to troubleshoot common PLC faults and errors"),
            ("Engineering Calc",   "Show common engineering formulas and unit conversions"),
            ("Open Notepad",       "Open Notepad"),
            ("System Status",      "Show complete system status"),
            ("Take Screenshot",    "Take a screenshot of my screen now"),
        ]
        for i, (lbl, cmd) in enumerate(quick_actions):
            tk.Button(f, text=lbl,
                     bg=self.C["button"], fg=self.C["white"],
                     font=self.F["small"], relief="flat",
                     cursor="hand2",
                     command=lambda c=cmd: self._quick(c)
                     ).grid(row=13+i, column=0, sticky="ew",
                            padx=10, pady=1)

    def _build_input(self, p):
        f = tk.Frame(p, bg=self.C["panel"],
                    highlightbackground=self.C["border"],
                    highlightthickness=1)
        f.grid(row=2, column=0, columnspan=2,
               sticky="ew", pady=(4,0))
        f.grid_columnconfigure(0, weight=1)

        tk.Label(f,
                text="Ask anything - REAL AI responds | PLC | Code | Safety | Math | Files | Automation...",
                bg=self.C["panel"], fg=self.C["dim"],
                font=self.F["small"], anchor="w").grid(
                row=0, column=0, columnspan=2,
                sticky="ew", padx=12, pady=(6,2))

        inf = tk.Frame(f, bg=self.C["panel"])
        inf.grid(row=1, column=0, columnspan=2,
                sticky="ew", padx=8, pady=(0,6))
        inf.grid_columnconfigure(0, weight=1)

        self.inp = tk.Text(inf,
                          bg=self.C["input_bg"],
                          fg=self.C["white"],
                          font=self.F["input"],
                          height=3, wrap=tk.WORD,
                          insertbackground=self.C["cyan"],
                          borderwidth=0, highlightthickness=1,
                          highlightcolor=self.C["cyan"],
                          highlightbackground=self.C["border"],
                          padx=10, pady=8)
        self.inp.grid(row=0, column=0, sticky="ew", padx=(0,8))
        self.inp.bind("<Return>", self._on_enter)

        bf = tk.Frame(inf, bg=self.C["panel"])
        bf.grid(row=0, column=1)

        self.send_btn = tk.Button(bf, text="> SEND",
                                   bg=self.C["cyan"],
                                   fg=self.C["bg"],
                                   font=self.F["head"],
                                   width=10, relief="flat",
                                   cursor="hand2",
                                   command=self._send)
        self.send_btn.pack(pady=(0,3))

        self.cancel_btn = tk.Button(bf, text="X CANCEL",
                                     bg=self.C["error"],
                                     fg=self.C["white"],
                                     font=self.F["small"],
                                     width=10, relief="flat",
                                     cursor="hand2",
                                     command=self._cancel,
                                     state="disabled")
        self.cancel_btn.pack(pady=(0,3))

        tk.Button(bf, text="CLEAR",
                 bg=self.C["button"], fg=self.C["white"],
                 font=self.F["small"], width=10,
                 relief="flat", cursor="hand2",
                 command=self._clear).pack()

        self.status_bar = tk.Label(f,
                                    text="Ready - Real AI Online",
                                    bg=self.C["panel"],
                                    fg=self.C["dim"],
                                    font=self.F["small"],
                                    anchor="w")
        self.status_bar.grid(row=2, column=0, columnspan=2,
                              sticky="ew", padx=12,
                              pady=(0,4))

    # =========================================================
    # CORE - REAL AI PROCESSING
    # =========================================================

    def _on_enter(self, e):
        if not (e.state & 0x1):
            self._send()
            return "break"

    def _send(self):
        if self._busy:
            return
        q = self.inp.get("1.0","end-1c").strip()
        if not q:
            return
        self.inp.delete("1.0","end")
        self._start(q)

    def _start(self, query: str):
        self._busy = True
        self._cancel.clear()
        self.send_btn.config(state="disabled", text="...")
        self.cancel_btn.config(state="normal")
        self.status_bar.config(text="Thinking...",
                              fg=self.C["warning"])
        threading.Thread(target=self._process,
                        args=(query,), daemon=True).start()

    def _cancel(self):
        self._cancel.set()
        self._msg("system", "[Cancelled]\n\n")
        self._done("Cancelled.")

    def _process(self, query: str):
        self._msg("user", f"You: {query}\n")
        self._all_dots(self.C["dim"])
        q = query.lower().strip()

        try:
            # Record for learning
            self.auto_agent.record_activity(query)
            self.graph.learn_from_query(query, "auto", [])

            # ── Check memory first ────────────────────────
            if not any(w in q for w in ["open","screenshot",
                                         "what is on screen"]):
                cached = self.memory.recall(query, threshold=0.82)
                if cached:
                    self._msg("model",
                        f"[MEMORY RECALL | {cached['brain']} | "
                        f"used {cached['uses']}x]\n")
                    self._msg("agent",
                        f"{cached['answer']}\n\n")
                    self._done("From memory (instant!)")
                    return

            # ── UI change ─────────────────────────────────
            if self._is_ui_cmd(q):
                self._handle_ui(query)
                return

            # ── Open software ─────────────────────────────
            if any(q.startswith(w) for w in
                   ["open ","launch ","start ","run "]):
                self._handle_open(query)
                return

            # ── Screenshot ────────────────────────────────
            if "screenshot" in q or "capture screen" in q:
                self._handle_screenshot()
                return

            # ── Math ──────────────────────────────────────
            if re.search(r'\d+\s*[\+\-\*\/\%]\s*\d+', q):
                self._handle_math(query)
                return

            # ── NL-PLC ────────────────────────────────────
            if any(w in q for w in ["create plc","write plc",
                                     "generate ladder","plc program for"]):
                self._handle_nl_plc(query)
                return

            # ── Files ─────────────────────────────────────
            if any(w in q for w in ["find file","list files",
                                     "organize","disk space",
                                     "read file"]):
                self._handle_files(query)
                return

            # ── Reports ───────────────────────────────────
            if any(w in q for w in ["generate report",
                                     "create report","write report"]):
                self._handle_report(query)
                return

            # ── Maintenance ───────────────────────────────
            if any(w in q for w in ["maintenance","equipment health",
                                     "predict failure"]):
                self._handle_maint(query)
                return

            # ── Status ────────────────────────────────────
            if q.strip() in ("status","system status","show status"):
                self._show_status()
                return

            # ── REAL AI query ─────────────────────────────
            self._real_ai_query(query)

        except Exception as e:
            self.healer.report_error(e, query, "process")
            self._msg("error", f"Error: {e}\n\n")
            self._done(f"Error: {e}")

    def _real_ai_query(self, query: str):
        """Route to correct brain and get REAL AI response."""
        brain = self._route(query.lower())
        model = MODELS[brain]
        start = time.time()

        # Update UI
        self.root.after(0, self._upd_active, brain)
        self.root.after(0, self._dot, brain, self.C["warning"])
        ollama_model = self.ai.get_model_for_brain(brain)

        self._msg("model",
            f"[{brain.upper()} BRAIN | {ollama_model} | "
            f"{model['accuracy']}% accuracy]\n")
        self.root.after(0, self.status_bar.config,
            {"text": f"Thinking with {brain} brain ({ollama_model})...",
             "fg": self.C["warning"]})
        self.root.after(0, self.brain_lbl.config,
            {"text": f"Brain: {brain} ({ollama_model})"})

        if self._cancel.is_set():
            return

        # Get context from memory
        ctx = ""
        recent = self.memory.get_recent(3)
        if recent:
            ctx = "\n".join(
                f"Q: {m['query'][:50]}" for m in recent)

        # Stream response token by token
        self._msg("stream", "")
        self._stream_buffer = ""

        def on_token(token: str):
            if self._cancel.is_set():
                return
            self._stream_buffer += token
            safe = token.encode(
                'ascii','replace').decode('ascii')
            self.root.after(0, self._append_stream, safe)

        # Call REAL AI
        try:
            answer = self.ai.ask(
                brain, query,
                stream_callback=on_token,
                context=ctx)
        except Exception as e:
            self.healer.report_error(e, query, brain)
            answer = self.ai._knowledge_fallback(brain, query)
            self._msg("agent", f"{answer}\n")

        if self._cancel.is_set():
            return

        # Add newlines after stream
        self._msg("agent", "\n\n")

        dur = round(time.time() - start, 2)
        self.root.after(0, self._dot, brain, self.C["green"])

        # Save to memory
        if answer and len(answer) > 10:
            self.memory.remember(query, answer, brain, True)

        # Update dashboard
        self.dashboard.record_query(brain, dur)
        self.graph.learn_from_query(query, brain, [brain])

        # Update stats
        self._qcount += 1
        self._ttime  += dur
        avg = round(self._ttime / self._qcount, 1)
        self.root.after(0, self.stats_lbl.config,
            {"text": f"Queries : {self._qcount}\n"
                     f"Avg time: {avg}s\nLast    : {dur}s"})
        stats = self.memory.get_stats()
        self.root.after(0, self.mem_lbl.config,
            {"text": f"Entries: {stats['total']}"})
        self._done(f"Done {dur}s | {brain} ({ollama_model})")

    def _append_stream(self, token: str):
        """Append streaming token to chat."""
        self.chat.config(state="normal")
        self.chat.insert("end", token, "stream")
        self.chat.see("end")
        self.chat.config(state="disabled")

    def _route(self, query: str) -> str:
        """Route to best brain by keyword scoring."""
        q = query.lower()
        scores = {}
        pri = self.priority.get()

        for key, model in CHAT_MODELS.items():
            score = 0.0
            for t in model.get("triggers", []):
                if t in q:
                    score += len(t.split()) * 12
            score += (model["accuracy"] / 100) * 15
            if pri == "speed":
                score += (1/max(model["speed_s"],0.1)) * 25
            elif pri == "accuracy":
                score += (model["accuracy"]/100) * 25
            else:
                score += (1/max(model["speed_s"],0.1)) * 8
            # Bonus if model available in Ollama
            ollama_m = BRAIN_MODELS.get(key,"phi3")
            if ollama_m in self.ai._models:
                score += 10
            scores[key] = score

        best = max(scores, key=scores.get)
        print(f"[ROUTE] '{q[:25]}' -> {best} ({scores[best]:.1f})")
        return best

    # =========================================================
    # FEATURE HANDLERS - ALL USE REAL AI
    # =========================================================

    def _handle_math(self, query: str):
        """Math - try direct calculation first, then AI."""
        self._msg("action", "[MATH BRAIN]\n")
        q = query
        try:
            expr = re.search(r'[\d\s\+\-\*\/\.\%\(\)]+', q)
            if expr:
                clean = expr.group().strip()
                if (any(c.isdigit() for c in clean) and
                        any(op in clean for op in ['+','-','*','/'])):
                    val = eval(clean)
                    result = f"Calculation:\n\n  {clean.strip()} = {val}\n"
                    self._msg("agent", f"{result}\n")
                    self._done("Calculated!")
                    return
        except Exception:
            pass
        # Use AI for complex math
        self._real_ai_query(f"Calculate or solve: {query}")

    def _handle_open(self, query: str):
        """Open software - try direct then AI for instructions."""
        q = query.lower()
        opened = None
        app_name = None

        for key, (exe, name) in SW_MAP.items():
            if key in q:
                try:
                    subprocess.Popen(exe, shell=True)
                    opened = exe
                    app_name = name
                    break
                except Exception:
                    pass

        if not opened:
            # Extract app name
            for pat in [r"open (.+?)(?:\s+and|\s*$)",
                       r"launch (.+?)(?:\s+and|\s*$)",
                       r"start (.+?)(?:\s+and|\s*$)"]:
                m = re.search(pat, q)
                if m:
                    app = m.group(1).strip()
                    try:
                        subprocess.Popen(app, shell=True)
                        opened = app
                        app_name = app.title()
                        break
                    except Exception:
                        try:
                            subprocess.Popen(
                                f'start "" "{app}"', shell=True)
                            opened = app
                            app_name = app.title()
                            break
                        except Exception:
                            pass

        # Check for multi-step (open X and write Y)
        if opened and ("write" in q or "type" in q):
            self.root.after(800, self._enter_mini)
            self._msg("action", f"[LEARNER BRAIN | Opening {app_name}]\n")
            # Ask AI for next steps
            ai_response = self.ai.ask(
                "learner",
                f"I opened {app_name}. User wants to: {query}\n"
                f"Give step-by-step instructions to complete this task.")
            self._msg("agent", f"{ai_response}\n\n")
            self._done(f"Opened {app_name}!")
            return

        if opened:
            self.root.after(800, self._enter_mini)
            self._msg("action",
                f"[LEARNER BRAIN | Opened {app_name}]\n")
            self._msg("agent",
                f"Opened {app_name}.\n"
                f"Switched to Mini Mode - I am in the corner.\n"
                f"Ask me anything while using {app_name}!\n\n")
        else:
            # Use AI to help find it
            ai_resp = self.ai.ask("learner",
                f"Help open: {query}\n"
                f"Provide Windows instructions to find and open this software.")
            self._msg("agent", f"{ai_resp}\n\n")
        self._done("Done!")

    def _handle_screenshot(self):
        """Take screenshot."""
        self._msg("action", "[OCR BRAIN | Screenshot]\n")
        try:
            import pyautogui
            img, path = self._do_screenshot()
            if img:
                self._msg("agent",
                    f"Screenshot saved!\nPath: {path}\n"
                    f"Size: {img.width}x{img.height}px\n\n")
            else:
                self._msg("error", "Screenshot failed.\n\n")
        except ImportError:
            self._msg("error",
                "Install pyautogui: pip install pyautogui Pillow\n\n")
        self._done("Screenshot done!")

    def _do_screenshot(self):
        try:
            import pyautogui
            img  = pyautogui.screenshot()
            path = str(self.settings.cache_path / "screenshot.png")
            img.save(path)
            return img, path
        except Exception:
            return None, None

    def _handle_nl_plc(self, query: str):
        """Generate PLC program using AI."""
        self._msg("action", "[NL-PLC | AI Generating]\n")
        # Strip trigger words
        q = query.lower()
        for w in ["create plc program","write plc","generate ladder",
                  "plc program for","program to control"]:
            q = q.replace(w,"").strip()

        # Use real AI to generate better code
        ai_code = self.ai.ask("plc",
            f"Generate IEC 61131-3 Structured Text PLC program for:\n"
            f"'{q or query}'\n\n"
            f"Include: variable declarations, logic, comments, safety checks.")

        prog = self.nl_plc.compile(q or query, f"GP_Program_{self._qcount}")
        if ai_code and len(ai_code) > 50:
            prog.st_code = ai_code

        path = self.nl_plc.save_program(prog)
        self.auto_doc.document_plc_program(
            prog.name, prog.st_code,
            prog.variables, prog.description)

        response = (f"PLC Program Generated!\n\n"
                   f"Name: {prog.name}\n"
                   f"Saved: {path}\n\n"
                   f"Code Preview:\n{prog.st_code[:400]}")
        self._msg("agent", f"{response}\n\n")
        self._done("PLC program generated!")

    def _handle_files(self, query: str):
        """Smart file operations."""
        self._msg("action", "[FILE MANAGER]\n")
        result = self.files.process_command(query, self.ai.ask)
        self._msg("agent", f"{result}\n\n")
        self._done("File operation done!")

    def _handle_report(self, query: str):
        """Generate professional report using AI."""
        self._msg("action", "[REPORT GENERATOR | AI Writing]\n")
        # Use real AI to write report content
        content = self.ai.ask("docs",
            f"Write a professional technical report about: {query}\n"
            f"Include: Executive Summary, Details, Findings, Recommendations.")
        path = self.reporter.quick_report(query, content)
        self._msg("agent",
            f"Report generated!\nFile: {path}\n"
            f"Opening...\n\n")
        self.auto_doc.open_document(path)
        self._done("Report ready!")

    def _handle_maint(self, query: str):
        """Predictive maintenance with AI analysis."""
        self._msg("action", "[PREDICTIVE MAINTENANCE AI]\n")
        health = self.pred_maint.get_health_report()
        sched  = self.pred_maint.get_maintenance_schedule()

        # Let AI analyze the data
        health_summary = "\n".join(
            f"{e['name']}: Health={e['health_score']:.0f}% "
            f"Failure_prob={e['failure_prob']:.1f}%"
            for e in health)

        ai_analysis = self.ai.ask("master",
            f"Analyze this equipment health data and give "
            f"maintenance recommendations:\n{health_summary}")

        self._msg("agent", f"{ai_analysis}\n\n")

        if sched:
            report  = self.reporter.generate_maintenance_report(health, sched)
            path    = self.reporter.save_as_html(report)
            self._msg("action", f"Full report: {path}\n\n")
        self._done("Maintenance analysis done!")

    def _show_status(self):
        """Show complete system status."""
        ai_status = self.ai.get_status()
        mem_stats = self.memory.get_stats()
        models_available = ", ".join(ai_status["models"]) or "None"
        status = (
            f"GP PRO AGENT v4.0 Status:\n\n"
            f"AI Engine: {'ONLINE' if ai_status['available'] else 'OFFLINE'}\n"
            f"Ollama URL: {ai_status['url']}\n"
            f"Models: {models_available}\n\n"
            f"Memory: {mem_stats['total']} entries\n"
            f"Queries: {self._qcount}\n"
            f"Avg time: {round(self._ttime/max(self._qcount,1),1)}s\n\n"
            f"Modules active:\n"
            f"  Predictive Maintenance, Digital Twin, NL-PLC\n"
            f"  Report Generator, Auto-Doc, File Manager\n"
            f"  Knowledge Graph, Alert System, Scheduler\n"
            f"  Autonomous Agent, Self-Healing, Web Server\n\n"
            f"Install models: ollama pull phi3\n"
            f"              ollama pull mistral\n"
            f"              ollama pull codellama")
        self._msg("agent", f"{status}\n\n")
        self._done("Status shown!")

    # =========================================================
    # UI SELF-MODIFICATION WITH REAL AI
    # =========================================================

    def _is_ui_cmd(self, q: str) -> bool:
        return any(k in q for k in [
            "change theme","change color","change accent",
            "make font","font size","change ui","dark mode",
            "light mode","change background",
        ])

    def _handle_ui(self, query: str):
        """Handle UI changes - can use AI to understand intent."""
        q = query.lower()
        changes = []
        colors = {
            "blue":   "#0066ff", "red":    "#ff3333",
            "green":  "#00ff88", "purple": "#bf5fff",
            "orange": "#ff6b2b", "yellow": "#ffdd00",
            "pink":   "#ff66cc", "cyan":   "#00e5ff",
            "teal":   "#00ccaa", "gold":   "#ffd700",
        }
        if any(w in q for w in ["color","theme","accent"]):
            for name, hx in colors.items():
                if name in q:
                    self.C["cyan"] = hx
                    self.settings.ui["accent_color"] = hx
                    self.root.after(0, self.send_btn.config, {"bg": hx})
                    self.chat.tag_config("user", foreground=hx)
                    changes.append(f"Theme -> {name}")
                    break
        if "font" in q:
            cur = self.F["body"][1]
            if any(w in q for w in ["bigger","larger","increase"]):
                ns = min(cur+2, 18)
                self.F["body"] = ("Consolas", ns)
                self.settings.ui["font_size"] = ns
                self.root.after(0, self.chat.config,
                    {"font": self.F["body"]})
                changes.append(f"Font -> {ns}pt")
            elif any(w in q for w in ["smaller","decrease"]):
                ns = max(cur-2, 8)
                self.F["body"] = ("Consolas", ns)
                self.settings.ui["font_size"] = ns
                self.root.after(0, self.chat.config,
                    {"font": self.F["body"]})
                changes.append(f"Font -> {ns}pt")
        if changes:
            self.settings.save_ui()
            self._msg("action",
                f"UI Updated: {', '.join(changes)}\n\n")
        else:
            self._msg("action",
                "Try: 'change theme to blue' | 'make font bigger'\n\n")
        self._done("UI updated!")

    # =========================================================
    # PANEL WINDOWS
    # =========================================================

    def _model_manager(self):
        """Ollama model manager."""
        win = tk.Toplevel(self.root)
        win.title("AI Model Manager")
        win.geometry("700x520")
        win.configure(bg=self.C["bg"])

        tk.Label(win, text=">> AI MODEL MANAGER (Ollama)",
                bg=self.C["bg"], fg=self.C["cyan"],
                font=self.F["head"]).pack(anchor="w", padx=16, pady=12)

        status = self.ai.get_status()
        avail = "ONLINE" if status["available"] else "OFFLINE"
        color = self.C["green"] if status["available"] else self.C["error"]
        tk.Label(win,
                text=f"Ollama: {avail} | URL: {status['url']}",
                bg=self.C["bg"], fg=color,
                font=self.F["small"]).pack(anchor="w", padx=16)

        tk.Label(win,
                text="Install Ollama from: ollama.com | Then pull models below",
                bg=self.C["bg"], fg=self.C["dim"],
                font=self.F["small"]).pack(anchor="w", padx=16)

        tk.Frame(win, bg=self.C["border"],
                height=1).pack(fill="x", padx=16, pady=8)

        # Recommended models
        recommended = [
            ("phi3",       "2.4GB", "Fast - Reflex/Math/Screen Brain"),
            ("mistral",    "4.1GB", "Smart - PLC/Safety/Master Brain"),
            ("codellama",  "3.8GB", "Expert - Code Brain"),
            ("llama3",     "4.7GB", "Advanced - All brains"),
            ("qwen2",      "4.4GB", "Documentation Brain"),
            ("gemma",      "5.0GB", "Safety Brain"),
        ]
        self._prog_labels = {}
        for model, size, desc in recommended:
            in_ollama = model in self.ai._models
            rf = tk.Frame(win, bg=self.C["panel"], pady=4)
            rf.pack(fill="x", padx=16, pady=2)
            c = self.C["green"] if in_ollama else self.C["dim"]
            tk.Label(rf, text="*" if in_ollama else "o",
                    bg=self.C["panel"], fg=c,
                    font=self.F["small"]).pack(side="left", padx=6)
            tk.Label(rf, text=f"{model:<12}",
                    bg=self.C["panel"], fg=self.C["orange"],
                    font=self.F["small"]).pack(side="left")
            tk.Label(rf, text=f"{size:<8}",
                    bg=self.C["panel"], fg=self.C["dim"],
                    font=self.F["small"]).pack(side="left")
            tk.Label(rf, text=desc,
                    bg=self.C["panel"], fg=self.C["white"],
                    font=self.F["small"],
                    anchor="w").pack(side="left", fill="x", expand=True)
            prog_lbl = tk.Label(rf, text="Ready" if in_ollama else "Not installed",
                               bg=self.C["panel"],
                               fg=self.C["green"] if in_ollama else self.C["dim"],
                               font=self.F["small"])
            prog_lbl.pack(side="right", padx=4)
            self._prog_labels[model] = prog_lbl
            if not in_ollama:
                tk.Button(rf, text="Install",
                         bg=self.C["cyan"], fg=self.C["bg"],
                         font=self.F["small"], relief="flat",
                         command=lambda m=model, l=prog_lbl:
                         threading.Thread(
                             target=self._install_model,
                             args=(m, l), daemon=True).start()
                         ).pack(side="right", padx=4)

        # Command reference
        tk.Frame(win, bg=self.C["border"],
                height=1).pack(fill="x", padx=16, pady=8)
        tk.Label(win,
                text="Manual install: Open CMD and run:\n"
                     "  ollama pull phi3\n"
                     "  ollama pull mistral\n"
                     "  ollama pull codellama",
                bg=self.C["bg"], fg=self.C["dim"],
                font=self.F["small"],
                justify="left").pack(anchor="w", padx=16)

    def _install_model(self, model: str, label: tk.Label):
        """Install Ollama model with progress."""
        label.config(text="Installing...", fg=self.C["warning"])
        def progress(status, completed, total):
            if total > 0:
                pct = int(completed/total*100)
                self.root.after(0, label.config,
                    {"text": f"{pct}%"})
            else:
                self.root.after(0, label.config,
                    {"text": status[:15]})
        ok = self.ai.install_model(model, progress)
        color = self.C["green"] if ok else self.C["error"]
        text  = "Installed!" if ok else "Failed"
        self.root.after(0, label.config,
            {"text": text, "fg": color})
        if ok:
            self._msg_system(f"[MODEL] {model} installed!")

    def _web_info(self):
        url = self.web.get_url()
        win = tk.Toplevel(self.root)
        win.title("Web Interface")
        win.geometry("400x200")
        win.configure(bg=self.C["bg"])
        tk.Label(win, text=">> WEB INTERFACE",
                bg=self.C["bg"], fg=self.C["cyan"],
                font=self.F["head"]).pack(pady=(16,8))
        tk.Label(win, text="Access from phone/browser:",
                bg=self.C["bg"], fg=self.C["dim"],
                font=self.F["small"]).pack()
        tk.Label(win, text=url,
                bg=self.C["bg"], fg=self.C["green"],
                font=("Consolas",14,"bold")).pack(pady=8)
        def copy():
            self.root.clipboard_clear()
            self.root.clipboard_append(url)
        tk.Button(win, text="Copy URL",
                 bg=self.C["cyan"], fg=self.C["bg"],
                 font=self.F["head"], relief="flat",
                 command=copy).pack(pady=8)

    def _web_handler(self, query: str) -> dict:
        """Handle web interface queries with real AI."""
        brain = self._route(query.lower())
        model = MODELS[brain]
        start = time.time()
        answer = self.ai.ask(brain, query)
        dur   = round(time.time()-start, 2)
        self.memory.remember(query, answer, brain)
        self._msg("system", f"[WEB] {query[:40]}\n")
        return {
            "answer":   answer,
            "brain":    brain,
            "duration": dur,
            "accuracy": model["accuracy"],
        }

    def _twin_panel(self):
        win = tk.Toplevel(self.root)
        win.title("Digital Twin")
        win.geometry("650x480")
        win.configure(bg=self.C["bg"])
        tk.Label(win, text=">> DIGITAL TWIN SIMULATOR",
                bg=self.C["bg"], fg=self.C["cyan"],
                font=self.F["head"]).pack(anchor="w", padx=16, pady=12)
        status = self.twin.get_status()
        running = status["plc_status"]["running"]
        tk.Label(win,
                text=f"Simulation: {'RUNNING' if running else 'STOPPED'}",
                bg=self.C["bg"],
                fg=self.C["green"] if running else self.C["error"],
                font=self.F["small"]).pack(anchor="w", padx=16)
        tk.Frame(win, bg=self.C["border"],
                height=1).pack(fill="x", padx=16, pady=8)
        for sc in status.get("scenarios", []):
            tk.Button(win, text=f"Run: {sc.replace('_',' ').title()}",
                     bg=self.C["button"], fg=self.C["white"],
                     font=self.F["small"], relief="flat",
                     command=lambda s=sc,w=win:
                     [self._quick(f"simulate run scenario {s}"),w.destroy()]
                     ).pack(fill="x", padx=16, pady=3)

        # Live values
        tk.Frame(win, bg=self.C["border"],
                height=1).pack(fill="x", padx=16, pady=8)
        tk.Label(win, text="Live Values:",
                bg=self.C["bg"], fg=self.C["dim"],
                font=self.F["small"]).pack(anchor="w", padx=16)
        vf = tk.Frame(win, bg=self.C["bg"])
        vf.pack(fill="x", padx=16)
        lbls = {}
        tags = status.get("process_tags", {})
        for i, (tag, val) in enumerate(list(tags.items())[:6]):
            rf = tk.Frame(vf, bg=self.C["panel"], padx=8, pady=3)
            rf.grid(row=i//2, column=i%2, padx=4, pady=2, sticky="ew")
            vf.grid_columnconfigure(i%2, weight=1)
            tk.Label(rf, text=tag, bg=self.C["panel"],
                    fg=self.C["dim"], font=self.F["small"]).pack(side="left")
            lbl = tk.Label(rf, text=str(val),
                          bg=self.C["panel"], fg=self.C["cyan"],
                          font=("Consolas",11,"bold"))
            lbl.pack(side="right")
            lbls[tag] = lbl
        def upd():
            if not win.winfo_exists(): return
            vals = self.twin.get_all_values()
            for t, l in lbls.items():
                v = vals.get(t)
                if v is not None:
                    l.config(text=f"{v:.1f}" if isinstance(v,float) else str(v))
            win.after(1000, upd)
        upd()

    def _maint_panel(self):
        win = tk.Toplevel(self.root)
        win.title("Predictive Maintenance")
        win.geometry("700x480")
        win.configure(bg=self.C["bg"])
        tk.Label(win, text=">> PREDICTIVE MAINTENANCE",
                bg=self.C["bg"], fg=self.C["cyan"],
                font=self.F["head"]).pack(anchor="w", padx=16, pady=12)
        health = self.pred_maint.get_health_report()
        cards  = tk.Frame(win, bg=self.C["bg"])
        cards.pack(fill="x", padx=16, pady=4)
        for eq in health:
            h = eq.get("health_score", 100)
            c = (self.C["green"] if h>80
                else self.C["warning"] if h>50
                else self.C["error"])
            card = tk.Frame(cards, bg=self.C["panel"],
                           highlightbackground=c,
                           highlightthickness=1, padx=8, pady=8)
            card.pack(side="left", padx=4, fill="x", expand=True)
            tk.Label(card, text=eq.get("name","?"),
                    bg=self.C["panel"], fg=c,
                    font=self.F["small"]).pack()
            tk.Label(card, text=f"{h:.0f}%",
                    bg=self.C["panel"], fg=c,
                    font=("Consolas",20,"bold")).pack()
        tk.Frame(win, bg=self.C["border"],
                height=1).pack(fill="x", padx=16, pady=8)
        tk.Button(win, text="AI Maintenance Analysis",
                 bg=self.C["cyan"], fg=self.C["bg"],
                 font=self.F["head"], relief="flat",
                 command=lambda: self._quick("maintenance report all equipment")
                 ).pack(padx=16, pady=8, ipadx=12, ipady=4)

    def _docs_panel(self):
        win = tk.Toplevel(self.root)
        win.title("Auto Documentation")
        win.geometry("600x420")
        win.configure(bg=self.C["bg"])
        tk.Label(win, text=">> AUTO DOCUMENTATION",
                bg=self.C["bg"], fg=self.C["cyan"],
                font=self.F["head"]).pack(anchor="w", padx=16, pady=12)
        docs = self.auto_doc.list_documents()
        tk.Label(win, text=f"Documents: {len(docs)}",
                bg=self.C["bg"], fg=self.C["dim"],
                font=self.F["small"]).pack(anchor="w", padx=16)
        tk.Frame(win, bg=self.C["border"],
                height=1).pack(fill="x", padx=16, pady=8)
        for d in docs[:10]:
            rf = tk.Frame(win, bg=self.C["panel"], pady=3)
            rf.pack(fill="x", padx=16, pady=2)
            tk.Label(rf, text=d["name"][:40],
                    bg=self.C["panel"], fg=self.C["white"],
                    font=self.F["small"], anchor="w",
                    width=40).pack(side="left", padx=6)
            tk.Button(rf, text="Open",
                     bg=self.C["cyan"], fg=self.C["bg"],
                     font=self.F["small"], relief="flat",
                     command=lambda p=d["path"]:
                     self.auto_doc.open_document(p)
                     ).pack(side="right", padx=6)

    def _scheduler_panel(self):
        win = tk.Toplevel(self.root)
        win.title("Task Scheduler")
        win.geometry("600x450")
        win.configure(bg=self.C["bg"])
        tk.Label(win, text=">> AUTO TASK SCHEDULER",
                bg=self.C["bg"], fg=self.C["cyan"],
                font=self.F["head"]).pack(anchor="w", padx=16, pady=12)
        lf = tk.Frame(win, bg=self.C["bg"])
        lf.pack(fill="both", expand=True, padx=16)

        def refresh():
            for w in lf.winfo_children(): w.destroy()
            for task in self.scheduler.get_tasks():
                rf = tk.Frame(lf, bg=self.C["panel"], pady=3)
                rf.pack(fill="x", pady=2)
                c = self.C["green"] if task.enabled else self.C["dim"]
                tk.Label(rf, text="*", bg=self.C["panel"],
                        fg=c, font=self.F["small"]).pack(side="left",padx=6)
                tk.Label(rf, text=f"{task.name[:30]}",
                        bg=self.C["panel"], fg=self.C["white"],
                        font=self.F["small"], width=30,
                        anchor="w").pack(side="left")
                tk.Label(rf, text=task.schedule,
                        bg=self.C["panel"], fg=self.C["dim"],
                        font=self.F["small"]).pack(side="left",padx=4)
                tk.Button(rf,
                         text="ON" if task.enabled else "OFF",
                         bg=self.C["button"], fg=self.C["white"],
                         font=self.F["small"], relief="flat",
                         command=lambda n=task.name,r=refresh:
                         [self.scheduler.toggle_task(n),r()]
                         ).pack(side="right",padx=4)
        refresh()

    # =========================================================
    # MINI MODE
    # =========================================================

    def _enter_mini(self):
        if self._minimized: return
        self._minimized = True
        self.root.withdraw()
        sw = self.root.winfo_screenwidth()
        self._mini_win = tk.Toplevel()
        self._mini_win.geometry(f"380x55+{sw-390}+8")
        self._mini_win.configure(bg=self.C["panel"])
        self._mini_win.attributes("-topmost", True)
        self._mini_win.overrideredirect(True)

        frame = tk.Frame(self._mini_win, bg=self.C["panel"],
                        highlightbackground=self.C["cyan"],
                        highlightthickness=1)
        frame.pack(fill="both", expand=True, padx=1, pady=1)

        tk.Label(frame, text="[GP]",
                bg=self.C["panel"], fg=self.C["cyan"],
                font=("Consolas",10,"bold")).pack(side="left", padx=6)

        self._mini_inp = tk.Entry(frame,
                                   bg=self.C["input_bg"],
                                   fg=self.C["white"],
                                   font=("Consolas",10),
                                   borderwidth=0,
                                   insertbackground=self.C["cyan"],
                                   width=24)
        self._mini_inp.pack(side="left", fill="x",
                            expand=True, pady=8, padx=2)
        self._mini_inp.bind("<Return>", self._mini_send)
        self._mini_inp.focus_set()

        tk.Button(frame, text=">",
                 bg=self.C["cyan"], fg=self.C["bg"],
                 font=("Consolas",10,"bold"),
                 relief="flat", width=2,
                 command=self._mini_send).pack(side="left", padx=2)
        tk.Button(frame, text="[+]",
                 bg=self.C["button"], fg=self.C["white"],
                 font=("Consolas",9),
                 relief="flat", width=3,
                 command=self._restore_mini).pack(side="left", padx=1)
        tk.Button(frame, text="X",
                 bg=self.C["error"], fg=self.C["white"],
                 font=("Consolas",9),
                 relief="flat", width=2,
                 command=self._close_mini).pack(side="left", padx=(1,3))

    def _mini_send(self, e=None):
        q = self._mini_inp.get().strip()
        if not q: return
        self._mini_inp.delete(0,"end")
        self._restore_mini()
        self.root.after(200, lambda: self._start(q))

    def _restore_mini(self):
        if not self._minimized: return
        self._minimized = False
        if self._mini_win:
            try: self._mini_win.destroy()
            except: pass
            self._mini_win = None
        self.root.deiconify()
        self.root.lift()

    def _close_mini(self):
        self._minimized = False
        if self._mini_win:
            try: self._mini_win.destroy()
            except: pass
            self._mini_win = None

    # =========================================================
    # DOWNLOAD MANAGER
    # =========================================================

    def _open_dl_manager(self):
        self._model_manager()

    # =========================================================
    # HELPERS
    # =========================================================

    def _welcome(self):
        self._msg("system",
            ">> GP PRO AGENT v4.0 - REAL AI Engine\n")
        self._msg("system",
            ">> Powered by Ollama - brains actually work!\n")
        self._msg("system",
            ">> Install: ollama.com | Run: ollama pull phi3\n\n")

    def _startup_check(self):
        time.sleep(2)
        status = self.ai.get_status()
        if status["available"]:
            models = ", ".join(status["models"])
            self._msg_system(
                f"[AI] Ollama online! Models: {models}\n"
                f"Real AI responses active!")
            self.root.after(0, self.ai_lbl.config,
                {"text": f"AI: ONLINE ({', '.join(status['models'][:2])})",
                 "fg": self.C["green"]})
        else:
            self._msg_system(
                "[AI] Ollama offline. Install from ollama.com\n"
                "Run: ollama pull phi3")
            self.root.after(0, self.ai_lbl.config,
                {"text": "AI: OFFLINE - Install Ollama",
                 "fg": self.C["error"]})
        self._refresh_dots()
        stats = self.memory.get_stats()
        self.root.after(0, self.mem_lbl.config,
            {"text": f"Entries: {stats['total']}"})

    def _msg(self, tag: str, text: str):
        def _d():
            safe = text.encode('ascii','replace').decode('ascii')
            self.chat.config(state="normal")
            self.chat.insert("end", safe, tag)
            self.chat.see("end")
            self.chat.config(state="disabled")
        self.root.after(0, _d)

    def _msg_system(self, text: str):
        self._msg("system", f"{text}\n")

    def _done(self, msg: str):
        self._busy = False
        self.root.after(0, self.send_btn.config,
            {"state": "normal", "text": "> SEND"})
        self.root.after(0, self.cancel_btn.config,
            {"state": "disabled"})
        safe = msg.encode('ascii','replace').decode('ascii')
        self.root.after(0, self.status_bar.config,
            {"text": safe, "fg": self.C["green"]})

    def _dot(self, key: str, color: str):
        if key in self.dots:
            self.dots[key].config(fg=color)

    def _all_dots(self, color: str):
        for d in self.dots.values():
            d.config(fg=color)

    def _refresh_dots(self):
        for key in MODELS:
            ollama_m = BRAIN_MODELS.get(key,"phi3")
            if ollama_m in self.ai._models:
                self.dots[key].config(fg=self.C["green"], text="*")
            else:
                self.dots[key].config(fg=self.C["dim"], text="o")

    def _upd_active(self, key: str):
        m = MODELS.get(key, {})
        ollama_m = BRAIN_MODELS.get(key,"phi3")
        self.active_lbl.config(
            text=f"{m.get('name','?')}\n"
                 f"Model: {ollama_m}\n"
                 f"Acc: {m.get('accuracy')}%")
        self.brain_lbl.config(
            text=f"Brain: {key} ({ollama_m})")

    def _clear(self):
        self.chat.config(state="normal")
        self.chat.delete("1.0","end")
        self.chat.config(state="disabled")
        self._msg("system","Chat cleared.\n")

    def _quick(self, cmd: str):
        self.inp.delete("1.0","end")
        self.inp.insert("1.0", cmd)
        self._send()

    def _auto_execute(self, query: str):
        """Called by scheduler/autonomous agent."""
        self._msg("system", f"[AUTO] {query[:50]}\n")
        if not self._busy:
            self._start(query)

    def _upd_ram(self):
        try:
            import psutil
            mb = psutil.Process(os.getpid()).memory_info().rss/(1024**2)
            c  = self.C["green"] if mb<500 else self.C["warning"]
            self.ram_lbl.config(text=f"RAM:{mb:.0f}MB", fg=c)
        except Exception:
            pass
        self.root.after(3000, self._upd_ram)

    def run(self):
        self._upd_ram()
        self.root.mainloop()

    def _features_panel(self):
        """Show 20 features panel."""
        win = tk.Toplevel(self.root)
        win.title("20 AI Features")
        win.geometry("700x560")
        win.configure(bg=self.C["bg"])
        tk.Label(win, text=">> 20 AI-POWERED FEATURES",
                bg=self.C["bg"], fg=self.C["cyan"],
                font=self.F["head"]).pack(anchor="w",
                padx=16, pady=(12,4))
        tk.Label(win,
                text="All features use real Ollama AI. Just type naturally!",
                bg=self.C["bg"], fg=self.C["dim"],
                font=self.F["small"]).pack(anchor="w", padx=16)
        tk.Frame(win, bg=self.C["border"],
                height=1).pack(fill="x", padx=16, pady=8)

        canvas = tk.Canvas(win, bg=self.C["bg"],
                          highlightthickness=0)
        sb = ttk.Scrollbar(win, orient="vertical",
                          command=canvas.yview)
        frame = tk.Frame(canvas, bg=self.C["bg"])
        canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side="left", fill="both",
                   expand=True, padx=(16,0))
        sb.pack(side="right", fill="y", padx=(0,8))
        cw = canvas.create_window((0,0), window=frame, anchor="nw")
        frame.bind("<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>",
            lambda e: canvas.itemconfig(cw, width=e.width))

        features = self.features.get_feature_list()
        colors = [self.C["cyan"], self.C["green"],
                 self.C["orange"], self.C["purple"],
                 self.C["warning"]]

        for i, feat in enumerate(features):
            rf = tk.Frame(frame, bg=self.C["panel"], pady=5)
            rf.pack(fill="x", pady=2)
            c = colors[i % len(colors)]
            tk.Label(rf, text=f"{feat['id']:02d}",
                    bg=self.C["panel"], fg=c,
                    font=("Consolas",11,"bold"),
                    width=4).pack(side="left", padx=6)
            tk.Label(rf, text=feat["name"],
                    bg=self.C["panel"], fg=self.C["white"],
                    font=self.F["small"],
                    width=18, anchor="w").pack(side="left")
            tk.Label(rf, text=f'Say: "{feat["trigger"]}"',
                    bg=self.C["panel"], fg=self.C["dim"],
                    font=self.F["small"],
                    anchor="w").pack(side="left", padx=8,
                                    fill="x", expand=True)
            tk.Button(rf, text="Try",
                     bg=c, fg=self.C["bg"],
                     font=self.F["small"],
                     relief="flat", cursor="hand2",
                     command=lambda t=feat["trigger"],w=win:
                     [self._quick(t), w.destroy()]
                     ).pack(side="right", padx=6)
