import tkinter as tk
from tkinter import ttk, scrolledtext
import threading, time, sys, os, json, gc, subprocess, shutil, re
from pathlib import Path

BASE = Path(__file__).parent.parent
sys.path.insert(0, str(BASE))

from config.settings import Settings
from config.models   import MODELS, CHAT_MODELS
from modules.voice         import VoiceEngine
from modules.vision        import ScreenVision
from modules.memory_db     import MemoryDB
from modules.plc_controller import PLCController
from modules.dashboard     import LiveDashboard
from modules.scheduler     import TaskScheduler

SYSTEM_PROMPTS = {
    "master":  "You are GP PRO AGENT, a senior engineering AI. Answer clearly and professionally.",
    "reflex":  "You are GP PRO AGENT. Give short, direct, accurate answers. Be friendly.",
    "plc":     "You are GP PRO AGENT, a PLC and industrial automation expert. Allen Bradley Studio 5000, Siemens TIA Portal, ladder logic, SCADA, Modbus, Profibus. Give expert answers.",
    "coder":   "You are GP PRO AGENT, an expert programmer. Write clean efficient well-commented code.",
    "screen":  "You are GP PRO AGENT, a GUI automation expert. Give precise step-by-step automation with pyautogui code.",
    "safety":  "You are GP PRO AGENT, an industrial safety engineer. Prioritize safety above everything.",
    "docs":    "You are GP PRO AGENT, a technical writer. Write clear professional structured documents.",
    "learner": "You are GP PRO AGENT, a software operation expert. Give clear step-by-step instructions.",
    "ocr":     "You are GP PRO AGENT, a vision and screen reading expert. Help analyze screen content.",
    "math":    "You are GP PRO AGENT, an engineering calculator. Solve problems precisely with all steps.",
}

SW_MAP = {
    "notepad":("notepad.exe","Notepad"),
    "calculator":("calc.exe","Calculator"),
    "paint":("mspaint.exe","Paint"),
    "explorer":("explorer.exe","File Explorer"),
    "file explorer":("explorer.exe","File Explorer"),
    "task manager":("taskmgr.exe","Task Manager"),
    "cmd":("cmd.exe","Command Prompt"),
    "command prompt":("cmd.exe","Command Prompt"),
    "control panel":("control.exe","Control Panel"),
    "word":("winword.exe","Microsoft Word"),
    "excel":("excel.exe","Microsoft Excel"),
    "chrome":("chrome.exe","Google Chrome"),
    "firefox":("firefox.exe","Firefox"),
    "edge":("msedge.exe","Microsoft Edge"),
    "vs code":("code.exe","VS Code"),
    "vscode":("code.exe","VS Code"),
    "pcwin":("PCWin.exe","PCWin"),
    "rslogix":("Studio5000Launcher.exe","Studio 5000"),
    "studio 5000":("Studio5000Launcher.exe","Studio 5000"),
    "tia portal":("TIA Portal.exe","TIA Portal"),
}

class MainWindow:
    def __init__(self):
        self.settings = Settings()
        self.settings.ensure_dirs()
        self._busy      = False
        self._cancel    = threading.Event()
        self._qcount    = 0
        self._ttime     = 0.0
        self._llm       = None
        self._llm_key   = None
        self._minimized = False
        self._dl_win    = None
        self._mini_win  = None
        self._voice_on  = False

        self.C = {
            "bg":"#0a0f1a","panel":"#0d1526","border":"#1a3a5c",
            "cyan":self.settings.ui.get("accent_color","#00e5ff"),
            "green":"#00ff88","orange":"#ff6b2b","purple":"#bf5fff",
            "white":"#d0e8ff","dim":"#3a5a7a","input_bg":"#071020",
            "button":"#0a2a4a","error":"#ff4444","warning":"#ffaa00",
        }
        self.F = {
            "title":("Consolas",16,"bold"),
            "head": ("Consolas",11,"bold"),
            "body": ("Consolas",self.settings.ui.get("font_size",10)),
            "small":("Consolas",9),
            "input":("Consolas",11),
        }

        # ── Init all 6 modules ────────────────────────────────
        self.memory    = MemoryDB(self.settings.brain_root)
        self.vision    = ScreenVision(self.settings.cache_path)
        self.plc       = PLCController(self.vision)
        self._setup_root()
        self.dashboard = LiveDashboard(
            self.root, self.C, self.F, self.settings)
        self.scheduler = TaskScheduler(
            str(self.settings.brain_root),
            self._scheduled_execute)
        self.voice     = VoiceEngine(self._voice_input_received)
        self.codegen   = CodeGenerator(str(self.settings.brain_root))
        self.files     = SmartFileManager(str(self.settings.brain_root))
        self.tag_mon   = TagMonitor(str(self.settings.brain_root), self.C, self.F)
        self.alerts    = AlertSystem(str(self.settings.brain_root), self.C, self.F, self._notify_from_alert)
        self.web       = WebServer(self._web_query_handler, port=5000)
        self.auto_agent = AutonomousAgent(
            str(self.settings.brain_root),
            self._scheduled_execute,
            self._msg_from_agent)
        self.cv_ai      = ComputerVisionAI(str(self.settings.cache_path))
        self.plc_hw     = PLCDirectConnection(str(self.settings.brain_root))
        self.team       = MultiAgentTeam(
            str(self.settings.brain_root),
            self._ask, self._msg_from_agent)
        # cloud already init above

        self._build_ui()
        self.scheduler.start()
        self.web.start()
        self.alerts.start_monitoring()
        self.auto_agent.start()
        self.team.start()
        self.cloud.start()
        self.healer.start()
        self.pred_maint.start_monitoring()
        self.twin.start()

    def _setup_root(self):
        self.root = tk.Tk()
        self.root.title("GP PRO AGENT v2.0")
        self.root.geometry("1300x880")
        self.root.minsize(1000,650)
        self.root.configure(bg=self.C["bg"])
        self.root.grid_rowconfigure(0,weight=1)
        self.root.grid_columnconfigure(0,weight=1)
        sw=self.root.winfo_screenwidth()
        sh=self.root.winfo_screenheight()
        self.root.geometry(f"1300x880+{(sw-1300)//2}+{(sh-880)//2}")

    def _build_ui(self):
        self._main = tk.Frame(self.root, bg=self.C["bg"])
        self._main.grid(row=0,column=0,sticky="nsew",padx=8,pady=8)
        self._main.grid_rowconfigure(1,weight=1)
        self._main.grid_columnconfigure(0,weight=3)
        self._main.grid_columnconfigure(1,weight=1)
        self._build_header()
        self._build_chat()
        self._build_sidebar()
        self._build_input()
        self._msg("system",">> GP PRO AGENT v2.0 — All 6 Modules Online\n")
        self._msg("system",">> Voice | Vision | Memory | PLC Control | Dashboard | Scheduler\n")
        self._msg("system",">> Say anything — I use the right brain automatically\n\n")
        threading.Thread(target=self._startup,daemon=True).start()

    def _build_header(self):
        h=tk.Frame(self._main,bg=self.C["panel"],
                   highlightbackground=self.C["border"],highlightthickness=1)
        h.grid(row=0,column=0,columnspan=2,sticky="ew",pady=(0,4))
        h.grid_columnconfigure(2,weight=1)
        tk.Label(h,text="[GP] GP PRO AGENT",bg=self.C["panel"],
                 fg=self.C["cyan"],font=self.F["title"]).grid(
                 row=0,column=0,padx=16,pady=8)
        tk.Label(h,text="Real AI | PLC | GUI | Vision | Voice | Memory | Auto-Schedule",
                 bg=self.C["panel"],fg=self.C["dim"],
                 font=self.F["small"]).grid(row=0,column=1,padx=4,sticky="w")
        tk.Frame(h,bg=self.C["panel"]).grid(row=0,column=2,sticky="ew")
        self.ram_lbl=tk.Label(h,text="RAM:--",bg=self.C["panel"],
                               fg=self.C["green"],font=self.F["small"])
        self.ram_lbl.grid(row=0,column=3,padx=4)
        self.priority=tk.StringVar(value="balanced")
        pf=tk.Frame(h,bg=self.C["panel"])
        pf.grid(row=0,column=4,padx=6)
        for v,l in [("speed","[FAST]"),("balanced","[BAL]"),("accuracy","[ACC]")]:
            tk.Radiobutton(pf,text=l,variable=self.priority,value=v,
                          bg=self.C["panel"],fg=self.C["white"],
                          selectcolor=self.C["button"],
                          activebackground=self.C["panel"],
                          font=self.F["small"]).pack(side="left",padx=1)
        # All 6 module buttons
        btns=[
            ("[MIC] Voice",   self._toggle_voice,   self.C["button"]),
            ("[EYE] Vision",  self._vision_action,   self.C["button"]),
            ("[DASH] Dash",    self.dashboard.toggle, self.C["button"]),
            ("[PLC] PLC",     self._plc_panel,       self.C["button"]),
            ("[TIME] Schedule",self._scheduler_panel, self.C["button"]),
            ("[-] Mini",     self._enter_mini_mode, self.C["button"]),
            ("[WEB] Web",      self._show_web_info,   self.C["button"]),
            ("[CODE] CodeGen",  self._codegen_panel,   self.C["button"]),
            ("[TAG] Tags",     self._open_tag_monitor,self.C["button"]),
            ("[FILE] Files",    self._files_panel,     self.C["button"]),
            ("[ALERT] Alerts",   self._open_alerts,     self.C["button"]),
            ("[v] Models",   self._open_dl_manager, self.C["button"]),
        ]
        for i,(txt,cmd,bg) in enumerate(btns):
            tk.Button(h,text=txt,bg=bg,fg=self.C["white"],
                     font=("Consolas",8),relief="flat",cursor="hand2",
                     command=cmd).grid(row=0,column=5+i,padx=2)
        self.voice_lbl=tk.Label(h,text="[MIC] OFF",bg=self.C["panel"],
                                 fg=self.C["dim"],font=self.F["small"])
        self.voice_lbl.grid(row=0,column=12,padx=4)

    def _build_chat(self):
        f=tk.Frame(self._main,bg=self.C["panel"],
                   highlightbackground=self.C["border"],highlightthickness=1)
        f.grid(row=1,column=0,sticky="nsew",padx=(0,4),pady=4)
        f.grid_rowconfigure(1,weight=1)
        f.grid_columnconfigure(0,weight=1)
        tk.Label(f,text=">> CONVERSATION",bg=self.C["panel"],
                 fg=self.C["cyan"],font=self.F["head"]).grid(
                 row=0,column=0,sticky="w",padx=12,pady=6)
        self.chat=scrolledtext.ScrolledText(
            f,bg=self.C["input_bg"],fg=self.C["white"],
            font=self.F["body"],wrap=tk.WORD,state="disabled",
            borderwidth=0,highlightthickness=0,padx=14,pady=10)
        self.chat.grid(row=1,column=0,sticky="nsew",padx=8,pady=(0,8))
        for tag,color,bold in [
            ("user",  self.C["cyan"],  True),
            ("agent", self.C["green"], False),
            ("model", self.C["orange"],False),
            ("system",self.C["dim"],   False),
            ("error", self.C["error"], False),
            ("ui_msg",self.C["purple"],False),
            ("action",self.C["warning"],False),
            ("memory",self.C["cyan"],False),
        ]:
            font=("Consolas",10,"bold") if bold else self.F["body"]
            self.chat.tag_config(tag,foreground=color,font=font)

    def _build_sidebar(self):
        f=tk.Frame(self._main,bg=self.C["panel"],
                   highlightbackground=self.C["border"],highlightthickness=1)
        f.grid(row=1,column=1,sticky="nsew",padx=(4,0),pady=4)
        f.grid_columnconfigure(0,weight=1)
        tk.Label(f,text=">> BRAIN STATUS",bg=self.C["panel"],
                 fg=self.C["cyan"],font=self.F["head"]).grid(
                 row=0,column=0,sticky="w",padx=12,pady=6)
        canvas=tk.Canvas(f,bg=self.C["panel"],
                         highlightthickness=0,height=200)
        sb=ttk.Scrollbar(f,orient="vertical",command=canvas.yview)
        mf=tk.Frame(canvas,bg=self.C["panel"])
        canvas.configure(yscrollcommand=sb.set)
        canvas.grid(row=1,column=0,sticky="nsew",padx=4)
        sb.grid(row=1,column=1,sticky="ns")
        f.grid_rowconfigure(1,weight=1)
        cw=canvas.create_window((0,0),window=mf,anchor="nw")
        mf.bind("<Configure>",lambda e:canvas.configure(
            scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>",lambda e:canvas.itemconfig(
            cw,width=e.width))
        self.dots={}
        for key,model in MODELS.items():
            row=tk.Frame(mf,bg=self.C["panel"],pady=1)
            row.pack(fill="x",padx=6)
            dot=tk.Label(row,text="●",bg=self.C["panel"],
                         fg=self.C["dim"],font=self.F["small"])
            dot.pack(side="left")
            tk.Label(row,text=f"[{key}]",bg=self.C["panel"],
                     fg=self.C["orange"],font=self.F["small"],
                     width=8,anchor="w").pack(side="left")
            tk.Label(row,text=f"{model['speed_s']}s",
                     bg=self.C["panel"],fg=self.C["dim"],
                     font=self.F["small"]).pack(side="right")
            self.dots[key]=dot
        self._refresh_dots()

        def sep(r):
            tk.Frame(f,bg=self.C["border"],height=1).grid(
                row=r,column=0,columnspan=2,sticky="ew",padx=8,pady=3)
        sep(2)
        tk.Label(f,text=">> ACTIVE BRAIN",bg=self.C["panel"],
                 fg=self.C["cyan"],font=self.F["head"]).grid(
                 row=3,column=0,sticky="w",padx=12,pady=(4,2))
        self.active_lbl=tk.Label(f,text="Waiting...",bg=self.C["panel"],
                                  fg=self.C["orange"],font=self.F["small"],
                                  justify="left",wraplength=195)
        self.active_lbl.grid(row=4,column=0,sticky="w",padx=12,pady=2)
        sep(5)
        tk.Label(f,text=">> MEMORY",bg=self.C["panel"],
                 fg=self.C["cyan"],font=self.F["head"]).grid(
                 row=6,column=0,sticky="w",padx=12,pady=(4,2))
        self.mem_lbl=tk.Label(f,text="Entries: 0",bg=self.C["panel"],
                               fg=self.C["white"],font=self.F["small"],
                               justify="left")
        self.mem_lbl.grid(row=7,column=0,sticky="w",padx=12,pady=2)
        sep(8)
        tk.Label(f,text=">> SESSION",bg=self.C["panel"],
                 fg=self.C["cyan"],font=self.F["head"]).grid(
                 row=9,column=0,sticky="w",padx=12,pady=(4,2))
        self.stats_lbl=tk.Label(
            f,text="Queries : 0\nAvg time: --\nLast    : --",
            bg=self.C["panel"],fg=self.C["white"],
            font=self.F["small"],justify="left")
        self.stats_lbl.grid(row=10,column=0,sticky="w",padx=12,pady=2)
        sep(11)
        tk.Label(f,text=">> QUICK",bg=self.C["panel"],
                 fg=self.C["cyan"],font=self.F["head"]).grid(
                 row=12,column=0,sticky="w",padx=12,pady=(4,2))
        for i,(lbl,cmd) in enumerate([
            ("PLC Ladder Logic","Explain PLC ladder logic all elements"),
            ("Safety SIL LOTO", "Explain industrial safety SIL LOTO estop"),
            ("GUI Automation",  "How to automate GUI pyautogui examples"),
            ("Python Script",   "Write Python automation script example"),
            ("Open Notepad",    "Open Notepad"),
            ("Take Screenshot", "Take a screenshot of my screen"),
            ("What's on screen","What text is visible on my screen right now"),
        ]):
            tk.Button(f,text=lbl,bg=self.C["button"],fg=self.C["white"],
                      font=self.F["small"],relief="flat",cursor="hand2",
                      command=lambda c=cmd:self._quick(c)).grid(
                      row=13+i,column=0,sticky="ew",padx=12,pady=1)

    def _build_input(self):
        f=tk.Frame(self._main,bg=self.C["panel"],
                   highlightbackground=self.C["border"],highlightthickness=1)
        f.grid(row=2,column=0,columnspan=2,sticky="ew",pady=(4,0))
        f.grid_columnconfigure(0,weight=1)
        self.hint_lbl=tk.Label(
            f,text="Ask anything — right brain selected automatically | [MIC] Voice | [EYE] Vision | [PLC] PLC | [TIME] Auto",
            bg=self.C["panel"],fg=self.C["dim"],
            font=self.F["small"],anchor="w")
        self.hint_lbl.grid(row=0,column=0,columnspan=2,
                            sticky="ew",padx=12,pady=(6,2))
        inf=tk.Frame(f,bg=self.C["panel"])
        inf.grid(row=1,column=0,columnspan=2,
                 sticky="ew",padx=8,pady=(0,6))
        inf.grid_columnconfigure(0,weight=1)
        self.inp=tk.Text(
            inf,bg=self.C["input_bg"],fg=self.C["white"],
            font=self.F["input"],height=3,wrap=tk.WORD,
            insertbackground=self.C["cyan"],borderwidth=0,
            highlightthickness=1,highlightcolor=self.C["cyan"],
            highlightbackground=self.C["border"],padx=10,pady=8)
        self.inp.grid(row=0,column=0,sticky="ew",padx=(0,8))
        self.inp.bind("<Return>",self._on_enter)
        bf=tk.Frame(inf,bg=self.C["panel"])
        bf.grid(row=0,column=1)
        self.send_btn=tk.Button(bf,text="> SEND",
                                 bg=self.C["cyan"],fg=self.C["bg"],
                                 font=self.F["head"],width=10,
                                 relief="flat",cursor="hand2",
                                 command=self._send)
        self.send_btn.pack(pady=(0,3))
        self.cancel_btn=tk.Button(bf,text="X CANCEL",
                                   bg=self.C["error"],fg=self.C["white"],
                                   font=self.F["small"],width=10,
                                   relief="flat",cursor="hand2",
                                   command=self._cancel_request,
                                   state="disabled")
        self.cancel_btn.pack(pady=(0,3))
        tk.Button(bf,text="[X] CLEAR",bg=self.C["button"],fg=self.C["white"],
                  font=self.F["small"],width=10,relief="flat",cursor="hand2",
                  command=self._clear).pack()
        self.status_bar=tk.Label(f,text="Ready — GP PRO AGENT v2.0 Online",
                                  bg=self.C["panel"],fg=self.C["dim"],
                                  font=self.F["small"],anchor="w")
        self.status_bar.grid(row=2,column=0,columnspan=2,
                              sticky="ew",padx=12,pady=(0,4))

    # ══════════════════════════════════════════════════════════
    # CORE PROCESSING
    # ══════════════════════════════════════════════════════════

    def _on_enter(self,e):
        if not(e.state&0x1):
            self._send()
            return "break"

    def _send(self):
        if self._busy: return
        q=self.inp.get("1.0","end-1c").strip()
        if not q: return
        self.inp.delete("1.0","end")
        self._start_processing(q)

    def _start_processing(self, query):
        self._busy=True
        self._cancel.clear()
        self.send_btn.config(state="disabled",text="......")
        self.cancel_btn.config(state="normal")
        self.status_bar.config(text="Processing...",
                               fg=self.C["warning"])
        threading.Thread(target=self._process,
                        args=(query,),daemon=True).start()

    def _cancel_request(self):
        self._cancel.set()
        if self._llm:
            try:
                del self._llm
                self._llm=None
                self._llm_key=None
                gc.collect()
            except: pass
        self._msg("system","[X Cancelled]\n\n")
        self._done_busy("Cancelled.")

    def _process(self, query):
        self._msg("user",f"You: {query}\n")
        # Record for autonomous learning
        self.auto_agent.record_activity(query)
        self._all_dots(self.C["dim"])
        q=query.lower().strip()

        try:
            # ── Check memory first ──────────────────────────
            cached=self.memory.recall(query, threshold=0.80)
            if cached and not any(w in q for w in
                ["open","screenshot","screen","what is on"]):
                self._msg("memory",
                    f"[MEMORY RECALL | {cached['brain']} brain | used {cached['uses']}x]\n")
                self._msg("agent",f"{cached['answer']}\n\n")
                self.memory.remember(query, cached["answer"],
                                    cached["brain"])
                self._done_busy("Answer from memory (instant!)")
                return

            # ── UI modification ──────────────────────────────
            if self._is_ui_cmd(q):
                self._handle_ui(query)
                return

            # ── PLC software commands ────────────────────────
            if any(w in q for w in ["studio 5000","tia portal","pcwin",
                                     "rslogix","open plc","ladder rung",
                                     "go online","download program",
                                     "plc software"]):
                self._handle_plc_cmd(query)
                return

            # ── Vision / screen commands ─────────────────────
            if any(w in q for w in ["what is on screen","what's on screen",
                                     "read screen","describe screen",
                                     "what do you see"]):
                self._handle_vision_cmd(query)
                return

            # ── Screenshot ───────────────────────────────────
            if any(w in q for w in ["screenshot","take screenshot",
                                     "capture screen"]):
                self._handle_screenshot()
                return

            # ── Open software ────────────────────────────────
            if any(q.startswith(w) for w in
                   ["open ","launch ","start ","run "]):
                self._handle_open(query)
                return

            # ── Math calculation ─────────────────────────────
            if re.search(r'\d+\s*[\+\-\*\/\%]\s*\d+',q):
                self._handle_math(query)
                return

            # ── Multi-step detection ─────────────────────────
            steps=self._parse_steps(query)
            if steps and len(steps)>1:
                self._run_multistep(steps)
                return

            # ── Normal AI query ──────────────────────────────
            if self._cancel.is_set(): return
            brain=self._route(q)
            self._run_brain(brain, query)

        except Exception as e:
            self._msg("error",f"Error: {e}\n\n")
            self._done_busy(f"Error: {e}")

    def _route(self, query):
        """Route to best CHAT brain by trigger match score."""
        q=query.lower()
        scores={}
        pri=self.priority.get()
        for key,model in CHAT_MODELS.items():
            score=0.0
            for t in model.get("triggers",[]):
                if t in q:
                    score += len(t.split())*12  # longer=more specific
            score += (model["accuracy"]/100)*15
            if pri=="speed":
                score += (1/max(model["speed_s"],0.1))*25
            elif pri=="accuracy":
                score += (model["accuracy"]/100)*25
            else:
                score += (1/max(model["speed_s"],0.1))*8
            dest=self.settings.model_path/model["file"]
            if not dest.exists():
                score *= 0.4
            scores[key]=score
        ranked=sorted(scores.items(),key=lambda x:x[1],reverse=True)
        best=ranked[0][0]
        print(f"[ROUTE] '{q[:25]}' -> {best} | scores: "
              f"{[(k,round(v,1)) for k,v in ranked[:3]]}")
        return best

    def _run_brain(self, brain, query):
        model=MODELS[brain]
        start=time.time()
        self.root.after(0,self._upd_active,brain)
        self.root.after(0,self._dot,brain,self.C["warning"])
        self._msg("model",
            f"[{brain.upper()} BRAIN | {model['accuracy']}% | {model['speed_s']}s est.]\n")
        self.root.after(0,self.status_bar.config,
            {"text":f"Thinking with {brain} brain...","fg":self.C["warning"]})

        if self._cancel.is_set(): return

        answer=self._ask(brain,query)
        if self._cancel.is_set(): return

        dur=round(time.time()-start,2)
        self.root.after(0,self._dot,brain,self.C["green"])
        self._msg("agent",f"{answer}\n\n")

        # Save to memory
        self.memory.remember(query, answer, brain, True)
        # Update knowledge graph
        self.graph.learn_from_query(query, brain, [brain])
        # Update dashboard
        self.dashboard.record_query(brain, dur)
        # Speak if voice on
        if self._voice_on:
            self.voice.speak(answer)
        # Update memory label
        stats=self.memory.get_stats()
        self.root.after(0,self.mem_lbl.config,
            {"text":f"Entries: {stats['total']}"})

        self._update_stats(dur, brain)
        self._done_busy(f"Done {dur}s | {brain} brain")

    def _run_multistep(self, steps):
        self._msg("action",f"[MULTI-BRAIN | {len(steps)} steps]\n")
        for i,step in enumerate(steps):
            if self._cancel.is_set(): break
            brain=self._route(step.lower())
            self._msg("action",f"Step {i+1}: {step}\n-> [{brain.upper()}]\n")
            self.root.after(0,self._dot,brain,self.C["warning"])
            answer=self._ask(brain,step)
            self.root.after(0,self._dot,brain,self.C["green"])
            self._msg("agent",f"{answer}\n")
            self.memory.remember(step,answer,brain)
            time.sleep(0.5)
        self._msg("system","\n")
        self._done_busy("Multi-step complete!")

    def _parse_steps(self,query):
        q=query.lower()
        parts=[]
        if " and then " in q:
            parts=query.split(" and then ")
        elif re.search(r'open \w+ and (write|type) .+',q):
            m=re.match(r'(open \w+)\s+and\s+(write|type)\s+(.+)',q,re.I)
            if m:
                parts=[m.group(1),
                       f"{m.group(2)} '{m.group(3)}'"]
        elif " then " in q:
            parts=query.split(" then ")
        return [p.strip() for p in parts if p.strip()] \
               if len(parts)>1 else []

    # ══════════════════════════════════════════════════════════
    # LLM INFERENCE
    # ══════════════════════════════════════════════════════════

    def _ask(self, brain, query):
        model=MODELS[brain]
        dest=self.settings.model_path/model["file"]
        if dest.exists():
            try:
                return self._llm_infer(brain,str(dest),query)
            except Exception as e:
                print(f"[LLM] {e}")
        return self._domain_answer(brain,query)

    def _llm_infer(self, brain, model_path, query):
        from llama_cpp import Llama
        if self._llm_key!=brain:
            if self._llm:
                del self._llm; gc.collect()
            self.root.after(0,self.status_bar.config,
                {"text":f"Loading {MODELS[brain]['name']}...",
                 "fg":self.C["warning"]})
            self._llm=Llama(
                model_path=model_path, n_ctx=2048,
                n_threads=self.settings.cpu_threads,
                n_gpu_layers=0, verbose=False, use_mmap=True)
            self._llm_key=brain
        sys_p=SYSTEM_PROMPTS.get(brain,SYSTEM_PROMPTS["master"])
        prompt=(f"<|system|>\n{sys_p}\n<|end|>\n"
                f"<|user|>\n{query}\n<|end|>\n"
                f"<|assistant|>\n")
        resp=self._llm(prompt,max_tokens=768,temperature=0.15,
                       top_p=0.9,
                       stop=["<|end|>","<|user|>","<|system|>"],
                       echo=False)
        text=resp["choices"][0]["text"].strip()
        return text if len(text)>5 else self._domain_answer(brain,query)

    # ══════════════════════════════════════════════════════════
    # DOMAIN ANSWERS — AI context-aware, not fixed strings
    # ══════════════════════════════════════════════════════════

    def _domain_answer(self, brain, query):
        q=query.lower()
        if brain in ("master","reflex"):
            return self._general_answer(query)
        if brain=="plc":     return self._plc_domain(q)
        if brain=="safety":  return self._safety_domain(q)
        if brain=="coder":   return self._code_domain(q)
        if brain=="screen":  return self._screen_domain(q)
        if brain=="docs":    return self._docs_domain(q)
        if brain=="learner": return self._learner_domain(query)
        if brain=="math":    return self._math_domain(query)
        if brain=="ocr":     return self._ocr_domain(q)
        return self._general_answer(query)

    def _general_answer(self,q):
        ql=q.lower()
        if any(w in ql for w in ["hello","hi","hey"]):
            return ("Hello! I am GP PRO AGENT v2.0\n\n"
                    "I have 11 specialist AI brains:\n"
                    "- PLC & Industrial Automation\n"
                    "- GUI & Screen Automation\n"
                    "- Real Screen Vision (OCR)\n"
                    "- Voice Control\n"
                    "- Software Learning & Operation\n"
                    "- Engineering Math\n"
                    "- Safety Systems\n"
                    "- Python Code Writing\n"
                    "- Memory (remembers everything)\n"
                    "- Auto Task Scheduler\n"
                    "- Live Dashboard\n\nAsk me anything!")
        if "who are you" in ql or "what are you" in ql:
            return ("I am GP PRO AGENT — Professional AI System\n\n"
                    "Built with 11 specialist AI brains.\n"
                    "I route every question to the best brain automatically.\n"
                    "I remember everything you ask.\n"
                    "I can see your screen, speak, and control software.\n\n"
                    "Created by IHTM Department.")
        return (f"I understood: '{q}'\n\n"
                "For full AI responses, download the brain models.\n"
                "Click '[v] Models' button. Currently using expert knowledge.\n"
                "Ask me about PLC, safety, code, math, GUI automation!")

    def _plc_domain(self,q):
        if any(w in q for w in ["ladder","element","basic","explain","what is"]):
            return ("PLC LADDER LOGIC — Complete Reference:\n\n"
                    "CONTACTS:\n"
                    "XIC — Examine If Closed (NO) — passes when bit=1\n"
                    "XIO — Examine If Open (NC)  — passes when bit=0\n\n"
                    "OUTPUTS:\n"
                    "OTE — Output Energize (Coil)  — sets bit when rung energized\n"
                    "OTL — Output Latch            — latches ON permanently\n"
                    "OTU — Output Unlatch          — releases latch\n\n"
                    "TIMERS:\n"
                    "TON — On-Delay:  starts timing when rung=TRUE\n"
                    "TOF — Off-Delay: starts timing when rung=FALSE\n"
                    "RTO — Retentive: holds value on power loss\n"
                    "PARAMETERS: Preset (PT), Accumulated (AC), EN, DN, TT\n\n"
                    "COUNTERS:\n"
                    "CTU — Count Up   | CTD — Count Down | RES — Reset\n\n"
                    "MATH: ADD SUB MUL DIV MOD SQR ABS NEG\n"
                    "COMPARE: EQU NEQ GRT LES GEQ LEQ\n"
                    "DATA: MOV COP FLL CLR\n\n"
                    "BRANDS: Allen Bradley->Studio 5000 | Siemens->TIA Portal\n"
                    "NETWORKS: Modbus TCP | Profibus | EtherNet/IP | OPC-UA")
        if "modbus" in q:
            return ("MODBUS PROTOCOL GUIDE:\n\n"
                    "RTU vs TCP:\n"
                    "- RTU — RS-485 serial, CRC check, compact\n"
                    "- TCP — Ethernet port 502, easier setup\n\n"
                    "Function Codes:\n"
                    "FC01 — Read Coils\nFC02 — Read Discrete Inputs\n"
                    "FC03 — Read Holding Registers\nFC04 — Read Input Registers\n"
                    "FC05 — Write Single Coil\nFC06 — Write Single Register\n"
                    "FC15 — Write Multiple Coils\nFC16 — Write Multiple Registers\n\n"
                    "Address Map: 00001+ Coils | 10001+ Inputs | 30001+ Input Reg | 40001+ Holding Reg")
        if "siemens" in q or "s7" in q or "tia" in q:
            return ("SIEMENS S7 / TIA PORTAL:\n\n"
                    "Series: S7-300 | S7-400 | S7-1200 | S7-1500\n\n"
                    "Block Types:\n"
                    "OB — Organization Block (called by OS)\n"
                    "FB — Function Block (with Instance DB)\n"
                    "FC — Function (no memory)\n"
                    "DB — Data Block (global/instance data)\n\n"
                    "Addressing:\n"
                    "I0.0=Digital Input | Q0.0=Digital Output\n"
                    "M0.0=Memory Bit | IW0=Input Word | QW0=Output Word\n"
                    "DB1.DBX0.0=DB Bit | DB1.DBW0=DB Word")
        if "allen" in q or "studio" in q or "rslogix" in q:
            return ("ALLEN BRADLEY STUDIO 5000:\n\n"
                    "Controllers: Micro820 | CompactLogix | ControlLogix\n\n"
                    "Tag Types:\n"
                    "BOOL SINT INT DINT LINT REAL LREAL STRING\n\n"
                    "Key Instructions:\n"
                    "XIC/XIO — Contacts | OTE/OTL/OTU — Outputs\n"
                    "TON/TOF/RTO — Timers | CTU/CTD — Counters\n"
                    "MOV/COP — Data move | ADD/SUB/MUL/DIV — Math\n"
                    "PID — Process control | MSG — Communications\n\n"
                    "Shortcuts:\n"
                    "Ctrl+W = Add rung | F5 = Download | Ctrl+D = Go online")
        return (f"PLC Expert Brain: '{q}'\n\n"
                "Ask specifically about:\n"
                "Ladder logic | Allen Bradley | Siemens TIA Portal\n"
                "Modbus | Profibus | SCADA | HMI | PID | Timers | Counters")

    def _safety_domain(self,q):
        if any(w in q for w in ["estop","emergency stop","e-stop"]):
            return ("EMERGENCY STOP DESIGN:\n\n"
                    "Hardware: NC (Normally Closed) in series — HARDWIRED\n"
                    "Color: RED mushroom, YELLOW background (ISO 13850)\n"
                    "Reset: Manual only — CANNOT auto-restart\n\n"
                    "Stop Categories (IEC 60204-1):\n"
                    "0 — Immediate power removal (uncontrolled)\n"
                    "1 — Controlled stop then power removal\n"
                    "2 — Controlled stop, power maintained\n\n"
                    "Safety Relay monitors:\n"
                    "- Feedback contacts (detects welded)\n"
                    "- Cross-monitoring (dual channel)\n"
                    "- Response time < 20ms typically")
        if "sil" in q:
            return ("SAFETY INTEGRITY LEVELS (IEC 61508):\n\n"
                    "SIL 1 | PFD 0.01-0.1    | RRF 10-100\n"
                    "SIL 2 | PFD 0.001-0.01  | RRF 100-1000\n"
                    "SIL 3 | PFD 0.0001-0.001| RRF 1000-10000\n"
                    "SIL 4 | PFD <0.0001     | RRF >10000\n\n"
                    "PFD = Probability of Failure on Demand\n"
                    "RRF = Risk Reduction Factor\n\n"
                    "Standards:\n"
                    "IEC 61508 — Electrical/Electronic systems\n"
                    "IEC 61511 — Process industry\n"
                    "ISO 13849 — Machinery safety\n"
                    "IEC 62061 — Complex machinery")
        if "loto" in q or "lockout" in q:
            return ("LOTO PROCEDURE (OSHA 29 CFR 1910.147):\n\n"
                    "1. NOTIFY — Inform all affected personnel\n"
                    "2. IDENTIFY — All energy sources (electrical, pneumatic, hydraulic, thermal, gravity)\n"
                    "3. SHUTDOWN — Stop equipment normally\n"
                    "4. ISOLATE — Disconnect/close all energy isolating devices\n"
                    "5. LOCKOUT — Apply personal lock to each isolation point\n"
                    "6. TAGOUT — Attach warning tag to each lock\n"
                    "7. RELEASE — Bleed pressure, discharge capacitors, block gravity\n"
                    "8. VERIFY — Test/measure to confirm ZERO energy state\n\n"
                    "Removal (reverse order):\n"
                    "Remove tools -> Restore guards -> Clear personnel\n"
                    "Remove locks/tags -> Restore energy -> Notify completion")
        return (f"Safety Brain: '{q}'\n\n"
                "I cover:\nE-stop design | SIL levels | LOTO procedure\n"
                "Risk assessment | IEC 61508/61511 | ISO 13849\n"
                "PPE | Permit to work | Hazard analysis | ATEX")

    def _code_domain(self,q):
        if "pyautogui" in q or "gui automat" in q:
            return ("PYTHON GUI AUTOMATION:\n\n"
                    "import pyautogui\nimport time\n\n"
                    "# Mouse control\npyautogui.moveTo(x, y, duration=0.5)\n"
                    "pyautogui.click(x, y)\npyautogui.doubleClick(x, y)\n"
                    "pyautogui.rightClick(x, y)\npyautogui.drag(x1,y1,x2,y2)\n\n"
                    "# Keyboard\npyautogui.typewrite('Hello', interval=0.05)\n"
                    "pyautogui.press('enter')\npyautogui.hotkey('ctrl','s')\n\n"
                    "# Find elements\nloc = pyautogui.locateOnScreen('btn.png')\n"
                    "if loc: pyautogui.click(loc)\n\n"
                    "# Screenshot\nimg = pyautogui.screenshot()\nimg.save('screen.png')\n\n"
                    "# Safety\npyautogui.FAILSAFE = True  # Move mouse corner to stop\n"
                    "pyautogui.PAUSE = 0.1  # Delay between actions")
        if "modbus" in q or "plc" in q:
            return ("PYTHON MODBUS:\n\n"
                    "from pymodbus.client import ModbusTcpClient\n\n"
                    "# Connect\nclient = ModbusTcpClient('192.168.1.1', port=502)\nclient.connect()\n\n"
                    "# Read registers\nresult = client.read_holding_registers(0, 10, unit=1)\nprint(result.registers)\n\n"
                    "# Write register\nclient.write_register(0, 1234, unit=1)\n\n"
                    "# Read coils\ncoils = client.read_coils(0, 8, unit=1)\nprint(coils.bits)\n\n"
                    "# Write coil\nclient.write_coil(0, True, unit=1)\nclient.close()\n\n"
                    "Install: pip install pymodbus")
        return (f"Code Brain: '{q}'\n\n"
                "I can write:\nPython scripts | GUI automation | PLC Modbus comms\n"
                "File operations | Data processing | Web automation\n"
                "Tell me specifically what code you need!")

    def _screen_domain(self,q):
        return ("GUI AUTOMATION EXPERT:\n\n"
                "pyautogui commands:\n"
                "pyautogui.click(x, y)           — Click position\n"
                "pyautogui.locateOnScreen(img)   — Find image\n"
                "pyautogui.typewrite('text')     — Type text\n"
                "pyautogui.hotkey('ctrl','c')    — Key combo\n"
                "pyautogui.screenshot()          — Capture screen\n\n"
                "Find coordinates:\nMove mouse to target -> Windows shows X,Y in taskbar\n\n"
                "For software automation:\n"
                "import subprocess\nsubprocess.Popen('notepad.exe')\n"
                "time.sleep(1)  # Wait for open\n"
                "pyautogui.typewrite('Hello World')")

    def _docs_domain(self,q):
        return (f"Documentation Brain ready for: '{q}'\n\n"
                "I can write:\n"
                "- Technical reports and manuals\n"
                "- PLC program documentation\n"
                "- Safety procedures (SOP, LOTO)\n"
                "- Email drafts\n- Project summaries\n\n"
                "For full AI document generation, download Qwen2-7B (4.5GB).\n"
                "Tell me what document you need and I will write it.")

    def _learner_domain(self,query):
        q=query.lower()
        sw=None
        for name in SW_MAP:
            if name in q:
                sw=name
                break
        if sw:
            return self._handle_open(query,return_str=True)
        return (f"Software Learning Brain: '{query}'\n\n"
                "I can help you:\n"
                "- Open any software\n"
                "- Navigate menus step by step\n"
                "- Learn keyboard shortcuts\n"
                "- Automate repetitive tasks\n\n"
                "Tell me which software you want to learn or open!")

    def _math_domain(self,query):
        return self._handle_math(query,return_str=True)

    def _ocr_domain(self,q):
        return ("OCR Vision Brain ready.\n\n"
                "I can:\n"
                "- Take screenshot and read all text\n"
                "- Find specific text on screen\n"
                "- Describe what's visible\n"
                "- Click on text found on screen\n\n"
                "Say: 'Take a screenshot' or 'What is on screen?'")

    # ══════════════════════════════════════════════════════════
    # SPECIAL HANDLERS
    # ══════════════════════════════════════════════════════════

    def _handle_open(self, query, return_str=False):
        q=query.lower()
        opened=None; app_name=None
        for key,(exe,name) in SW_MAP.items():
            if key in q:
                try:
                    subprocess.Popen(exe, shell=True)
                    opened=exe; app_name=name
                    break
                except: pass
        if not opened:
            pats=[r"open (.+?)(?:\s+and|\s*$)",
                  r"launch (.+?)(?:\s+and|\s*$)",
                  r"start (.+?)(?:\s+and|\s*$)"]
            for pat in pats:
                m=re.search(pat,q)
                if m:
                    app=m.group(1).strip().rstrip(".")
                    # Try direct, then shell search
                    for cmd in [app, f'start "" "{app}"', 
                                f'"{app}.exe"',
                                f'start "" "{app}.exe"']: 
                        try:
                            subprocess.Popen(cmd, shell=True)
                            opened=app; app_name=app.title()
                            break
                        except: pass
                    if opened: break
        if opened:
            self.root.after(800, self._enter_mini_mode)
            msg=(f"OK Opening {app_name}...\n"
                 "Switching to Mini Mode — I am in the corner.\n"
                 "Type commands in the small bar while using software.")
        else:
            app_search=re.sub(r'^(open|launch|start|run)\s+','',q).strip()
            subprocess.Popen(f'start "" "{app_search}"',shell=True)
            msg=(f"Searching Windows for: {app_search}\n"
                 "If not found, tell me exact software name or path.")
        if return_str: return msg
        self._msg("action","[LEARNER BRAIN | Opening software]\n")
        self._msg("agent",f"{msg}\n\n")
        self._done_busy("Software launched!")

    def _handle_math(self, query, return_str=False):
        q=query
        result_str="MATH BRAIN:\n\n"
        # Direct calculation
        try:
            expr=re.search(r'[\d\s\+\-\*\/\.\%\(\)]+',q)
            if expr:
                clean=expr.group().strip()
                if any(c.isdigit() for c in clean) and \
                   any(op in clean for op in ['+','-','*','/']):
                    val=eval(clean)
                    result_str=(f"Calculation:\n\n"
                               f"  {clean.strip()} = {val}\n\n"
                               f"Computed by GP PRO AGENT Math Brain.")
        except: pass
        # Unit conversions
        ql=q.lower()
        if "psi" in ql:
            m=re.search(r'(\d+\.?\d*)',ql)
            if m:
                psi=float(m.group(1))
                result_str=f"{psi} PSI = {psi*0.0689476:.4f} Bar"
        elif "celsius" in ql or "°c" in ql:
            m=re.search(r'(\d+\.?\d*)',ql)
            if m:
                c=float(m.group(1))
                result_str=f"{c}°C = {c*9/5+32:.2f}°F"
        elif "4-20" in ql or "4ma" in ql.replace(" ",""):
            m=re.search(r'(\d+\.?\d*)\s*ma',ql,re.I)
            if m:
                ma=float(m.group(1))
                pct=(ma-4)/16*100
                result_str=f"{ma}mA = {pct:.2f}% (4-20mA scale)"
        if return_str: return result_str
        self._msg("model","[MATH BRAIN | instant]\n")
        self._msg("agent",f"{result_str}\n\n")
        self._done_busy("Calculated!")

    def _handle_vision_cmd(self, query):
        self._msg("action","[OCR VISION BRAIN | Reading screen]\n")
        self.root.after(0,self.status_bar.config,
            {"text":"Reading screen...","fg":self.C["warning"]})
        text=self.vision.describe_screen()
        windows=self.vision.detect_open_windows()
        resp=text
        if windows:
            resp+=f"\n\nOpen windows:\n"+"\n".join(f"- {w}" for w in windows)
        self._msg("agent",f"{resp}\n\n")
        self._done_busy("Screen read complete!")

    def _handle_screenshot(self):
        self._msg("action","[OCR BRAIN | Capturing screen]\n")
        img, path=self.vision.take_screenshot()
        if img:
            self._msg("agent",
                f"Screenshot saved!\nPath: {path}\n"
                f"Size: {img.width}x{img.height}px\n\n")
        else:
            self._msg("error","Screenshot failed. Install pyautogui.\n\n")
        self._done_busy("Screenshot done!")

    def _handle_plc_cmd(self, query):
        self._msg("action","[PLC CONTROLLER BRAIN]\n")
        result=self.plc.execute_plc_command(query)
        self._msg("agent",f"{result}\n\n")
        self._done_busy("PLC command sent!")

    def _scheduled_execute(self, query):
        """Called by scheduler — run query automatically."""
        self._msg("system",f"[[TIME] SCHEDULED TASK]\n")
        self._start_processing(query)

    # ══════════════════════════════════════════════════════════
    # UI SELF-MODIFICATION
    # ══════════════════════════════════════════════════════════

    def _is_ui_cmd(self,q):
        return any(k in q for k in [
            "change theme","change color","change accent",
            "make font","font size","make text",
            "change background","dark mode","light mode",
        ])

    def _handle_ui(self,query):
        q=query.lower()
        changes=[]
        colors={
            "blue":"#0066ff","red":"#ff3333","green":"#00ff88",
            "purple":"#bf5fff","orange":"#ff6b2b","yellow":"#ffdd00",
            "pink":"#ff66cc","cyan":"#00e5ff","teal":"#00ccaa",
            "white":"#e0f0ff","gold":"#ffd700","lime":"#aaff00",
        }
        if any(w in q for w in ["color","theme","accent"]):
            for name,hx in colors.items():
                if name in q:
                    self.C["cyan"]=hx
                    self.settings.ui["accent_color"]=hx
                    self.root.after(0,self.send_btn.config,{"bg":hx})
                    self.root.after(0,self.chat.tag_config,
                        "user",{"foreground":hx})
                    changes.append(f"Accent -> {name} ({hx})")
                    break
        if "font" in q or "text size" in q:
            cur=self.F["body"][1]
            if any(w in q for w in ["bigger","larger","increase","+"]):
                ns=min(cur+2,18)
                self.F["body"]=("Consolas",ns)
                self.settings.ui["font_size"]=ns
                self.root.after(0,self.chat.config,{"font":self.F["body"]})
                changes.append(f"Font -> {ns}pt")
            elif any(w in q for w in ["smaller","decrease","-"]):
                ns=max(cur-2,8)
                self.F["body"]=("Consolas",ns)
                self.settings.ui["font_size"]=ns
                self.root.after(0,self.chat.config,{"font":self.F["body"]})
                changes.append(f"Font -> {ns}pt")
        if "dark" in q:
            self.C["bg"]="#0a0f1a"; self.C["panel"]="#0d1526"
            changes.append("Dark mode")
        if changes:
            self.settings.save_ui()
            self._msg("ui_msg",
                ">> UI MODIFIED:\n"
                +"".join(f"  OK {c}\n" for c in changes)
                +"Saved permanently.\n\n")
        else:
            self._msg("ui_msg",
                ">> Try: 'change theme to blue' | 'make font bigger'\n\n")
        self._done_busy("UI updated!")

    # ══════════════════════════════════════════════════════════
    # VOICE MODULE
    # ══════════════════════════════════════════════════════════

    def _toggle_voice(self):
        self._voice_on = not self._voice_on
        if self._voice_on:
            self.voice.start_listening(self._voice_input_received)
            self.voice_lbl.config(text="[MIC] ON",fg=self.C["green"])
            self._msg("system",">> Voice activated — speak your commands\n\n")
        else:
            self.voice.stop_listening()
            self.voice_lbl.config(text="[MIC] OFF",fg=self.C["dim"])
            self._msg("system",">> Voice deactivated\n\n")

    def _voice_input_received(self, text: str):
        """Called when voice recognizes speech."""
        self._msg("user",f"[MIC] (voice): {text}\n")
        if not self._busy:
            self._start_processing(text)

    # ══════════════════════════════════════════════════════════
    # VISION MODULE
    # ══════════════════════════════════════════════════════════

    def _vision_action(self):
        """Quick vision action from button."""
        if not self._busy:
            self._start_processing("What text is visible on my screen right now?")

    # ══════════════════════════════════════════════════════════
    # PLC PANEL
    # ══════════════════════════════════════════════════════════

    def _plc_panel(self):
        win=tk.Toplevel(self.root)
        win.title("PLC Controller")
        win.geometry("500x400")
        win.configure(bg=self.C["bg"])
        tk.Label(win,text=">> PLC SOFTWARE CONTROLLER",
                 bg=self.C["bg"],fg=self.C["cyan"],
                 font=self.F["head"]).pack(anchor="w",padx=16,pady=12)
        sw=self.plc.detect_plc_software()
        status=sw if sw else "No PLC software detected"
        tk.Label(win,text=f"Status: {status}",
                 bg=self.C["bg"],fg=self.C["green"] if sw else self.C["dim"],
                 font=self.F["small"]).pack(anchor="w",padx=16)
        tk.Frame(win,bg=self.C["border"],height=1).pack(
            fill="x",padx=16,pady=8)
        cmds=[
            ("Open Studio 5000","Open Studio 5000 PLC software"),
            ("Open TIA Portal", "Open TIA Portal PLC software"),
            ("Open PCWin",      "Open PCWin PLC software"),
            ("Go Online",       "Go online in PLC software"),
            ("Add New Rung",    "Add new rung in ladder logic"),
            ("Save Project",    "Save PLC project"),
            ("Read Screen",     "Read current PLC screen content"),
        ]
        for lbl,cmd in cmds:
            tk.Button(win,text=lbl,bg=self.C["button"],fg=self.C["white"],
                      font=self.F["small"],relief="flat",cursor="hand2",
                      command=lambda c=cmd:self._quick(c)).pack(
                      fill="x",padx=16,pady=3)

    # ══════════════════════════════════════════════════════════
    # SCHEDULER PANEL
    # ══════════════════════════════════════════════════════════

    def _scheduler_panel(self):
        win=tk.Toplevel(self.root)
        win.title("Task Scheduler")
        win.geometry("650x500")
        win.configure(bg=self.C["bg"])
        tk.Label(win,text=">> AUTO TASK SCHEDULER",
                 bg=self.C["bg"],fg=self.C["cyan"],
                 font=self.F["head"]).pack(anchor="w",padx=16,pady=12)
        tk.Label(win,text="Tasks run automatically in background. Add tasks below.",
                 bg=self.C["bg"],fg=self.C["dim"],
                 font=self.F["small"]).pack(anchor="w",padx=16)
        tk.Frame(win,bg=self.C["border"],height=1).pack(
            fill="x",padx=16,pady=8)
        # Task list
        lf=tk.Frame(win,bg=self.C["bg"])
        lf.pack(fill="both",expand=True,padx=16)
        def refresh_tasks():
            for w in lf.winfo_children(): w.destroy()
            for task in self.scheduler.get_tasks():
                rf=tk.Frame(lf,bg=self.C["panel"],pady=4)
                rf.pack(fill="x",pady=2)
                color=self.C["green"] if task.enabled else self.C["dim"]
                tk.Label(rf,text="●",bg=self.C["panel"],fg=color,
                         font=self.F["small"]).pack(side="left",padx=6)
                tk.Label(rf,text=f"{task.name}",bg=self.C["panel"],
                         fg=self.C["white"],font=self.F["small"],
                         width=22,anchor="w").pack(side="left")
                tk.Label(rf,text=f"{task.schedule}",bg=self.C["panel"],
                         fg=self.C["dim"],font=self.F["small"],
                         width=12).pack(side="left")
                tk.Label(rf,text=f"Ran:{task.run_count}x",bg=self.C["panel"],
                         fg=self.C["dim"],font=self.F["small"]).pack(side="left")
                tk.Button(rf,text="Enable" if not task.enabled else "Disable",
                          bg=self.C["button"],fg=self.C["white"],
                          font=self.F["small"],relief="flat",
                          command=lambda t=task.name,r=refresh_tasks:
                          [self.scheduler.toggle_task(t),r()]).pack(
                          side="right",padx=4)
                tk.Button(rf,text="Run Now",bg=self.C["cyan"],
                          fg=self.C["bg"],font=self.F["small"],relief="flat",
                          command=lambda c=task.command:self._quick(c)).pack(
                          side="right",padx=2)

        refresh_tasks()
        # Add new task
        tk.Frame(win,bg=self.C["border"],height=1).pack(
            fill="x",padx=16,pady=8)
        af=tk.Frame(win,bg=self.C["bg"])
        af.pack(fill="x",padx=16,pady=(0,8))
        tk.Label(af,text="Add task:",bg=self.C["bg"],
                 fg=self.C["dim"],font=self.F["small"]).pack(side="left")
        name_e=tk.Entry(af,bg=self.C["input_bg"],fg=self.C["white"],
                        font=self.F["small"],width=14)
        name_e.insert(0,"Task name")
        name_e.pack(side="left",padx=4)
        cmd_e=tk.Entry(af,bg=self.C["input_bg"],fg=self.C["white"],
                       font=self.F["small"],width=20)
        cmd_e.insert(0,"Command to run")
        cmd_e.pack(side="left",padx=4)
        sched_e=tk.Entry(af,bg=self.C["input_bg"],fg=self.C["white"],
                         font=self.F["small"],width=10)
        sched_e.insert(0,"every 1h")
        sched_e.pack(side="left",padx=4)
        def add_task():
            self.scheduler.add_task(
                name_e.get(),cmd_e.get(),sched_e.get())
            refresh_tasks()
        tk.Button(af,text="Add",bg=self.C["cyan"],fg=self.C["bg"],
                  font=self.F["small"],relief="flat",
                  command=add_task).pack(side="left")

    # ══════════════════════════════════════════════════════════
    # MINI MODE — Small floating search bar
    # ══════════════════════════════════════════════════════════

    def _enter_mini_mode(self):
        if self._minimized: return
        self._minimized=True
        self.root.withdraw()
        sw=self.root.winfo_screenwidth()
        self._mini_win=tk.Toplevel()
        self._mini_win.geometry(f"380x55+{sw-390}+8")
        self._mini_win.configure(bg=self.C["panel"])
        self._mini_win.attributes("-topmost",True)
        self._mini_win.overrideredirect(True)
        self._mini_win.resizable(False,False)
        frame=tk.Frame(self._mini_win,bg=self.C["panel"],
                       highlightbackground=self.C["cyan"],
                       highlightthickness=1)
        frame.pack(fill="both",expand=True,padx=1,pady=1)
        tk.Label(frame,text="[GP]",bg=self.C["panel"],
                 fg=self.C["cyan"],font=("Consolas",12)).pack(
                 side="left",padx=4)
        self._mini_inp=tk.Entry(frame,bg=self.C["input_bg"],
                                 fg=self.C["white"],
                                 font=("Consolas",10),
                                 borderwidth=0,
                                 insertbackground=self.C["cyan"],
                                 width=22)
        self._mini_inp.pack(side="left",fill="x",expand=True,
                            pady=6,padx=2)
        self._mini_inp.bind("<Return>",self._mini_send)
        self._mini_inp.focus_set()
        tk.Button(frame,text=">",bg=self.C["cyan"],fg=self.C["bg"],
                  font=("Consolas",9,"bold"),relief="flat",width=2,
                  command=self._mini_send).pack(side="left",padx=1)
        tk.Button(frame,text="[+]",bg=self.C["button"],fg=self.C["white"],
                  font=("Consolas",9),relief="flat",width=2,
                  command=self._restore_mini).pack(side="left",padx=1)
        tk.Button(frame,text="X",bg=self.C["error"],fg=self.C["white"],
                  font=("Consolas",9),relief="flat",width=2,
                  command=self._close_mini).pack(side="left",padx=(1,3))
        self._mini_win.protocol("WM_DELETE_WINDOW",self._restore_mini)

    def _mini_send(self,e=None):
        q=self._mini_inp.get().strip()
        if not q: return
        self._mini_inp.delete(0,"end")
        self._restore_mini()
        self.root.after(200,lambda:self._send_direct(q))

    def _send_direct(self,q):
        self.inp.delete("1.0","end")
        self.inp.insert("1.0",q)
        self._send()

    def _restore_mini(self):
        if not self._minimized: return
        self._minimized=False
        if self._mini_win:
            try: self._mini_win.destroy()
            except: pass
            self._mini_win=None
        self.root.deiconify()
        self.root.lift()

    def _close_mini(self):
        self._minimized=False
        if self._mini_win:
            try: self._mini_win.destroy()
            except: pass
            self._mini_win=None

    # ══════════════════════════════════════════════════════════
    # DOWNLOAD MANAGER — Singleton
    # ══════════════════════════════════════════════════════════

    def _open_dl_manager(self):
        if self._dl_win and self._dl_win.winfo_exists():
            self._dl_win.lift(); self._dl_win.focus_force(); return
        win=tk.Toplevel(self.root)
        win.title("GP PRO AGENT — Download Manager")
        win.geometry("740x540")
        win.configure(bg=self.C["bg"])
        self._dl_win=win
        tk.Label(win,text=">> BRAIN DOWNLOAD MANAGER",
                 bg=self.C["bg"],fg=self.C["cyan"],
                 font=self.F["head"]).pack(anchor="w",padx=16,pady=(12,2))
        tk.Label(win,text="C:\\GPProAgent\\models\\ | Downloads auto-resume",
                 bg=self.C["bg"],fg=self.C["dim"],
                 font=self.F["small"]).pack(anchor="w",padx=16)
        tk.Frame(win,bg=self.C["border"],height=1).pack(
            fill="x",padx=16,pady=8)
        canvas=tk.Canvas(win,bg=self.C["bg"],highlightthickness=0)
        sb=ttk.Scrollbar(win,orient="vertical",command=canvas.yview)
        frame=tk.Frame(canvas,bg=self.C["bg"])
        canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side="left",fill="both",expand=True,padx=(16,0))
        sb.pack(side="right",fill="y",padx=(0,8))
        cw=canvas.create_window((0,0),window=frame,anchor="nw")
        frame.bind("<Configure>",lambda e:canvas.configure(
            scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>",lambda e:canvas.itemconfig(cw,width=e.width))
        self._dl_labels={}
        for key,model in MODELS.items():
            dest=self.settings.model_path/model["file"]
            exists=dest.exists()
            row=tk.Frame(frame,bg=self.C["panel"],pady=3)
            row.pack(fill="x",pady=2,padx=4)
            c=self.C["green"] if exists else self.C["error"]
            s="OK Ready" if exists else "X Missing"
            tk.Label(row,text=f"[{key}]",bg=self.C["panel"],
                     fg=self.C["orange"],font=self.F["small"],
                     width=8).pack(side="left",padx=6)
            tk.Label(row,text=f"{model['name'][:24]}",
                     bg=self.C["panel"],fg=self.C["white"],
                     font=self.F["small"],width=25,
                     anchor="w").pack(side="left")
            tk.Label(row,text=f"{model['size_gb']}GB",
                     bg=self.C["panel"],fg=self.C["dim"],
                     font=self.F["small"],width=6).pack(side="left")
            lbl=tk.Label(row,text=s,bg=self.C["panel"],fg=c,
                         font=self.F["small"],width=12)
            lbl.pack(side="left",padx=4)
            self._dl_labels[key]=lbl
            if not exists:
                tk.Button(row,text="[v] Download",bg=self.C["cyan"],
                          fg=self.C["bg"],font=self.F["small"],
                          relief="flat",cursor="hand2",
                          command=lambda k=key,m=model,l=lbl:
                          threading.Thread(target=self._dl_one,
                              args=(k,m,l),daemon=True).start()
                          ).pack(side="right",padx=6)
            else:
                tk.Label(row,text="OK",bg=self.C["panel"],
                         fg=self.C["green"],font=self.F["small"]
                         ).pack(side="right",padx=6)
        bot=tk.Frame(win,bg=self.C["bg"])
        bot.pack(fill="x",padx=16,pady=8)
        self._dl_status=tk.Label(bot,text="",bg=self.C["bg"],
                                  fg=self.C["green"],font=self.F["small"])
        self._dl_status.pack(side="left",padx=8)
        tk.Button(bot,text="[v] Download ALL Missing",
                  bg=self.C["cyan"],fg=self.C["bg"],
                  font=self.F["head"],relief="flat",cursor="hand2",
                  command=lambda:threading.Thread(
                      target=self._dl_all,daemon=True).start()
                  ).pack(side="right")

    def _dl_one(self,key,model,label):
        dest=self.settings.model_path/model["file"]
        ok=self._dl_file(model["url"],dest,label)
        if ok:
            label.config(text="OK Ready",fg=self.C["green"])
            self._refresh_dots()

    def _dl_all(self):
        missing=[(k,m) for k,m in MODELS.items()
                 if not(self.settings.model_path/m["file"]).exists()]
        self._dl_status.config(text=f"Downloading {len(missing)}...")
        for key,model in missing:
            lbl=self._dl_labels.get(key)
            dest=self.settings.model_path/model["file"]
            ok=self._dl_file(model["url"],dest,lbl)
            if ok and lbl:
                lbl.config(text="OK Ready",fg=self.C["green"])
        self._dl_status.config(text="OK All done!")
        self._refresh_dots()

    def _dl_file(self,url,dest,lbl=None):
        import urllib.request
        tmp=Path(str(dest)+".part")
        headers={"User-Agent":"GP-PRO-AGENT/2.0"}
        resume=tmp.stat().st_size if tmp.exists() else 0
        if resume>0: headers["Range"]=f"bytes={resume}-"
        try:
            req=urllib.request.Request(url,headers=headers)
            with urllib.request.urlopen(req,timeout=30) as r:
                total=int(r.headers.get("Content-Length",0))+resume
                dl=resume
                with open(tmp,"ab" if resume>0 else "wb") as f:
                    while True:
                        chunk=r.read(524288)
                        if not chunk: break
                        f.write(chunk)
                        dl+=len(chunk)
                        if total>0 and lbl:
                            pct=int(dl/total*100)
                            self.root.after(0,lbl.config,
                                {"text":f"{pct}% | {dl//1048576}MB",
                                 "fg":self.C["warning"]})
            shutil.move(str(tmp),str(dest))
            return True
        except Exception as e:
            print(f"[DL] {e}")
            return False

    # ══════════════════════════════════════════════════════════
    # HELPERS
    # ══════════════════════════════════════════════════════════

    def _startup(self):
        time.sleep(1)
        ready=sum(1 for m in MODELS.values()
                  if(self.settings.model_path/m["file"]).exists())
        self._msg("system",
            f">> Models: {ready}/{len(MODELS)} ready")
        if ready < len(MODELS):
            self._msg("system",
                f" | Click '[v] Models' to download {len(MODELS)-ready} missing")
        self._msg("system","\n")
        try:
            import llama_cpp
            self._msg("system",
                ">> AI Engine: llama.cpp OK — Real AI responses active\n")
        except ImportError:
            self._msg("system",
                ">> AI Engine: Expert knowledge mode\n"
                ">> For real AI: pip install llama-cpp-python --prefer-binary\n")
        self._msg("system",
            f">> Memory: {self.memory.get_stats()['total']} entries loaded\n")
        self._msg("system",
            f">> Scheduler: {len(self.scheduler.get_tasks())} tasks configured\n\n")
        self._refresh_dots()
        stats=self.memory.get_stats()
        self.root.after(0,self.mem_lbl.config,
            {"text":f"Entries: {stats['total']}"})

    def _refresh_dots(self):
        for key,model in MODELS.items():
            c=(self.C["green"]
               if(self.settings.model_path/model["file"]).exists()
               else self.C["error"])
            self.dots[key].config(fg=c)

    def _update_stats(self,dur,brain):
        self._qcount+=1
        self._ttime+=dur
        avg=round(self._ttime/self._qcount,1)
        self.root.after(0,self.stats_lbl.config,
            {"text":f"Queries : {self._qcount}\n"
                    f"Avg time: {avg}s\nLast    : {dur}s"})

    def _done_busy(self,msg):
        self._busy=False
        self.root.after(0,self.send_btn.config,
            {"state":"normal","text":"> SEND"})
        self.root.after(0,self.cancel_btn.config,{"state":"disabled"})
        self.root.after(0,self.status_bar.config,
            {"text":msg,"fg":self.C["green"]})

    def _msg(self,tag,text):
        def _d():
            # Safely encode text for Windows
            try:
                safe_text = text.encode('cp1252','replace').decode('cp1252')
            except:
                safe_text = text.encode('ascii','replace').decode('ascii')
            self.chat.config(state="normal")
            self.chat.insert("end",safe_text,tag)
            self.chat.see("end")
            self.chat.config(state="disabled")
        self.root.after(0,_d)

    def _dot(self,key,color):
        if key in self.dots: self.dots[key].config(fg=color)

    def _all_dots(self,color):
        for d in self.dots.values(): d.config(fg=color)

    def _upd_active(self,key):
        m=MODELS.get(key,{})
        self.active_lbl.config(
            text=f"{m.get('name','?')}\n"
                 f"Speed:{m.get('speed_s')}s  Acc:{m.get('accuracy')}%\n"
                 f"RAM:{m.get('ram_mb')}MB")

    def _clear(self):
        self.chat.config(state="normal")
        self.chat.delete("1.0","end")
        self.chat.config(state="disabled")
        self._msg("system","Chat cleared.\n")

    def _quick(self,cmd):
        self.inp.delete("1.0","end")
        self.inp.insert("1.0",cmd)
        self._send()

    def _upd_ram(self):
        try:
            import psutil
            mb=psutil.Process(os.getpid()).memory_info().rss/(1024**2)
            c=self.C["green"] if mb<500 else self.C["warning"]
            self.ram_lbl.config(text=f"RAM:{mb:.0f}MB",fg=c)
            # Update dashboard
            if self._qcount>0:
                self.dashboard._stat_labels.get("RAM",
                    type("x",(),{"config":lambda **k:None})()).config(
                    text=f"{mb:.0f}MB")
        except: pass
        self.root.after(3000,self._upd_ram)

    def run(self):
        self._upd_ram()
        self.root.mainloop()

    # ══════════════════════════════════════════════════════════
    # IMPROVEMENT 1 — WEB SERVER
    # ══════════════════════════════════════════════════════════

    def _web_query_handler(self, query: str) -> dict:
        """Handle queries from web interface."""
        brain = self._route(query.lower())
        model = MODELS[brain]
        start = time.time()
        answer = self._ask(brain, query)
        dur  = round(time.time()-start, 2)
        self.memory.remember(query, answer, brain)
        self.dashboard.record_query(brain, dur)
        # Also show in main chat
        self._msg("system", f"[[WEB] Web] {query[:40]}\n")
        self._msg("agent",  f"{answer[:100]}...\n\n")
        return {
            "answer":   answer,
            "brain":    brain,
            "duration": dur,
            "accuracy": model["accuracy"],
        }

    def _show_web_info(self):
        url = self.web.get_url()
        win = tk.Toplevel(self.root)
        win.title("Web Interface")
        win.geometry("400x220")
        win.configure(bg=self.C["bg"])
        tk.Label(win, text=">> WEB INTERFACE",
                bg=self.C["bg"], fg=self.C["cyan"],
                font=self.F["head"]).pack(pady=(16,8))
        tk.Label(win, text="Access GP PRO AGENT from any browser\nor phone on same WiFi:",
                bg=self.C["bg"], fg=self.C["dim"],
                font=self.F["small"]).pack()
        tk.Label(win, text=url,
                bg=self.C["bg"], fg=self.C["green"],
                font=("Consolas",14,"bold")).pack(pady=12)
        tk.Label(win, text="Also try: http://localhost:5000",
                bg=self.C["bg"], fg=self.C["dim"],
                font=self.F["small"]).pack()
        def copy_url():
            self.root.clipboard_clear()
            self.root.clipboard_append(url)
        tk.Button(win, text="Copy URL",
                 bg=self.C["cyan"], fg=self.C["bg"],
                 font=self.F["head"], relief="flat",
                 command=copy_url).pack(pady=12)
        self._msg("system",
            f">> Web interface: {url}\n"
            "Open in phone browser to control GP PRO AGENT remotely!\n\n")

    # ══════════════════════════════════════════════════════════
    # IMPROVEMENT 2 — CODE GENERATOR
    # ══════════════════════════════════════════════════════════

    def _handle_codegen(self, query: str):
        self._msg("action", "[CODE GENERATOR BRAIN]\n")
        llm_cb = None
        if self._llm:
            llm_cb = lambda q: self._ask("coder", q)
        result = self.codegen.generate(query, llm_cb)
        response = (f"OK Code Generated!\n\n"
                   f"Language : {result['language']}\n"
                   f"File     : {result['filename']}\n"
                   f"Lines    : {result['lines']}\n"
                   f"Saved to : {result['filepath']}\n\n"
                   f"Preview (first 30 lines):\n"
                   + "\n".join(result['code'].split('\n')[:30]))
        self._msg("agent", f"{response}\n\n")
        self._done_busy("Code generated!")

    def _codegen_panel(self):
        win = tk.Toplevel(self.root)
        win.title("AI Code Generator")
        win.geometry("600x450")
        win.configure(bg=self.C["bg"])
        tk.Label(win, text=">> AI CODE GENERATOR",
                bg=self.C["bg"], fg=self.C["cyan"],
                font=self.F["head"]).pack(anchor="w", padx=16, pady=12)
        tk.Label(win,
                text="Describe what code you need — I generate complete working programs.",
                bg=self.C["bg"], fg=self.C["dim"],
                font=self.F["small"]).pack(anchor="w", padx=16)
        tk.Frame(win, bg=self.C["border"], height=1).pack(
            fill="x", padx=16, pady=8)
        # Examples
        examples = [
            ("Modbus PLC Client",  "Generate Modbus TCP client to read PLC registers at 192.168.1.1"),
            ("GUI Automation",     "Generate GUI automation script to open Notepad and type text"),
            ("PLC Structured Text","Generate PLC structured text program for motor start stop"),
            ("Data Logger",        "Generate data logger to log temperature every 5 seconds to CSV"),
            ("Screen Monitor",     "Generate script to take screenshot every minute and save"),
        ]
        tk.Label(win, text="Quick Templates:",
                bg=self.C["bg"], fg=self.C["dim"],
                font=self.F["small"]).pack(anchor="w", padx=16)
        bf = tk.Frame(win, bg=self.C["bg"])
        bf.pack(fill="x", padx=16, pady=4)
        for lbl, cmd in examples:
            tk.Button(bf, text=lbl,
                     bg=self.C["button"], fg=self.C["white"],
                     font=self.F["small"], relief="flat",
                     command=lambda c=cmd,w=win: [
                         self._quick(c), w.destroy()]
                     ).pack(side="left", padx=2)
        tk.Frame(win, bg=self.C["border"], height=1).pack(
            fill="x", padx=16, pady=8)
        tk.Label(win, text="Custom description:",
                bg=self.C["bg"], fg=self.C["dim"],
                font=self.F["small"]).pack(anchor="w", padx=16)
        desc = tk.Text(win, bg=self.C["input_bg"],
                      fg=self.C["white"], font=self.F["body"],
                      height=6, wrap=tk.WORD,
                      insertbackground=self.C["cyan"],
                      borderwidth=0, highlightthickness=1,
                      highlightcolor=self.C["cyan"],
                      highlightbackground=self.C["border"],
                      padx=8, pady=8)
        desc.pack(fill="x", padx=16, pady=4)
        desc.insert("1.0",
            "Example: Generate a Python script that monitors PLC via Modbus TCP, "
            "reads temperature every second, logs to CSV, and alerts if above 80°C")
        def generate():
            query = desc.get("1.0","end-1c").strip()
            if query:
                win.destroy()
                self._quick(f"Generate code: {query}")
        tk.Button(win, text="[FAST] GENERATE CODE",
                 bg=self.C["cyan"], fg=self.C["bg"],
                 font=self.F["head"], relief="flat",
                 command=generate).pack(pady=12, ipadx=20, ipady=4)

    # ══════════════════════════════════════════════════════════
    # IMPROVEMENT 3 — PLC TAG MONITOR
    # ══════════════════════════════════════════════════════════

    def _open_tag_monitor(self):
        self.tag_mon.open_window(self.root)

    # ══════════════════════════════════════════════════════════
    # IMPROVEMENT 4 — SMART FILE MANAGER
    # ══════════════════════════════════════════════════════════

    def _handle_file_cmd(self, query: str):
        self._msg("action", "[FILE MANAGER BRAIN]\n")
        llm_cb = None
        if self._llm:
            llm_cb = lambda q: self._ask("docs", q)
        result = self.files.process_command(query, llm_cb)
        self._msg("agent", f"{result}\n\n")
        self._done_busy("File operation complete!")

    def _files_panel(self):
        win = tk.Toplevel(self.root)
        win.title("Smart File Manager")
        win.geometry("550x400")
        win.configure(bg=self.C["bg"])
        tk.Label(win, text=">> SMART FILE MANAGER",
                bg=self.C["bg"], fg=self.C["cyan"],
                font=self.F["head"]).pack(anchor="w", padx=16, pady=12)
        cmds = [
            ("List Desktop Files",      "List files on Desktop"),
            ("List Downloads",          "List files in Downloads"),
            ("Organize Downloads",      "Organize my Downloads folder by file type"),
            ("Find Python Files",       "Find file .py on Desktop"),
            ("Disk Space Info",         "How much disk space do I have?"),
            ("Find Log Files",          "Find file .log"),
        ]
        for lbl, cmd in cmds:
            tk.Button(win, text=lbl,
                     bg=self.C["button"], fg=self.C["white"],
                     font=self.F["small"], relief="flat",
                     cursor="hand2",
                     command=lambda c=cmd,w=win: [
                         self._quick(c), w.destroy()]
                     ).pack(fill="x", padx=16, pady=3)
        tk.Frame(win, bg=self.C["border"], height=1).pack(
            fill="x", padx=16, pady=8)
        inp_f = tk.Frame(win, bg=self.C["bg"])
        inp_f.pack(fill="x", padx=16)
        e = tk.Entry(inp_f, bg=self.C["input_bg"],
                    fg=self.C["white"], font=self.F["small"])
        e.insert(0, "Find file report.xlsx")
        e.pack(side="left", fill="x", expand=True, padx=(0,8))
        tk.Button(inp_f, text="Run",
                 bg=self.C["cyan"], fg=self.C["bg"],
                 font=self.F["small"], relief="flat",
                 command=lambda: [
                     self._quick(e.get()), win.destroy()]
                 ).pack(side="left")

    # ══════════════════════════════════════════════════════════
    # IMPROVEMENT 5 — ALERT SYSTEM
    # ══════════════════════════════════════════════════════════

    def _open_alerts(self):
        self.alerts.open_window(self.root)

    def _notify_from_alert(self, message: str):
        """Called when alert system detects something."""
        self._msg("error", f"{message}\n\n")
        # Flash status bar
        self.root.after(0, self.status_bar.config,
            {"text": f"!! ALERT: {message[:60]}",
             "fg": self.C["error"]})

    # ======================================================
    # NEW MODULE 1 - AUTONOMOUS AGENT
    # ======================================================

    def _msg_from_agent(self, text: str):
        """Receive messages from background agents."""
        safe = text.encode('ascii','replace').decode('ascii')
        self._msg("action", f"{safe}\n\n")

    def _auto_panel(self):
        win = tk.Toplevel(self.root)
        win.title("Autonomous Agent")
        win.geometry("700x550")
        win.configure(bg=self.C["bg"])
        tk.Label(win, text=">> AUTONOMOUS AGENT MODE",
                bg=self.C["bg"], fg=self.C["cyan"],
                font=self.F["head"]).pack(anchor="w",
                padx=16, pady=(12,4))
        status = (f"Patterns: {self.auto_agent.pattern_count} | "
                 f"Active: {self.auto_agent.enabled_count}")
        tk.Label(win, text=status, bg=self.C["bg"],
                fg=self.C["green"],
                font=self.F["small"]).pack(anchor="w", padx=16)
        tk.Frame(win, bg=self.C["border"],
                height=1).pack(fill="x", padx=16, pady=8)

        # Pattern list
        pf = tk.Frame(win, bg=self.C["bg"])
        pf.pack(fill="both", expand=True, padx=16)

        def refresh():
            for w in pf.winfo_children():
                w.destroy()
            for p in self.auto_agent.get_patterns():
                row = tk.Frame(pf, bg=self.C["panel"], pady=3)
                row.pack(fill="x", pady=2)
                c = self.C["green"] if p.enabled else self.C["dim"]
                tk.Label(row, text="*", bg=self.C["panel"],
                        fg=c, font=self.F["small"]).pack(side="left",padx=6)
                tk.Label(row, text=p.name[:35],
                        bg=self.C["panel"], fg=self.C["white"],
                        font=self.F["small"], width=35,
                        anchor="w").pack(side="left")
                tk.Label(row,
                        text=f"Runs:{p.frequency} Conf:{p.confidence:.0%}",
                        bg=self.C["panel"], fg=self.C["dim"],
                        font=self.F["small"]).pack(side="left", padx=8)
                tk.Button(row,
                         text="Enable" if not p.enabled else "Disable",
                         bg=self.C["cyan"] if not p.enabled else self.C["button"],
                         fg=self.C["bg"] if not p.enabled else self.C["white"],
                         font=self.F["small"], relief="flat",
                         command=lambda n=p.name,e=p.enabled:
                         [self.auto_agent.enable_pattern(n,not e),
                          refresh()]).pack(side="right", padx=6)
                tk.Button(row, text="Run Now",
                         bg=self.C["button"], fg=self.C["white"],
                         font=self.F["small"], relief="flat",
                         command=lambda s=p.steps:
                         [self._quick(s[0]) if s else None]
                         ).pack(side="right", padx=2)
        refresh()

        # Add custom pattern
        tk.Frame(win, bg=self.C["border"],
                height=1).pack(fill="x", padx=16, pady=8)
        af = tk.Frame(win, bg=self.C["bg"])
        af.pack(fill="x", padx=16, pady=(0,8))
        tk.Label(af, text="Add pattern:",
                bg=self.C["bg"], fg=self.C["dim"],
                font=self.F["small"]).pack(side="left")
        ne = tk.Entry(af, bg=self.C["input_bg"],
                     fg=self.C["white"],
                     font=self.F["small"], width=16)
        ne.insert(0, "Pattern name")
        ne.pack(side="left", padx=4)
        te = tk.Entry(af, bg=self.C["input_bg"],
                     fg=self.C["white"],
                     font=self.F["small"], width=10)
        te.insert(0, "09:00")
        te.pack(side="left", padx=4)
        ce = tk.Entry(af, bg=self.C["input_bg"],
                     fg=self.C["white"],
                     font=self.F["small"], width=20)
        ce.insert(0, "Command to run")
        ce.pack(side="left", padx=4)
        tk.Button(af, text="Add",
                 bg=self.C["cyan"], fg=self.C["bg"],
                 font=self.F["small"], relief="flat",
                 command=lambda: [
                     self.auto_agent.add_pattern(
                         ne.get(), [te.get()], [ce.get()]),
                     refresh()
                 ]).pack(side="left")

    # ======================================================
    # NEW MODULE 2 - COMPUTER VISION AI
    # ======================================================

    def _handle_cv_analysis(self, query: str):
        self._msg("action", "[CV-AI BRAIN | Analyzing screen]\n")
        self.root.after(0, self.status_bar.config,
            {"text": "CV-AI scanning screen...",
             "fg": self.C["warning"]})
        result = self.cv_ai.analyze_screen()
        desc   = result.get("description", "No description")
        alarms = result.get("alarms", [])
        sw     = result.get("software", "Unknown")
        actions = result.get("actions", [])

        response = f"CV-AI Screen Analysis:\n\n{desc}"
        if alarms:
            response += f"\n\n!! ALARMS DETECTED ({len(alarms)}):"
            for a in alarms:
                response += f"\n  [{a['severity']}] {a['text']}"
        if actions:
            response += f"\n\nSuggested actions:"
            for act in actions:
                response += f"\n  - {act}"

        self._msg("agent", f"{response}\n\n")
        self._done_busy("CV-AI analysis complete!")

    # ======================================================
    # NEW MODULE 3 - PLC HARDWARE DIRECT
    # ======================================================

    def _handle_plc_hw(self, query: str):
        self._msg("action", "[PLC-DIRECT BRAIN | Hardware connection]\n")
        result = self.plc_hw.execute_command(query)
        self._msg("agent", f"{result}\n\n")
        self._done_busy("PLC hardware command sent!")

    def _plc_hw_panel(self):
        win = tk.Toplevel(self.root)
        win.title("PLC Direct Hardware Connection")
        win.geometry("650x500")
        win.configure(bg=self.C["bg"])
        tk.Label(win, text=">> PLC DIRECT HARDWARE CONNECTION",
                bg=self.C["bg"], fg=self.C["cyan"],
                font=self.F["head"]).pack(anchor="w",
                padx=16, pady=(12,4))
        active = self.plc_hw.active_count
        tk.Label(win,
                text=f"Connections: {self.plc_hw.connection_count} | Active: {active}",
                bg=self.C["bg"],
                fg=self.C["green"] if active else self.C["dim"],
                font=self.F["small"]).pack(anchor="w", padx=16)
        tk.Frame(win, bg=self.C["border"],
                height=1).pack(fill="x", padx=16, pady=8)

        # Connect form
        cf = tk.Frame(win, bg=self.C["bg"])
        cf.pack(fill="x", padx=16, pady=4)
        tk.Label(cf, text="PLC IP:",
                bg=self.C["bg"], fg=self.C["dim"],
                font=self.F["small"]).pack(side="left")
        ip_e = tk.Entry(cf, bg=self.C["input_bg"],
                       fg=self.C["white"],
                       font=self.F["small"], width=14)
        ip_e.insert(0, "192.168.1.1")
        ip_e.pack(side="left", padx=4)

        proto_v = tk.StringVar(value="modbus")
        for p, l in [("modbus","Modbus TCP"),("s7","Siemens S7")]:
            tk.Radiobutton(cf, text=l, variable=proto_v,
                          value=p, bg=self.C["bg"],
                          fg=self.C["white"],
                          selectcolor=self.C["button"],
                          font=self.F["small"]
                          ).pack(side="left", padx=4)

        result_lbl = tk.Label(win, text="",
                              bg=self.C["bg"],
                              fg=self.C["green"],
                              font=self.F["small"],
                              wraplength=600, justify="left")
        result_lbl.pack(anchor="w", padx=16, pady=4)

        def do_connect():
            ip    = ip_e.get().strip()
            proto = proto_v.get()
            port  = 102 if proto=="s7" else 502
            name  = f"PLC_{ip}"
            self.plc_hw.add_connection(name, proto, ip, port)
            ok, msg = self.plc_hw.connect(name)
            result_lbl.config(
                text=f"{'OK' if ok else 'FAILED'}: {msg}",
                fg=self.C["green"] if ok else self.C["error"])

        tk.Button(cf, text="Connect",
                 bg=self.C["cyan"], fg=self.C["bg"],
                 font=self.F["head"], relief="flat",
                 command=do_connect).pack(side="left", padx=8)

        tk.Frame(win, bg=self.C["border"],
                height=1).pack(fill="x", padx=16, pady=8)

        # Quick commands
        cmds = [
            ("Read All Tags",     "read all plc tags"),
            ("Read Register 0",   "read plc register 0"),
            ("PLC Status",        "plc direct status"),
            ("Write Test (0=1)",  "write 0 to 1"),
        ]
        for lbl, cmd in cmds:
            tk.Button(win, text=lbl,
                     bg=self.C["button"], fg=self.C["white"],
                     font=self.F["small"], relief="flat",
                     cursor="hand2",
                     command=lambda c=cmd,w=win:
                     [self._quick(c), w.destroy()]
                     ).pack(fill="x", padx=16, pady=3)

    # ======================================================
    # NEW MODULE 4 - MULTI-AGENT TEAM
    # ======================================================

    def _handle_team_task(self, query: str):
        self._msg("action",
            f"[MULTI-AGENT TEAM | Coordinating {self.team.agent_count} agents]\n")
        result = self.team.execute_team_task(query)
        self._msg("agent", f"{result}\n\n")
        self._done_busy("Team task complete!")

    def _team_panel(self):
        win = tk.Toplevel(self.root)
        win.title("Multi-Agent Team")
        win.geometry("700x520")
        win.configure(bg=self.C["bg"])
        tk.Label(win, text=">> MULTI-AGENT TEAM",
                bg=self.C["bg"], fg=self.C["cyan"],
                font=self.F["head"]).pack(anchor="w",
                padx=16, pady=(12,4))
        tk.Label(win,
                text=f"Team: {self.team.agent_count} agents | Active: {self.team.active_count}",
                bg=self.C["bg"], fg=self.C["green"],
                font=self.F["small"]).pack(anchor="w", padx=16)
        tk.Frame(win, bg=self.C["border"],
                height=1).pack(fill="x", padx=16, pady=8)

        # Agent status cards
        status = self.team.get_team_status()
        agent_colors = {
            "engineer": self.C["cyan"],
            "monitor":  self.C["green"],
            "safety":   self.C["error"],
            "analyst":  self.C["orange"],
            "operator": self.C["purple"],
        }
        cards = tk.Frame(win, bg=self.C["bg"])
        cards.pack(fill="x", padx=16, pady=4)
        for role, info in status.items():
            card = tk.Frame(cards, bg=self.C["panel"],
                           highlightbackground=agent_colors.get(
                               role, self.C["border"]),
                           highlightthickness=1,
                           padx=8, pady=6)
            card.pack(side="left", padx=4, fill="x", expand=True)
            tk.Label(card, text=info["name"],
                    bg=self.C["panel"],
                    fg=agent_colors.get(role, self.C["white"]),
                    font=self.F["small"]).pack()
            status_txt = "BUSY" if info["busy"] else "READY"
            status_col = self.C["warning"] if info["busy"] else self.C["green"]
            tk.Label(card, text=status_txt,
                    bg=self.C["panel"],
                    fg=status_col,
                    font=self.F["small"]).pack()
            tk.Label(card, text=f"Tasks: {info['tasks']}",
                    bg=self.C["panel"], fg=self.C["dim"],
                    font=self.F["small"]).pack()
            tk.Button(card, text="Assign",
                     bg=self.C["button"], fg=self.C["white"],
                     font=self.F["small"], relief="flat",
                     command=lambda r=role: self._assign_to_agent(r)
                     ).pack(pady=(4,0))

        tk.Frame(win, bg=self.C["border"],
                height=1).pack(fill="x", padx=16, pady=8)

        # Team task shortcuts
        team_tasks = [
            ("Analyze PLC and report",
             "team analyze PLC status and generate report"),
            ("Safety review + engineer fix",
             "team safety review current PLC program and fix issues"),
            ("Monitor + alert on faults",
             "team monitor screen continuously and alert on any fault"),
            ("Full system check",
             "team do complete system check and status report"),
        ]
        for lbl, cmd in team_tasks:
            tk.Button(win, text=lbl,
                     bg=self.C["button"], fg=self.C["white"],
                     font=self.F["small"], relief="flat",
                     cursor="hand2",
                     command=lambda c=cmd,w=win:
                     [self._quick(c), w.destroy()]
                     ).pack(fill="x", padx=16, pady=3)

        # Task history
        history = self.team.task_history
        if history:
            tk.Frame(win, bg=self.C["border"],
                    height=1).pack(fill="x", padx=16, pady=8)
            tk.Label(win, text="Recent team tasks:",
                    bg=self.C["bg"], fg=self.C["dim"],
                    font=self.F["small"]).pack(anchor="w", padx=16)
            for h in history[:5]:
                tk.Label(win,
                        text=f"  [{h['primary']}] {h['task'][:50]}",
                        bg=self.C["bg"], fg=self.C["dim"],
                        font=self.F["small"]).pack(anchor="w", padx=16)

    def _assign_to_agent(self, role: str):
        query = self.inp.get("1.0","end-1c").strip()
        if not query:
            import tkinter.simpledialog as sd
            query = sd.askstring(
                "Assign Task",
                f"Task for {role} agent:")
        if query:
            result = self.team.assign_to_agent(role, query)
            self._msg("action",
                f"[{role.upper()} AGENT] {result}\n\n")

    # ======================================================
    # NEW MODULE 5 - CLOUD SYNC
    # ======================================================

    def _cloud_panel(self):
        win = tk.Toplevel(self.root)
        win.title("Cloud Brain Sync")
        win.geometry("550x450")
        win.configure(bg=self.C["bg"])
        tk.Label(win, text=">> CLOUD BRAIN SYNC",
                bg=self.C["bg"], fg=self.C["cyan"],
                font=self.F["head"]).pack(anchor="w",
                padx=16, pady=(12,4))

        status = self.cloud.get_status()
        enabled_txt = "ENABLED" if status["enabled"] else "DISABLED"
        enabled_col = self.C["green"] if status["enabled"] else self.C["dim"]
        tk.Label(win,
                text=f"Status: {enabled_txt} | Last sync: {status['last_sync'] or 'Never'}",
                bg=self.C["bg"], fg=enabled_col,
                font=self.F["small"]).pack(anchor="w", padx=16)
        tk.Label(win,
                text="Privacy: Only anonymized patterns sync. No personal data shared.",
                bg=self.C["bg"], fg=self.C["dim"],
                font=self.F["small"]).pack(anchor="w", padx=16)
        tk.Frame(win, bg=self.C["border"],
                height=1).pack(fill="x", padx=16, pady=8)

        # Token setup
        tf = tk.Frame(win, bg=self.C["bg"])
        tf.pack(fill="x", padx=16, pady=4)
        tk.Label(tf, text="GitHub Token:",
                bg=self.C["bg"], fg=self.C["dim"],
                font=self.F["small"]).pack(side="left")
        token_e = tk.Entry(tf, bg=self.C["input_bg"],
                          fg=self.C["white"],
                          font=self.F["small"],
                          show="*", width=30)
        token_e.pack(side="left", padx=8)

        result_lbl = tk.Label(win, text="",
                              bg=self.C["bg"],
                              fg=self.C["green"],
                              font=self.F["small"],
                              wraplength=500)
        result_lbl.pack(padx=16, pady=8)

        def do_setup():
            token = token_e.get().strip()
            if not token:
                result_lbl.config(
                    text="Enter GitHub token first",
                    fg=self.C["error"])
                return
            result = self.cloud.setup(token, enable=True)
            result_lbl.config(text=result,
                             fg=self.C["green"])

        def do_sync():
            result = self.cloud.sync_now()
            result_lbl.config(text=result,
                             fg=self.C["green"])

        def do_disable():
            self.cloud.disable()
            result_lbl.config(text="Cloud sync disabled",
                             fg=self.C["warning"])

        btns = tk.Frame(win, bg=self.C["bg"])
        btns.pack(fill="x", padx=16, pady=4)
        tk.Button(btns, text="Enable Sync",
                 bg=self.C["cyan"], fg=self.C["bg"],
                 font=self.F["head"], relief="flat",
                 command=do_setup).pack(side="left", padx=4)
        tk.Button(btns, text="Sync Now",
                 bg=self.C["button"], fg=self.C["white"],
                 font=self.F["small"], relief="flat",
                 command=do_sync).pack(side="left", padx=4)
        tk.Button(btns, text="Disable",
                 bg=self.C["error"], fg=self.C["white"],
                 font=self.F["small"], relief="flat",
                 command=do_disable).pack(side="left", padx=4)

        tk.Frame(win, bg=self.C["border"],
                height=1).pack(fill="x", padx=16, pady=8)

        # Privacy info
        tk.Label(win,
                text="What gets synced (privacy-safe):",
                bg=self.C["bg"], fg=self.C["dim"],
                font=self.F["small"]).pack(anchor="w", padx=16)
        safe_items = [
            "OK - Anonymized command patterns (no personal data)",
            "OK - Brain usage statistics (anonymous)",
            "OK - Automation template types",
            "X  - Never: PLC IP addresses or credentials",
            "X  - Never: Tag values or process data",
            "X  - Never: File contents or company data",
        ]
        for item in safe_items:
            col = (self.C["green"] if item.startswith("OK")
                  else self.C["error"])
            tk.Label(win, text=f"  {item}",
                    bg=self.C["bg"], fg=col,
                    font=self.F["small"]).pack(anchor="w", padx=16)

        # Get token link
        tk.Label(win,
                text="Get GitHub token: github.com/settings/tokens",
                bg=self.C["bg"], fg=self.C["cyan"],
                font=self.F["small"],
                cursor="hand2").pack(anchor="w", padx=16, pady=8)

    # ======================================================
    # FEATURE 1 - SELF-HEALING SYSTEM
    # ======================================================

    def _heal_panel(self):
        win = tk.Toplevel(self.root)
        win.title("Self-Healing System")
        win.geometry("600x450")
        win.configure(bg=self.C["bg"])
        report = self.healer.get_health_report()
        tk.Label(win, text=">> SELF-HEALING SYSTEM",
                bg=self.C["bg"], fg=self.C["cyan"],
                font=self.F["head"]).pack(anchor="w", padx=16, pady=12)
        health = report["health_score"]
        color  = (self.C["green"] if health > 80
                 else self.C["warning"] if health > 50
                 else self.C["error"])
        tk.Label(win,
                text=f"System Health: {health}% | "
                     f"Errors: {report['total_errors']} | "
                     f"Auto-fixed: {report['fixed']} ({report['fix_rate']}%)",
                bg=self.C["bg"], fg=color,
                font=self.F["small"]).pack(anchor="w", padx=16)
        tk.Frame(win, bg=self.C["border"],
                height=1).pack(fill="x", padx=16, pady=8)

        # Health bar
        bar_f = tk.Frame(win, bg=self.C["border"], height=20)
        bar_f.pack(fill="x", padx=16, pady=4)
        bar_f.pack_propagate(False)
        fill_w = int(health / 100 * (win.winfo_reqwidth() - 32))
        tk.Frame(bar_f, bg=color, width=max(fill_w, 4)).pack(
            side="left", fill="y")

        # Recent errors
        tk.Label(win, text="Recent Errors (auto-fixed where possible):",
                bg=self.C["bg"], fg=self.C["dim"],
                font=self.F["small"]).pack(anchor="w", padx=16, pady=(8,4))
        for err in report["recent_errors"][-5:]:
            fixed_txt = "OK Fixed" if err["fixed"] else "!! Not fixed"
            fixed_col = self.C["green"] if err["fixed"] else self.C["error"]
            rf = tk.Frame(win, bg=self.C["panel"], pady=3)
            rf.pack(fill="x", padx=16, pady=2)
            tk.Label(rf, text=f"[{err['type']}]",
                    bg=self.C["panel"], fg=self.C["orange"],
                    font=self.F["small"], width=25,
                    anchor="w").pack(side="left", padx=6)
            tk.Label(rf, text=fixed_txt,
                    bg=self.C["panel"], fg=fixed_col,
                    font=self.F["small"]).pack(side="right", padx=6)

        # Fixes applied
        if report["fixes_applied"]:
            tk.Label(win, text="Fixes Applied by Type:",
                    bg=self.C["bg"], fg=self.C["dim"],
                    font=self.F["small"]).pack(anchor="w", padx=16, pady=(8,4))
            for err_type, count in report["fixes_applied"].items():
                tk.Label(win, text=f"  {err_type}: {count} fix(es)",
                        bg=self.C["bg"], fg=self.C["green"],
                        font=self.F["small"]).pack(anchor="w", padx=16)

    # ======================================================
    # FEATURE 2 - NL PLC COMPILER
    # ======================================================

    def _handle_nl_plc(self, query: str):
        self._msg("action", "[NL-PLC COMPILER]\n")
        llm_cb = lambda brain, q: self._ask(brain, q)
        q = query.lower()
        for w in ["create plc program","write plc","generate ladder",
                  "plc program for","program to control","nl plc"]:
            q = q.replace(w,"").strip()
        prog = self.nl_plc.compile(q or query, f"GP_Program_{self._qcount}")
        path = self.nl_plc.save_program(prog)
        # Auto-document it
        self.auto_doc.document_plc_program(
            prog.name, prog.st_code,
            prog.variables, prog.description)

        response = (f"PLC Program Generated!\n\n"
                   f"Name: {prog.name}\n"
                   f"Variables: {len(prog.variables)}\n"
                   f"Rungs: {len(prog.rungs)}\n"
                   f"Saved to: {path}\n\n"
                   f"Preview (ST Code):\n"
                   + prog.st_code[:300])
        self._msg("agent", f"{response}\n\n")
        self._done_busy("PLC program generated!")

    def _nlplc_panel(self):
        win = tk.Toplevel(self.root)
        win.title("NL-PLC Compiler")
        win.geometry("650x500")
        win.configure(bg=self.C["bg"])
        tk.Label(win, text=">> NATURAL LANGUAGE PLC COMPILER",
                bg=self.C["bg"], fg=self.C["cyan"],
                font=self.F["head"]).pack(anchor="w", padx=16, pady=12)
        tk.Label(win,
                text="Describe your PLC program in English. AI generates IEC 61131-3 code.",
                bg=self.C["bg"], fg=self.C["dim"],
                font=self.F["small"]).pack(anchor="w", padx=16)
        tk.Frame(win, bg=self.C["border"],
                height=1).pack(fill="x", padx=16, pady=8)

        examples = [
            "Motor start stop with E-stop and fault protection",
            "Count 100 parts then stop conveyor and alarm",
            "Temperature PID control for furnace setpoint 350C",
            "Safety circuit with dual E-stop and light curtain",
            "5-step sequence for filling machine",
        ]
        tk.Label(win, text="Quick Templates:",
                bg=self.C["bg"], fg=self.C["dim"],
                font=self.F["small"]).pack(anchor="w", padx=16)
        for ex in examples:
            tk.Button(win, text=ex[:55],
                     bg=self.C["button"], fg=self.C["white"],
                     font=self.F["small"], relief="flat", anchor="w",
                     command=lambda e=ex,w=win:
                     [self._quick(f"create plc program {e}"), w.destroy()]
                     ).pack(fill="x", padx=16, pady=2)

        tk.Frame(win, bg=self.C["border"],
                height=1).pack(fill="x", padx=16, pady=8)
        tk.Label(win, text="Custom description:",
                bg=self.C["bg"], fg=self.C["dim"],
                font=self.F["small"]).pack(anchor="w", padx=16)
        desc = tk.Text(win, bg=self.C["input_bg"],
                      fg=self.C["white"], font=self.F["body"],
                      height=5, wrap=tk.WORD,
                      insertbackground=self.C["cyan"],
                      borderwidth=0, highlightthickness=1,
                      highlightcolor=self.C["cyan"],
                      highlightbackground=self.C["border"],
                      padx=8, pady=8)
        desc.pack(fill="x", padx=16, pady=4)
        desc.insert("1.0", "Motor with start button, stop button, "
                   "fault input, run output and indicator lamp")
        tk.Button(win, text=">> COMPILE PLC PROGRAM",
                 bg=self.C["cyan"], fg=self.C["bg"],
                 font=self.F["head"], relief="flat",
                 command=lambda: [
                     self._quick(f"create plc program {desc.get('1.0','end-1c').strip()}"),
                     win.destroy()
                 ]).pack(pady=12, ipadx=20, ipady=4)

    # ======================================================
    # FEATURE 3 - PREDICTIVE MAINTENANCE
    # ======================================================

    def _handle_maint_query(self, query: str):
        self._msg("action", "[PREDICTIVE MAINTENANCE AI]\n")
        health  = self.pred_maint.get_health_report()
        sched   = self.pred_maint.get_maintenance_schedule()
        report  = self.reporter.generate_maintenance_report(health, sched)
        path    = self.reporter.save_as_html(report)

        response = "Equipment Health Report:\n\n"
        for eq in health:
            h = eq.get("health_score", 100)
            status = "OK" if h > 80 else "!!" if h > 50 else "CRITICAL"
            response += (f"{status} {eq.get('name','?')}: "
                        f"Health={h:.0f}% "
                        f"Failure={eq.get('failure_prob',0):.1f}%\n")
        if sched:
            response += f"\nMaintenance needed ({len(sched)} items):\n"
            for s in sched[:5]:
                response += (f"  [{s['urgency']}] {s['equipment']}: "
                            f"{s.get('days_until','?')} days\n")
        response += f"\nFull report: {path}"
        self._msg("agent", f"{response}\n\n")
        self._done_busy("Maintenance report generated!")

    def _maint_panel(self):
        win = tk.Toplevel(self.root)
        win.title("Predictive Maintenance")
        win.geometry("750x550")
        win.configure(bg=self.C["bg"])
        tk.Label(win, text=">> PREDICTIVE MAINTENANCE AI",
                bg=self.C["bg"], fg=self.C["cyan"],
                font=self.F["head"]).pack(anchor="w", padx=16, pady=12)

        health = self.pred_maint.get_health_report()
        sched  = self.pred_maint.get_maintenance_schedule()

        # Equipment cards
        cards = tk.Frame(win, bg=self.C["bg"])
        cards.pack(fill="x", padx=16, pady=4)

        for eq in health:
            h     = eq.get("health_score", 100)
            color = (self.C["green"] if h > 80
                    else self.C["warning"] if h > 50
                    else self.C["error"])
            card  = tk.Frame(cards, bg=self.C["panel"],
                            highlightbackground=color,
                            highlightthickness=1,
                            padx=8, pady=8)
            card.pack(side="left", padx=4, fill="x", expand=True)
            tk.Label(card, text=eq.get("name","?"),
                    bg=self.C["panel"], fg=color,
                    font=self.F["small"]).pack()
            tk.Label(card, text=f"{h:.0f}%",
                    bg=self.C["panel"], fg=color,
                    font=("Consolas",20,"bold")).pack()
            days = eq.get("est_failure")
            info = f"Fail: {days}d" if days else "Normal"
            tk.Label(card, text=info,
                    bg=self.C["panel"], fg=self.C["dim"],
                    font=self.F["small"]).pack()

        if sched:
            tk.Frame(win, bg=self.C["border"],
                    height=1).pack(fill="x", padx=16, pady=8)
            tk.Label(win, text="Maintenance Schedule:",
                    bg=self.C["bg"], fg=self.C["cyan"],
                    font=self.F["head"]).pack(anchor="w", padx=16)
            for s in sched:
                urg_col = (self.C["error"] if s["urgency"]=="IMMEDIATE"
                          else self.C["warning"] if s["urgency"]=="SOON"
                          else self.C["green"])
                rf = tk.Frame(win, bg=self.C["panel"], pady=3)
                rf.pack(fill="x", padx=16, pady=2)
                tk.Label(rf, text=f"[{s['urgency']}]",
                        bg=self.C["panel"], fg=urg_col,
                        font=self.F["small"], width=12).pack(side="left",padx=6)
                tk.Label(rf, text=s["equipment"],
                        bg=self.C["panel"], fg=self.C["white"],
                        font=self.F["small"], width=20,
                        anchor="w").pack(side="left")
                days = f"in {s.get('days_until','?')} days" if s.get("days_until") else "ASAP"
                tk.Label(rf, text=days,
                        bg=self.C["panel"], fg=self.C["dim"],
                        font=self.F["small"]).pack(side="right", padx=6)

        tk.Frame(win, bg=self.C["border"],
                height=1).pack(fill="x", padx=16, pady=8)
        tk.Button(win, text="Generate Full Report",
                 bg=self.C["cyan"], fg=self.C["bg"],
                 font=self.F["head"], relief="flat",
                 command=lambda: self._quick("generate maintenance report")
                 ).pack(padx=16, pady=4, ipadx=12, ipady=4)

    # ======================================================
    # FEATURE 4 - DIGITAL TWIN
    # ======================================================

    def _handle_twin_query(self, query: str):
        self._msg("action", "[DIGITAL TWIN SIMULATOR]\n")
        q = query.lower()
        if "run scenario" in q or "test" in q:
            scenarios = {
                "normal": "normal_start",
                "estop": "estop_test",
                "fault": "fault_test",
            }
            for key, sc_id in scenarios.items():
                if key in q:
                    result = self.twin.run_scenario(sc_id)
                    status = "PASSED" if result.get("passed") else "FAILED"
                    response = (f"Scenario: {result.get('scenario','?')}\n"
                               f"Result: {status}\n\nSteps:\n")
                    for step in result.get("steps",[]):
                        if "check" in step:
                            ok = "OK" if step.get("passed") else "FAIL"
                            response += f"  [{ok}] {step['check']}\n"
                        else:
                            response += f"  Set {step.get('tag','?')} = {step.get('value','?')}\n"
                    self._msg("agent", f"{response}\n\n")
                    self._done_busy(f"Scenario {status}")
                    return

        # Show current state
        status = self.twin.get_status()
        tags   = status.get("process_tags", {})
        response = "Digital Twin Status:\n\n"
        response += f"PLC: {'Running' if status['plc_status']['running'] else 'Stopped'}\n"
        response += f"Scans: {status['plc_status']['scan_count']}\n\n"
        response += "Process Values:\n"
        for tag, val in list(tags.items())[:8]:
            response += f"  {tag}: {val}\n"
        response += "\nScenarios: " + ", ".join(status.get("scenarios",[]))
        self._msg("agent", f"{response}\n\n")
        self._done_busy("Twin status shown!")

    def _twin_panel(self):
        win = tk.Toplevel(self.root)
        win.title("Digital Twin Simulator")
        win.geometry("700x520")
        win.configure(bg=self.C["bg"])
        tk.Label(win, text=">> DIGITAL TWIN SIMULATOR",
                bg=self.C["bg"], fg=self.C["cyan"],
                font=self.F["head"]).pack(anchor="w", padx=16, pady=12)
        status = self.twin.get_status()
        running = status["plc_status"]["running"]
        tk.Label(win,
                text=f"Simulation: {'RUNNING' if running else 'STOPPED'} | "
                     f"Scans: {status['plc_status']['scan_count']}",
                bg=self.C["bg"],
                fg=self.C["green"] if running else self.C["error"],
                font=self.F["small"]).pack(anchor="w", padx=16)
        tk.Frame(win, bg=self.C["border"],
                height=1).pack(fill="x", padx=16, pady=8)

        # Tag editor
        tag_f = tk.Frame(win, bg=self.C["bg"])
        tag_f.pack(fill="x", padx=16, pady=4)
        tags  = status.get("process_tags", {})

        self._twin_vars = {}
        bool_tags  = {k:v for k,v in tags.items() if isinstance(v, bool)}
        float_tags = {k:v for k,v in tags.items() if isinstance(v, float)}

        # Bool toggles
        tk.Label(tag_f, text="Boolean Inputs:",
                bg=self.C["bg"], fg=self.C["dim"],
                font=self.F["small"]).grid(row=0, column=0,
                columnspan=4, sticky="w", pady=(0,4))
        col = 0
        for i, (tag, val) in enumerate(list(bool_tags.items())[:6]):
            var = tk.BooleanVar(value=val)
            self._twin_vars[tag] = var
            cb = tk.Checkbutton(tag_f, text=tag,
                               variable=var,
                               bg=self.C["bg"],
                               fg=self.C["white"],
                               selectcolor=self.C["button"],
                               activebackground=self.C["bg"],
                               font=self.F["small"],
                               command=lambda t=tag, v=var:
                               self.twin.set_input(t, v.get()))
            cb.grid(row=1+i//4, column=i%4, sticky="w", padx=8)

        # Scenarios
        tk.Frame(win, bg=self.C["border"],
                height=1).pack(fill="x", padx=16, pady=8)
        tk.Label(win, text="Test Scenarios:",
                bg=self.C["bg"], fg=self.C["cyan"],
                font=self.F["head"]).pack(anchor="w", padx=16)
        for sc_id in status.get("scenarios",[]):
            tk.Button(win, text=f"Run: {sc_id.replace('_',' ').title()}",
                     bg=self.C["button"], fg=self.C["white"],
                     font=self.F["small"], relief="flat", cursor="hand2",
                     command=lambda s=sc_id,w=win:
                     [self._quick(f"simulate run scenario {s}"),w.destroy()]
                     ).pack(fill="x", padx=16, pady=3)

        # Live values display
        tk.Frame(win, bg=self.C["border"],
                height=1).pack(fill="x", padx=16, pady=8)
        tk.Label(win, text="Live Process Values:",
                bg=self.C["bg"], fg=self.C["cyan"],
                font=self.F["head"]).pack(anchor="w", padx=16)

        val_frame = tk.Frame(win, bg=self.C["bg"])
        val_frame.pack(fill="x", padx=16)
        self._twin_lbls = {}
        for i, (tag, val) in enumerate(list(float_tags.items())[:4]):
            rf = tk.Frame(val_frame, bg=self.C["panel"], padx=8, pady=4)
            rf.grid(row=i//2, column=i%2, padx=4, pady=2, sticky="ew")
            tk.Label(rf, text=tag, bg=self.C["panel"],
                    fg=self.C["dim"], font=self.F["small"]).pack(side="left")
            lbl = tk.Label(rf, text=f"{val:.2f}",
                          bg=self.C["panel"], fg=self.C["cyan"],
                          font=("Consolas",12,"bold"))
            lbl.pack(side="right")
            self._twin_lbls[tag] = lbl

        def update_vals():
            if not win.winfo_exists():
                return
            vals = self.twin.get_all_values()
            for tag, lbl in self._twin_lbls.items():
                v = vals.get(tag)
                if v is not None:
                    lbl.config(text=f"{v:.2f}" if isinstance(v,float) else str(v))
            win.after(1000, update_vals)
        update_vals()

    # ======================================================
    # FEATURE 5 - REPORT GENERATOR
    # ======================================================

    def _handle_report_query(self, query: str):
        self._msg("action", "[REPORT GENERATOR]\n")
        path = self.reporter.quick_report(
            query, query,
            lambda brain, q: self._ask(brain, q))
        self._msg("agent",
            f"Report generated!\nFile: {path}\n"
            f"Opening in browser...\n\n")
        self.auto_doc.open_document(path)
        self._done_busy("Report ready!")

    def _report_panel(self):
        win = tk.Toplevel(self.root)
        win.title("Report Generator")
        win.geometry("600x450")
        win.configure(bg=self.C["bg"])
        tk.Label(win, text=">> PROFESSIONAL REPORT GENERATOR",
                bg=self.C["bg"], fg=self.C["cyan"],
                font=self.F["head"]).pack(anchor="w", padx=16, pady=12)
        tk.Frame(win, bg=self.C["border"],
                height=1).pack(fill="x", padx=16, pady=8)
        reports = [
            ("Maintenance Report",    "generate maintenance report for all equipment"),
            ("Alarm Analysis Report", "generate alarm analysis report for last 24 hours"),
            ("PLC Status Report",     "generate plc status report"),
            ("Session Summary",       "generate report of this session"),
            ("Equipment Health PDF",  "generate report equipment health pdf"),
        ]
        for lbl, cmd in reports:
            tk.Button(win, text=lbl,
                     bg=self.C["button"], fg=self.C["white"],
                     font=self.F["small"], relief="flat", cursor="hand2",
                     command=lambda c=cmd,w=win:
                     [self._quick(c), w.destroy()]
                     ).pack(fill="x", padx=16, pady=4)

        tk.Frame(win, bg=self.C["border"],
                height=1).pack(fill="x", padx=16, pady=8)
        tk.Label(win, text="Custom Report:",
                bg=self.C["bg"], fg=self.C["dim"],
                font=self.F["small"]).pack(anchor="w", padx=16)
        e = tk.Entry(win, bg=self.C["input_bg"],
                    fg=self.C["white"], font=self.F["input"])
        e.insert(0, "Describe the report you need")
        e.pack(fill="x", padx=16, pady=4)
        tk.Button(win, text="Generate Report",
                 bg=self.C["cyan"], fg=self.C["bg"],
                 font=self.F["head"], relief="flat",
                 command=lambda: [
                     self._quick(f"generate report {e.get()}"),
                     win.destroy()
                 ]).pack(pady=8, ipadx=16, ipady=4)

    # ======================================================
    # FEATURE 6 - GESTURE CONTROL
    # ======================================================

    def _gesture_panel(self):
        win = tk.Toplevel(self.root)
        win.title("Gesture Control")
        win.geometry("550x450")
        win.configure(bg=self.C["bg"])
        tk.Label(win, text=">> GESTURE CONTROL",
                bg=self.C["bg"], fg=self.C["cyan"],
                font=self.F["head"]).pack(anchor="w", padx=16, pady=12)
        is_on = self.gesture.is_running
        tk.Label(win,
                text=f"Status: {'ACTIVE' if is_on else 'INACTIVE'}",
                bg=self.C["bg"],
                fg=self.C["green"] if is_on else self.C["dim"],
                font=self.F["small"]).pack(anchor="w", padx=16)
        tk.Label(win,
                text="Requires webcam. Install mediapipe for full gesture support.",
                bg=self.C["bg"], fg=self.C["dim"],
                font=self.F["small"]).pack(anchor="w", padx=16)
        tk.Frame(win, bg=self.C["border"],
                height=1).pack(fill="x", padx=16, pady=8)

        result_lbl = tk.Label(win, text="",
                              bg=self.C["bg"],
                              fg=self.C["green"],
                              font=self.F["small"])
        result_lbl.pack(anchor="w", padx=16, pady=4)

        def toggle():
            if self.gesture.is_running:
                self.gesture.stop()
                result_lbl.config(text="Gesture control stopped",
                                 fg=self.C["warning"])
            else:
                ok, msg = self.gesture.start()
                result_lbl.config(text=msg,
                                 fg=self.C["green"] if ok else self.C["error"])
        tk.Button(win,
                 text="Stop Gesture Control" if is_on else "Start Gesture Control",
                 bg=self.C["error"] if is_on else self.C["cyan"],
                 fg=self.C["white"] if is_on else self.C["bg"],
                 font=self.F["head"], relief="flat",
                 command=toggle).pack(padx=16, pady=8, ipadx=12)

        # Gesture reference
        tk.Frame(win, bg=self.C["border"],
                height=1).pack(fill="x", padx=16, pady=8)
        tk.Label(win, text="Gesture Reference:",
                bg=self.C["bg"], fg=self.C["cyan"],
                font=self.F["head"]).pack(anchor="w", padx=16)
        for g in self.gesture.get_gesture_list()[:8]:
            rf = tk.Frame(win, bg=self.C["panel"], pady=2)
            rf.pack(fill="x", padx=16, pady=1)
            tk.Label(rf, text=g["gesture"].replace("_"," ").title(),
                    bg=self.C["panel"], fg=self.C["orange"],
                    font=self.F["small"], width=16,
                    anchor="w").pack(side="left", padx=6)
            tk.Label(rf, text=g["custom"] or g["default"],
                    bg=self.C["panel"], fg=self.C["white"],
                    font=self.F["small"],
                    anchor="w").pack(side="left", padx=4)

    # ======================================================
    # FEATURE 8 - AUTO DOCUMENTATION
    # ======================================================

    def _handle_autodoc(self, query: str):
        self._msg("action", "[AUTO-DOCUMENTATION]\n")
        q = query.lower()
        if "session" in q:
            history = [{"query": h.get("query",""),
                       "brain": h.get("brain","?")}
                      for h in self.auto_agent.get_activity_log()[:20]]
            path = self.auto_doc.document_session(history)
            self._msg("agent",
                f"Session documented!\nFile: {path}\n\n")
        else:
            docs = self.auto_doc.list_documents()
            response = f"Auto-Documentation System\n\nDocuments ({len(docs)}):\n"
            for d in docs[:10]:
                response += f"  {d['name']} ({d['size']}B) - {d['modified']}\n"
            self._msg("agent", f"{response}\n\n")
        self._done_busy("Documentation complete!")

    def _autodoc_panel(self):
        win = tk.Toplevel(self.root)
        win.title("Auto Documentation")
        win.geometry("650x480")
        win.configure(bg=self.C["bg"])
        tk.Label(win, text=">> AUTO-DOCUMENTATION SYSTEM",
                bg=self.C["bg"], fg=self.C["cyan"],
                font=self.F["head"]).pack(anchor="w", padx=16, pady=12)
        tk.Label(win,
                text="Automatically generates documentation from your work.",
                bg=self.C["bg"], fg=self.C["dim"],
                font=self.F["small"]).pack(anchor="w", padx=16)
        tk.Frame(win, bg=self.C["border"],
                height=1).pack(fill="x", padx=16, pady=8)

        actions = [
            ("Document This Session",  "document this session"),
            ("Document PLC Programs",  "auto document plc programs"),
            ("Generate User Manual",   "create manual for this system"),
        ]
        for lbl, cmd in actions:
            tk.Button(win, text=lbl,
                     bg=self.C["button"], fg=self.C["white"],
                     font=self.F["small"], relief="flat", cursor="hand2",
                     command=lambda c=cmd,w=win:
                     [self._quick(c), w.destroy()]
                     ).pack(fill="x", padx=16, pady=4)

        tk.Frame(win, bg=self.C["border"],
                height=1).pack(fill="x", padx=16, pady=8)
        tk.Label(win, text="Recent Documents:",
                bg=self.C["bg"], fg=self.C["cyan"],
                font=self.F["head"]).pack(anchor="w", padx=16)
        docs = self.auto_doc.list_documents()
        for d in docs[:8]:
            rf = tk.Frame(win, bg=self.C["panel"], pady=3)
            rf.pack(fill="x", padx=16, pady=2)
            tk.Label(rf, text=d["name"][:40],
                    bg=self.C["panel"], fg=self.C["white"],
                    font=self.F["small"], anchor="w",
                    width=40).pack(side="left", padx=6)
            tk.Label(rf, text=d["modified"],
                    bg=self.C["panel"], fg=self.C["dim"],
                    font=self.F["small"]).pack(side="left", padx=4)
            tk.Button(rf, text="Open",
                     bg=self.C["cyan"], fg=self.C["bg"],
                     font=self.F["small"], relief="flat",
                     command=lambda p=d["path"]:
                     self.auto_doc.open_document(p)
                     ).pack(side="right", padx=6)
