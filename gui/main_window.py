import tkinter as tk
from tkinter import ttk, scrolledtext
import threading, time, sys, os, json, gc, subprocess, shutil
from pathlib import Path
BASE = Path(__file__).parent.parent
sys.path.insert(0, str(BASE))
from config.settings import Settings
from config.models import MODELS, CHAT_MODELS

# ── Expert Knowledge (instant answers, no model needed) ───────
KNOWLEDGE = {
    "plc": """PLC LADDER LOGIC — Expert Answer:

BASIC ELEMENTS:
• XIC (Examine If Closed)  = NO Contact — bit=1 to pass
• XIO (Examine If Open)    = NC Contact — bit=0 to pass
• OTE (Output Energize)    = Coil — sets bit when rung true
• OTL (Output Latch)       = Latches ON permanently
• OTU (Output Unlatch)     = Unlatches output

TIMERS:
• TON — Timer On-Delay    (delays turning ON)
• TOF — Timer Off-Delay   (delays turning OFF)
• RTO — Retentive Timer   (holds value on power loss)

COUNTERS:
• CTU — Count Up    • CTD — Count Down    • RES — Reset

PLC BRANDS:
• Allen Bradley  → Studio 5000 / RSLogix 5000
• Siemens        → TIA Portal S7-1200/1500
• Schneider      → Unity Pro / Modicon M340
• Mitsubishi     → GX Works / MELSEC iQ

NETWORKS: Modbus TCP/RTU | Profibus | Profinet | EtherNet/IP | OPC-UA""",

    "safety": """SAFETY ENGINEERING — Expert Answer:

EMERGENCY STOP:
• Must be NC (Normally Closed) hardwired in series
• Cannot be software controlled alone
• Requires manual reset after activation
• Category 0: immediate power removal
• Category 1: controlled stop then power off

SAFETY INTEGRITY LEVELS:
• SIL 1: Risk reduction 10-100x
• SIL 2: Risk reduction 100-1000x
• SIL 3: Risk reduction 1000-10000x

LOTO PROCEDURE:
1. Notify personnel  2. Identify energy sources
3. Isolate sources   4. Lock and Tag all points
5. Release stored energy  6. Verify de-energized
7. Perform work  8. Remove locks reverse order

STANDARDS: IEC 61508 | IEC 61511 | ISO 13849 | IEC 62061""",

    "screen": """GUI AUTOMATION — Expert Answer:

PYAUTOGUI COMMANDS:
• pyautogui.click(x, y)              — Left click
• pyautogui.doubleClick(x, y)        — Double click
• pyautogui.rightClick(x, y)         — Right click
• pyautogui.moveTo(x, y, duration=1) — Move mouse
• pyautogui.typewrite('hello')       — Type text
• pyautogui.press('enter')           — Press key
• pyautogui.hotkey('ctrl','c')       — Key combo
• pyautogui.screenshot()             — Capture screen
• pyautogui.locateOnScreen('img.png')— Find element

FIND COORDINATES:
Open any app → move mouse → check taskbar for X,Y coords

WINDOWS SHORTCUTS:
Win+R=Run | Win+E=Explorer | Ctrl+Shift+Esc=TaskMgr""",

    "code": """PYTHON EXPERT — Code Answer:

BEST PRACTICES:
• Virtual env: python -m venv env && env/Scripts/activate
• Exception handling: try/except with specific types
• Type hints: def func(x: int) -> str:
• Follow PEP8 style guide always

COMMON PATTERNS:
# Read file safely
with open('file.txt', 'r') as f:
    content = f.read()

# Error handling
try:
    result = risky_function()
except ValueError as e:
    print(f'Error: {e}')

# List comprehension
squares = [x**2 for x in range(10)]

# GUI automation
import pyautogui
pyautogui.click(100, 200)
pyautogui.typewrite('hello world')""",

    "math": """ENGINEERING CALCULATOR:

ELECTRICAL:
• Ohm's Law:    V = I × R
• Power:        P = V × I = I²R = V²/R
• 4-20mA:       Value% = (mA-4) / 16 × 100

UNIT CONVERSIONS:
• PSI → Bar:    Bar = PSI × 0.0689
• Bar → PSI:    PSI = Bar × 14.504
• °C  → °F:     F = (C × 9/5) + 32
• °F  → °C:     C = (F-32) × 5/9
• kPa → PSI:    PSI = kPa × 0.14504

PID FORMULA:
Output = Kp×e + Ki∫e dt + Kd×(de/dt)

Please provide specific values to calculate.""",

    "open": """OPENING SOFTWARE — Expert Answer:

I can open software on your PC automatically!
Tell me the software name and I will open it.

EXAMPLES YOU CAN SAY:
• 'Open Notepad'
• 'Open PCWin'
• 'Open RSLogix'
• 'Open Calculator'
• 'Open File Explorer'
• 'Open Task Manager'

I will use Windows commands to open it directly.
Just say: OPEN [software name]""",

    "default": """GP PRO AGENT — Ready to Help!

I am specialized in:
• PLC & Industrial Automation (ladder logic, SCADA)
• GUI & Screen Automation (pyautogui, screen reading)
• Software Learning & Operation (open any software)
• Engineering Calculations (formulas, conversions)
• Safety Systems (SIL, LOTO, E-stop)
• Python Code Writing & Debugging

QUICK COMMANDS:
• 'Open [software]'     — Opens any software
• 'Change theme to blue'— Changes UI color
• 'Make font bigger'    — Increases font size
• Click 'PLC Basics'    — PLC expert answer
• Click 'Safety Check'  — Safety protocols

Ask me anything specific!"""
}

# ── Software launcher map ──────────────────────────────────
SOFTWARE_MAP = {
    "notepad":        "notepad.exe",
    "calculator":     "calc.exe",
    "paint":          "mspaint.exe",
    "explorer":       "explorer.exe",
    "file explorer":  "explorer.exe",
    "task manager":   "taskmgr.exe",
    "cmd":            "cmd.exe",
    "command prompt": "cmd.exe",
    "control panel":  "control.exe",
    "registry":       "regedit.exe",
    "pcwin":          "PCWin.exe",
    "rslogix":        "Studio5000Launcher.exe",
    "studio 5000":    "Studio5000Launcher.exe",
    "tia portal":     "TIA Portal.exe",
    "word":           "winword.exe",
    "excel":          "excel.exe",
    "chrome":         "chrome.exe",
    "firefox":        "firefox.exe",
    "edge":           "msedge.exe",
    "vlc":            "vlc.exe",
    "vs code":        "code.exe",
    "vscode":         "code.exe",
}


class MainWindow:
    def __init__(self):
        self.settings  = Settings()
        self.settings.ensure_dirs()
        self._busy     = False
        self._paused   = False
        self._qcount   = 0
        self._ttime    = 0.0
        self._llm      = None
        self._llm_key  = None
        self._minimized= False
        self._overlay  = None
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
        self._setup()
        self._build()

    def _setup(self):
        self.root = tk.Tk()
        self.root.title("GP PRO AGENT v1.0.0")
        self.root.geometry("1300x850")
        self.root.minsize(1000,650)
        self.root.configure(bg=self.C["bg"])
        self.root.grid_rowconfigure(0,weight=1)
        self.root.grid_columnconfigure(0,weight=1)
        self.root.update_idletasks()
        x=(self.root.winfo_screenwidth()-1300)//2
        y=(self.root.winfo_screenheight()-850)//2
        self.root.geometry(f"1300x850+{x}+{y}")

    def _build(self):
        m=tk.Frame(self.root,bg=self.C["bg"])
        m.grid(row=0,column=0,sticky="nsew",padx=8,pady=8)
        m.grid_rowconfigure(1,weight=1)
        m.grid_columnconfigure(0,weight=3)
        m.grid_columnconfigure(1,weight=1)
        self._main = m
        self._build_header(m)
        self._build_chat(m)
        self._build_sidebar(m)
        self._build_input(m)
        self._chat("system","◈ GP PRO AGENT v1.0.0 — Online\n")
        self._chat("system","◈ 11 AI Brains | PLC | GUI Automation | Software Learning\n")
        self._chat("system","◈ Say: 'Open Notepad' | 'Change theme to blue' | 'PLC ladder logic'\n\n")
        threading.Thread(target=self._check_models,daemon=True).start()

    def _build_header(self,p):
        h=tk.Frame(p,bg=self.C["panel"],highlightbackground=self.C["border"],highlightthickness=1)
        h.grid(row=0,column=0,columnspan=2,sticky="ew",pady=(0,4))
        h.grid_columnconfigure(2,weight=1)
        tk.Label(h,text="⬡ GP PRO AGENT",bg=self.C["panel"],fg=self.C["cyan"],font=self.F["title"]).grid(row=0,column=0,padx=16,pady=8)
        tk.Label(h,text="PLC | GUI Automation | Software Learning | Offline",bg=self.C["panel"],fg=self.C["dim"],font=self.F["small"]).grid(row=0,column=1,padx=4,sticky="w")
        tk.Frame(h,bg=self.C["panel"]).grid(row=0,column=2,sticky="ew")
        self.ram_lbl=tk.Label(h,text="RAM:--",bg=self.C["panel"],fg=self.C["green"],font=self.F["small"])
        self.ram_lbl.grid(row=0,column=3,padx=4)
        self.priority=tk.StringVar(value="balanced")
        pf=tk.Frame(h,bg=self.C["panel"])
        pf.grid(row=0,column=4,padx=8)
        for v,l in [("speed","⚡Speed"),("balanced","⚖Bal"),("accuracy","🎯Acc")]:
            tk.Radiobutton(pf,text=l,variable=self.priority,value=v,bg=self.C["panel"],fg=self.C["white"],selectcolor=self.C["button"],activebackground=self.C["panel"],font=self.F["small"]).pack(side="left",padx=2)
        # Minimize button
        tk.Button(h,text="⊟ Mini",bg=self.C["button"],fg=self.C["white"],font=self.F["small"],relief="flat",cursor="hand2",command=self._toggle_mini).grid(row=0,column=5,padx=4)
        # Download manager button
        tk.Button(h,text="⬇ Models",bg=self.C["button"],fg=self.C["cyan"],font=self.F["small"],relief="flat",cursor="hand2",command=self._open_download_manager).grid(row=0,column=6,padx=4)

    def _build_chat(self,p):
        f=tk.Frame(p,bg=self.C["panel"],highlightbackground=self.C["border"],highlightthickness=1)
        f.grid(row=1,column=0,sticky="nsew",padx=(0,4),pady=4)
        f.grid_rowconfigure(1,weight=1)
        f.grid_columnconfigure(0,weight=1)
        tk.Label(f,text="◈ CONVERSATION",bg=self.C["panel"],fg=self.C["cyan"],font=self.F["head"]).grid(row=0,column=0,sticky="w",padx=12,pady=6)
        self.chat=scrolledtext.ScrolledText(f,bg=self.C["input_bg"],fg=self.C["white"],font=self.F["body"],wrap=tk.WORD,state="disabled",borderwidth=0,highlightthickness=0,padx=14,pady=10)
        self.chat.grid(row=1,column=0,sticky="nsew",padx=8,pady=(0,8))
        self.chat.tag_config("user",  foreground=self.C["cyan"],font=("Consolas",10,"bold"))
        self.chat.tag_config("agent", foreground=self.C["green"])
        self.chat.tag_config("model", foreground=self.C["orange"])
        self.chat.tag_config("system",foreground=self.C["dim"])
        self.chat.tag_config("error", foreground=self.C["error"])
        self.chat.tag_config("ui_msg",foreground=self.C["purple"])
        self.chat.tag_config("action",foreground=self.C["warning"])

    def _build_sidebar(self,p):
        f=tk.Frame(p,bg=self.C["panel"],highlightbackground=self.C["border"],highlightthickness=1)
        f.grid(row=1,column=1,sticky="nsew",padx=(4,0),pady=4)
        f.grid_columnconfigure(0,weight=1)
        tk.Label(f,text="◈ BRAIN STATUS",bg=self.C["panel"],fg=self.C["cyan"],font=self.F["head"]).grid(row=0,column=0,sticky="w",padx=12,pady=6)
        canvas=tk.Canvas(f,bg=self.C["panel"],highlightthickness=0,height=200)
        sb=ttk.Scrollbar(f,orient="vertical",command=canvas.yview)
        self._mf=tk.Frame(canvas,bg=self.C["panel"])
        canvas.configure(yscrollcommand=sb.set)
        canvas.grid(row=1,column=0,sticky="nsew",padx=4)
        sb.grid(row=1,column=1,sticky="ns")
        f.grid_rowconfigure(1,weight=1)
        cw=canvas.create_window((0,0),window=self._mf,anchor="nw")
        self._mf.bind("<Configure>",lambda e:canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>",lambda e:canvas.itemconfig(cw,width=e.width))
        self.dots={}
        for key,model in MODELS.items():
            row=tk.Frame(self._mf,bg=self.C["panel"],pady=2)
            row.pack(fill="x",padx=6)
            dot=tk.Label(row,text="●",bg=self.C["panel"],fg=self.C["dim"],font=self.F["small"])
            dot.pack(side="left")
            tk.Label(row,text=f"[{key}]",bg=self.C["panel"],fg=self.C["orange"],font=self.F["small"],width=8,anchor="w").pack(side="left")
            tk.Label(row,text=f"{model['speed_s']}s|{model['accuracy']}%",bg=self.C["panel"],fg=self.C["dim"],font=self.F["small"]).pack(side="right")
            self.dots[key]=dot
        # Update dots based on downloaded models
        for key,model in MODELS.items():
            if (self.settings.model_path/model["file"]).exists():
                self.dots[key].config(fg=self.C["green"])
            else:
                self.dots[key].config(fg=self.C["error"],text="○")

        tk.Frame(f,bg=self.C["border"],height=1).grid(row=2,column=0,columnspan=2,sticky="ew",padx=8,pady=4)
        tk.Label(f,text="◈ ACTIVE MODEL",bg=self.C["panel"],fg=self.C["cyan"],font=self.F["head"]).grid(row=3,column=0,sticky="w",padx=12,pady=(4,2))
        self.active_lbl=tk.Label(f,text="None selected",bg=self.C["panel"],fg=self.C["orange"],font=self.F["small"],justify="left",wraplength=200)
        self.active_lbl.grid(row=4,column=0,sticky="w",padx=12,pady=2)
        tk.Frame(f,bg=self.C["border"],height=1).grid(row=5,column=0,columnspan=2,sticky="ew",padx=8,pady=4)
        tk.Label(f,text="◈ SESSION",bg=self.C["panel"],fg=self.C["cyan"],font=self.F["head"]).grid(row=6,column=0,sticky="w",padx=12,pady=(4,2))
        self.stats_lbl=tk.Label(f,text="Queries  : 0\nAvg time : --\nLast     : --",bg=self.C["panel"],fg=self.C["white"],font=self.F["small"],justify="left")
        self.stats_lbl.grid(row=7,column=0,sticky="w",padx=12,pady=2)
        tk.Frame(f,bg=self.C["border"],height=1).grid(row=8,column=0,columnspan=2,sticky="ew",padx=8,pady=4)
        tk.Label(f,text="◈ QUICK ACTIONS",bg=self.C["panel"],fg=self.C["cyan"],font=self.F["head"]).grid(row=9,column=0,sticky="w",padx=12,pady=(4,2))
        actions=[
            ("PLC Basics","Explain PLC ladder logic basics with all elements"),
            ("Safety Check","What are the main safety protocols for industrial systems?"),
            ("GUI Help","How do I automate GUI clicks using pyautogui?"),
            ("Code Help","Show me Python best practices and useful code patterns"),
            ("Math Help","Show me common engineering formulas and conversions"),
            ("Open Notepad","Open Notepad"),
            ("Take Screenshot","Take a screenshot of my screen"),
        ]
        for i,(lbl,cmd) in enumerate(actions):
            tk.Button(f,text=lbl,bg=self.C["button"],fg=self.C["white"],font=self.F["small"],relief="flat",cursor="hand2",command=lambda c=cmd:self._quick(c)).grid(row=10+i,column=0,sticky="ew",padx=12,pady=2)

    def _build_input(self,p):
        f=tk.Frame(p,bg=self.C["panel"],highlightbackground=self.C["border"],highlightthickness=1)
        f.grid(row=2,column=0,columnspan=2,sticky="ew",pady=(4,0))
        f.grid_columnconfigure(0,weight=1)
        tk.Label(f,text="Ask anything: Open software | PLC logic | GUI automation | Math | Safety | Code...",bg=self.C["panel"],fg=self.C["dim"],font=self.F["small"],anchor="w").grid(row=0,column=0,columnspan=3,sticky="ew",padx=12,pady=(8,2))
        inf=tk.Frame(f,bg=self.C["panel"])
        inf.grid(row=1,column=0,columnspan=3,sticky="ew",padx=8,pady=(0,8))
        inf.grid_columnconfigure(0,weight=1)
        self.inp=tk.Text(inf,bg=self.C["input_bg"],fg=self.C["white"],font=self.F["input"],height=3,wrap=tk.WORD,insertbackground=self.C["cyan"],borderwidth=0,highlightthickness=1,highlightcolor=self.C["cyan"],highlightbackground=self.C["border"],padx=10,pady=8)
        self.inp.grid(row=0,column=0,sticky="ew",padx=(0,8))
        self.inp.bind("<Return>",self._enter)
        bf=tk.Frame(inf,bg=self.C["panel"])
        bf.grid(row=0,column=1)
        self.send_btn=tk.Button(bf,text="▶ SEND",bg=self.C["cyan"],fg=self.C["bg"],font=self.F["head"],width=10,relief="flat",cursor="hand2",command=self._send)
        self.send_btn.pack(pady=(0,3))
        self.pause_btn=tk.Button(bf,text="⏸ PAUSE",bg=self.C["warning"],fg=self.C["bg"],font=self.F["small"],width=10,relief="flat",cursor="hand2",command=self._pause)
        self.pause_btn.pack(pady=(0,3))
        tk.Button(bf,text="⊘ CLEAR",bg=self.C["button"],fg=self.C["white"],font=self.F["small"],width=10,relief="flat",cursor="hand2",command=self._clear).pack()
        self.status_bar=tk.Label(f,text="Ready — Ask me anything!",bg=self.C["panel"],fg=self.C["dim"],font=self.F["small"],anchor="w")
        self.status_bar.grid(row=2,column=0,columnspan=3,sticky="ew",padx=12,pady=(0,6))

    # ── Core Processing ───────────────────────────────────────

    def _enter(self,e):
        if not(e.state&0x1):
            self._send()
            return "break"

    def _send(self):
        if self._busy or self._paused: return
        q=self.inp.get("1.0","end-1c").strip()
        if not q: return
        self.inp.delete("1.0","end")
        self._busy=True
        self.send_btn.config(state="disabled",text="⏳...")
        self.status_bar.config(text="Processing...",fg=self.C["warning"])
        threading.Thread(target=self._process,args=(q,),daemon=True).start()

    def _pause(self):
        if not self._paused:
            self._paused=True
            self.pause_btn.config(text="▶ RESUME",bg=self.C["green"])
            self.status_bar.config(text="⏸ PAUSED — Click Resume to continue",fg=self.C["warning"])
        else:
            self._paused=False
            self.pause_btn.config(text="⏸ PAUSE",bg=self.C["warning"])
            self.status_bar.config(text="Ready",fg=self.C["dim"])

    def _process(self,query):
        self._chat("user",f"You: {query}\n")
        self._all_dots(self.C["dim"])

        # Check pause
        while self._paused:
            time.sleep(0.5)

        q=query.lower().strip()

        # ── UI modification ───────────────────────────────────
        if self._is_ui_cmd(q):
            self._handle_ui(query)
            return

        # ── Open software command ─────────────────────────────
        if any(q.startswith(w) for w in ["open ","launch ","run ","start "]):
            self._handle_open(query)
            return

        # ── Screenshot command ────────────────────────────────
        if any(w in q for w in ["screenshot","take screenshot","capture screen"]):
            self._handle_screenshot()
            return

        # ── Math calculation ──────────────────────────────────
        if self._is_math(q):
            result=self._calc_math(q)
            if result:
                self._chat("model","[MATH BRAIN | instant]\n")
                self._chat("agent",f"{result}\n\n")
                self._finish("Done!",0.01)
                return

        # ── Pick best brain and answer ────────────────────────
        try:
            start=time.time()
            key=self._pick(q)
            model=MODELS[key]
            self.root.after(0,self._upd_active,key)
            self.root.after(0,self._dot,key,self.C["warning"])
            answer=self._get_answer(key,query)
            dur=round(time.time()-start,2)
            self.root.after(0,self._dot,key,self.C["green"])
            self._chat("model",f"[{key.upper()} BRAIN | {dur}s | {model['accuracy']}%]\n")
            self._chat("agent",f"{answer}\n\n")
            self._qcount+=1
            self._ttime+=dur
            avg=round(self._ttime/self._qcount,1)
            self.root.after(0,self.stats_lbl.config,{"text":f"Queries  : {self._qcount}\nAvg time : {avg}s\nLast     : {dur}s"})
            self._finish(f"Done in {dur}s | Brain: {key}",dur)
        except Exception as e:
            self._chat("error",f"Error: {e}\n\n")
            self._finish(f"Error: {e}",0)

    def _pick(self,query):
        """Pick best CHAT-capable model only."""
        q=query.lower()
        scores={}
        pri=self.priority.get()
        for key,model in CHAT_MODELS.items():  # Only chat models!
            score=0.0
            triggers=model.get("triggers",[])
            matched=sum(1 for t in triggers if t in q)
            if triggers:
                score+=(matched/len(triggers))*60
            score+=(model["accuracy"]/100)*25
            if pri=="speed":
                score+=(1/max(model["speed_s"],0.1))*40
            elif pri=="accuracy":
                score+=(model["accuracy"]/100)*40
            else:
                score+=(1/max(model["speed_s"],0.1))*15
            dest=self.settings.model_path/model["file"]
            if not dest.exists():
                score*=0.05
            scores[key]=score
        best=max(scores,key=scores.get)
        print(f"[GP PRO] '{q[:25]}' → {best} ({scores[best]:.1f})")
        return best

    def _get_answer(self,key,query):
        """Get answer — try LLM first, then rich knowledge."""
        q=query.lower()
        model=MODELS[key]
        dest=self.settings.model_path/model["file"]

        # Try LLM if available
        if dest.exists():
            try:
                answer=self._llm_ask(key,dest,query)
                if answer and len(answer)>10:
                    return answer
            except Exception as e:
                print(f"LLM error: {e}")

        # Rich knowledge fallback — specific to each brain
        return self._knowledge_answer(key,q)

    def _llm_ask(self,key,dest,query):
        from llama_cpp import Llama
        if self._llm_key!=key:
            if self._llm:
                del self._llm
                gc.collect()
            self.root.after(0,self.status_bar.config,
                {"text":f"Loading {MODELS[key]['name']}...","fg":self.C["warning"]})
            self._llm=Llama(
                model_path=str(dest),n_ctx=2048,
                n_threads=self.settings.cpu_threads,
                n_gpu_layers=0,verbose=False,use_mmap=True)
            self._llm_key=key
        prompts={
            "master": "You are GP PRO AGENT Senior Engineering AI. Give precise professional answers.",
            "reflex": "You are GP PRO AGENT. Give direct accurate answers in 2-3 sentences.",
            "plc":    "You are GP PRO AGENT PLC Expert. Specialize in ladder logic Allen Bradley Siemens SCADA.",
            "coder":  "You are GP PRO AGENT Code Expert. Write clean efficient code with explanations.",
            "screen": "You are GP PRO AGENT GUI Expert. Give precise screen automation instructions.",
            "safety": "You are GP PRO AGENT Safety Engineer. Prioritize safety above all.",
            "docs":   "You are GP PRO AGENT Documentation Expert. Write professional technical content.",
            "learner":"You are GP PRO AGENT Software Expert. Teach step by step clearly.",
            "ocr":    "You are GP PRO AGENT Vision Expert. Help with screen reading and OCR.",
            "math":   "You are GP PRO AGENT Engineering Calculator. Solve precisely.",
        }
        sys_p=prompts.get(key,"You are GP PRO AGENT professional AI assistant.")
        prompt=f"<|system|>{sys_p}<|end|>\n<|user|>{query}<|end|>\n<|assistant|>"
        resp=self._llm(prompt,max_tokens=512,temperature=0.1,stop=["<|end|>","<|user|>"],echo=False)
        return resp["choices"][0]["text"].strip()

    def _knowledge_answer(self,key,q):
        """Rich knowledge answers — different for every topic."""
        if key=="plc" or any(w in q for w in ["plc","ladder","rung","coil","allen","siemens","modbus","scada","hmi"]):
            return KNOWLEDGE["plc"]
        if key=="safety" or any(w in q for w in ["safety","estop","emergency","sil","loto","interlock"]):
            return KNOWLEDGE["safety"]
        if key=="screen" or any(w in q for w in ["click","pyautogui","automate","navigate","button"]):
            return KNOWLEDGE["screen"]
        if key=="coder" or any(w in q for w in ["python","code","script","function","debug","program"]):
            return KNOWLEDGE["code"]
        if key=="math" or any(w in q for w in ["formula","convert","ohm","pid","pressure","temperature"]):
            return KNOWLEDGE["math"]
        if any(w in q for w in ["open","launch","run","software","pcwin","rslogix"]):
            return KNOWLEDGE["open"]
        if any(w in q for w in ["hi","hello","hey","name","who are you","what are you"]):
            return ("Hello! I am GP PRO AGENT v1.0.0\n\n"
                   "I specialize in:\n"
                   "• PLC & Industrial Automation\n"
                   "• GUI & Screen Automation\n"
                   "• Software Learning & Operation\n"
                   "• Engineering Math & Calculations\n"
                   "• Safety Systems & Protocols\n\n"
                   "I have 11 specialist AI brains.\n"
                   "Ask me anything!")
        if "1+1" in q or "1 + 1" in q:
            return "1 + 1 = 2"
        if "capital" in q:
            caps={"india":"New Delhi","france":"Paris","usa":"Washington D.C.","uk":"London","japan":"Tokyo","china":"Beijing","germany":"Berlin","australia":"Canberra"}
            for country,capital in caps.items():
                if country in q:
                    return f"The capital of {country.title()} is {capital}."
        return KNOWLEDGE["default"]

    # ── Special Commands ──────────────────────────────────────

    def _is_math(self,q):
        import re
        return bool(re.search(r'\d+\s*[\+\-\*\/\^]\s*\d+',q))

    def _calc_math(self,q):
        import re
        try:
            expr=re.search(r'[\d\s\+\-\*\/\.\^\(\)]+',q)
            if expr:
                clean=expr.group().replace('^','**').strip()
                if clean and any(c.isdigit() for c in clean):
                    result=eval(clean)
                    return f"{clean.replace('**','^')} = {result}"
        except: pass
        return None

    def _handle_open(self,query):
        """Open software on PC."""
        q=query.lower()
        # Remove trigger words
        for w in ["open ","launch ","run ","start ","please "]:
            q=q.replace(w,"")
        q=q.strip()

        self._chat("action",f"[SCREEN BRAIN | Opening: {q}]\n")

        # Check software map
        exe=None
        for name,path in SOFTWARE_MAP.items():
            if name in q:
                exe=path
                break

        # Minimize to overlay when opening software
        self._minimize_to_overlay()

        if exe:
            try:
                subprocess.Popen(exe,shell=True)
                self._chat("agent",f"✓ Opening {q}...\nSoftware launched successfully!\n\n")
                self._overlay_msg(f"Opened: {q}")
            except Exception as e:
                # Try searching in Program Files
                found=self._find_and_open(q)
                if not found:
                    self._chat("error",f"Could not open '{q}'.\nMake sure it is installed.\n\n")
        else:
            # Try to open by name directly
            found=self._find_and_open(q)
            if not found:
                self._chat("agent",f"Searching for '{q}'...\n")
                try:
                    subprocess.Popen(f'start "" "{q}"',shell=True)
                    self._chat("agent",f"Attempted to open: {q}\n\n")
                except:
                    self._chat("error",f"Could not find '{q}'. Check if it is installed.\n\n")

        self._finish("Done!",0.5)

    def _find_and_open(self,name):
        """Search common paths for software."""
        search_paths=[
            f"C:/Program Files/{name}",
            f"C:/Program Files (x86)/{name}",
            f"C:/Program Files/{name}/{name}.exe",
            f"C:/Program Files (x86)/{name}/{name}.exe",
        ]
        for path in search_paths:
            p=Path(path)
            if p.exists():
                try:
                    subprocess.Popen(str(p),shell=True)
                    return True
                except: pass
        # Try Windows search
        try:
            subprocess.Popen(f'start "" "{name}"',shell=True)
            return True
        except:
            return False

    def _handle_screenshot(self):
        """Take and show screenshot."""
        self._chat("action","[OCR BRAIN | Taking screenshot]\n")
        try:
            import pyautogui
            from PIL import Image
            self._minimize_to_overlay()
            time.sleep(0.5)
            img=pyautogui.screenshot()
            path=str(self.settings.cache_path/"screenshot.png")
            img.save(path)
            self._chat("agent",f"Screenshot saved to:\n{path}\n\nSize: {img.width}x{img.height}px\n\n")
            self._overlay_msg("Screenshot taken!")
        except ImportError:
            self._chat("error","pyautogui not installed. Installing...\n")
            subprocess.run([sys.executable,"-m","pip","install","pyautogui","Pillow","--quiet"])
            self._chat("agent","Installed! Try again.\n\n")
        self._finish("Screenshot done!",0.5)

    # ── UI Self-Modification ──────────────────────────────────

    def _is_ui_cmd(self,q):
        return any(k in q for k in [
            "change theme","make font","change color","change accent",
            "modify ui","change ui","change the color","make it bigger",
            "make it smaller","change window","dark mode","light mode",
            "change background","change text color"
        ])

    def _handle_ui(self,query):
        q=query.lower()
        changes=[]
        colors={
            "blue":"#0066ff","red":"#ff3333","green":"#00ff88",
            "purple":"#bf5fff","orange":"#ff6b2b","yellow":"#ffdd00",
            "pink":"#ff66cc","cyan":"#00e5ff","teal":"#00ccaa",
            "white":"#ffffff","gold":"#ffd700","lime":"#aaff00",
        }
        # Color change
        if any(w in q for w in ["color","theme","accent"]):
            for name,hex_v in colors.items():
                if name in q:
                    self.C["cyan"]=hex_v
                    self.settings.ui["accent_color"]=hex_v
                    # Apply immediately to all UI elements
                    self.root.after(0,self._apply_color,hex_v)
                    changes.append(f"Theme color → {name} ({hex_v})")
                    break

        # Font size
        if "font" in q or "text" in q:
            if any(w in q for w in ["bigger","larger","increase","up","+"]):
                s=min(self.F["body"][1]+2,18)
                self.F["body"]=("Consolas",s)
                self.settings.ui["font_size"]=s
                self.root.after(0,self.chat.config,{"font":self.F["body"]})
                self.root.after(0,self.inp.config,{"font":self.F["body"]})
                changes.append(f"Font size → {s}pt")
            elif any(w in q for w in ["smaller","decrease","down","-"]):
                s=max(self.F["body"][1]-2,8)
                self.F["body"]=("Consolas",s)
                self.settings.ui["font_size"]=s
                self.root.after(0,self.chat.config,{"font":self.F["body"]})
                self.root.after(0,self.inp.config,{"font":self.F["body"]})
                changes.append(f"Font size → {s}pt")

        # Background
        if "dark" in q and "mode" in q:
            self.C["bg"]="#0a0f1a"
            self.C["panel"]="#0d1526"
            self.root.after(0,self.root.configure,{"bg":self.C["bg"]})
            changes.append("Dark mode enabled")
        elif "light" in q and "mode" in q:
            self.C["bg"]="#1a2a3a"
            self.C["panel"]="#1e3248"
            self.root.after(0,self.root.configure,{"bg":self.C["bg"]})
            changes.append("Light mode applied")

        if changes:
            self.settings.save_ui()
            self._chat("ui_msg","◈ UI MODIFIED BY AI:\n"+"".join(f"  ✓ {c}\n" for c in changes)+"\nSaved permanently to C:\\GPProAgent\\ui_config.json\n\n")
        else:
            self._chat("ui_msg","◈ UI command received.\nExamples:\n  'change theme to blue'\n  'make font bigger'\n  'change accent to red'\n\n")

        self._finish("UI updated!",0.1)

    def _apply_color(self,color):
        """Apply color change to all UI elements immediately."""
        try:
            self.send_btn.config(bg=color)
            self.chat.tag_config("user",foreground=color)
            # Update header labels
            for widget in self.root.winfo_children():
                self._apply_color_recursive(widget,color)
        except: pass

    def _apply_color_recursive(self,widget,color):
        try:
            if isinstance(widget,(tk.Label,)) and widget.cget("fg")==self.C.get("old_cyan","#00e5ff"):
                widget.config(fg=color)
        except: pass
        for child in widget.winfo_children():
            self._apply_color_recursive(child,color)

    # ── Minimize / Overlay Mode ───────────────────────────────

    def _toggle_mini(self):
        if not self._minimized:
            self._minimize_to_overlay()
        else:
            self._restore_from_overlay()

    def _minimize_to_overlay(self):
        """Shrink to small overlay in corner."""
        if self._minimized:
            return
        self._minimized=True
        self.root.geometry("320x80")
        sw=self.root.winfo_screenwidth()
        self.root.geometry(f"320x80+{sw-330}+10")
        # Hide main content
        self._main.grid_remove()
        # Show mini bar
        self._mini_frame=tk.Frame(self.root,bg=self.C["panel"])
        self._mini_frame.pack(fill="both",expand=True)
        tk.Label(self._mini_frame,text="⬡ GP PRO AGENT",bg=self.C["panel"],fg=self.C["cyan"],font=("Consolas",11,"bold")).pack(side="left",padx=8)
        self._mini_status=tk.Label(self._mini_frame,text="Ready",bg=self.C["panel"],fg=self.C["green"],font=("Consolas",9))
        self._mini_status.pack(side="left",padx=4)
        tk.Button(self._mini_frame,text="⊞ Restore",bg=self.C["button"],fg=self.C["white"],font=("Consolas",9),relief="flat",cursor="hand2",command=self._restore_from_overlay).pack(side="right",padx=8)

    def _restore_from_overlay(self):
        """Restore full window."""
        if not self._minimized:
            return
        self._minimized=False
        if hasattr(self,"_mini_frame"):
            self._mini_frame.destroy()
        self._main.grid()
        self.root.geometry("1300x850")
        self.root.update_idletasks()
        x=(self.root.winfo_screenwidth()-1300)//2
        y=(self.root.winfo_screenheight()-850)//2
        self.root.geometry(f"1300x850+{x}+{y}")

    def _overlay_msg(self,msg):
        if self._minimized and hasattr(self,"_mini_status"):
            self.root.after(0,self._mini_status.config,{"text":msg})

    # ── Download Manager ──────────────────────────────────────

    def _open_download_manager(self):
        win=tk.Toplevel(self.root)
        win.title("GP PRO AGENT — Download Manager")
        win.geometry("700x500")
        win.configure(bg=self.C["bg"])
        win.resizable(False,False)

        tk.Label(win,text="◈ BRAIN DOWNLOAD MANAGER",bg=self.C["bg"],fg=self.C["cyan"],font=self.F["head"]).pack(anchor="w",padx=16,pady=(12,4))
        tk.Label(win,text="Download missing AI brain models. Models save to C:\\GPProAgent\\models\\",bg=self.C["bg"],fg=self.C["dim"],font=self.F["small"]).pack(anchor="w",padx=16)
        tk.Frame(win,bg=self.C["border"],height=1).pack(fill="x",padx=16,pady=8)

        frame=tk.Frame(win,bg=self.C["bg"])
        frame.pack(fill="both",expand=True,padx=16)

        self._dl_labels={}
        self._dl_bars={}
        self._dl_btns={}

        for i,(key,model) in enumerate(MODELS.items()):
            dest=self.settings.model_path/model["file"]
            exists=dest.exists()

            row=tk.Frame(frame,bg=self.C["panel"],pady=4)
            row.pack(fill="x",pady=2)

            status="✓ Downloaded" if exists else "✗ Missing"
            color=self.C["green"] if exists else self.C["error"]
            tk.Label(row,text=f"[{key}]",bg=self.C["panel"],fg=self.C["orange"],font=self.F["small"],width=8).pack(side="left",padx=6)
            tk.Label(row,text=f"{model['name'][:28]}",bg=self.C["panel"],fg=self.C["white"],font=self.F["small"],width=30,anchor="w").pack(side="left")
            tk.Label(row,text=f"{model['size_gb']}GB",bg=self.C["panel"],fg=self.C["dim"],font=self.F["small"],width=6).pack(side="left")
            lbl=tk.Label(row,text=status,bg=self.C["panel"],fg=color,font=self.F["small"],width=14)
            lbl.pack(side="left")
            self._dl_labels[key]=lbl

            if not exists:
                btn=tk.Button(row,text="⬇ Download",bg=self.C["cyan"],fg=self.C["bg"],font=self.F["small"],relief="flat",cursor="hand2",
                    command=lambda k=key,m=model,l=lbl,b=None:self._download_single(k,m,l,win))
                btn.pack(side="right",padx=6)
                self._dl_btns[key]=btn
            else:
                tk.Label(row,text="Ready",bg=self.C["panel"],fg=self.C["green"],font=self.F["small"]).pack(side="right",padx=6)

        # Download all missing button
        tk.Frame(win,bg=self.C["border"],height=1).pack(fill="x",padx=16,pady=8)
        btn_frame=tk.Frame(win,bg=self.C["bg"])
        btn_frame.pack(fill="x",padx=16,pady=(0,12))
        tk.Button(btn_frame,text="⬇ Download ALL Missing Models",bg=self.C["cyan"],fg=self.C["bg"],font=self.F["head"],relief="flat",cursor="hand2",
            command=lambda:threading.Thread(target=self._download_all_missing,args=(win,),daemon=True).start()).pack(side="left")
        self._dl_status=tk.Label(btn_frame,text="",bg=self.C["bg"],fg=self.C["green"],font=self.F["small"])
        self._dl_status.pack(side="left",padx=12)

    def _download_single(self,key,model,label,win):
        def _do():
            label.config(text="Downloading...",fg=self.C["warning"])
            dest=self.settings.model_path/model["file"]
            success=self._dl_file(model["url"],dest,label)
            if success:
                label.config(text="✓ Downloaded",fg=self.C["green"])
                self.dots[key].config(fg=self.C["green"],text="●")
                if key in self._dl_btns:
                    try: self._dl_btns[key].config(state="disabled",text="✓ Done")
                    except: pass
        threading.Thread(target=_do,daemon=True).start()

    def _download_all_missing(self,win):
        missing=[k for k,m in MODELS.items() if not (self.settings.model_path/m["file"]).exists()]
        self._dl_status.config(text=f"Downloading {len(missing)} models...")
        for key in missing:
            model=MODELS[key]
            lbl=self._dl_labels.get(key)
            dest=self.settings.model_path/model["file"]
            if lbl:
                lbl.config(text="Downloading...",fg=self.C["warning"])
            success=self._dl_file(model["url"],dest,lbl)
            if success and lbl:
                lbl.config(text="✓ Downloaded",fg=self.C["green"])
                self.dots[key].config(fg=self.C["green"],text="●")
        self._dl_status.config(text="✓ All downloads complete!")

    def _dl_file(self,url,dest,label=None):
        import urllib.request, urllib.error
        tmp=Path(str(dest)+".part")
        headers={"User-Agent":"GP-PRO-AGENT/1.0"}
        resume=tmp.stat().st_size if tmp.exists() else 0
        if resume>0: headers["Range"]=f"bytes={resume}-"
        try:
            req=urllib.request.Request(url,headers=headers)
            with urllib.request.urlopen(req,timeout=30) as r:
                total=int(r.headers.get("Content-Length",0))+resume
                dl=resume
                mode="ab" if resume>0 else "wb"
                with open(tmp,mode) as f:
                    while True:
                        chunk=r.read(524288)
                        if not chunk: break
                        f.write(chunk)
                        dl+=len(chunk)
                        if total>0 and label:
                            pct=int(dl/total*100)
                            mb=dl//1048576
                            tmb=total//1048576
                            self.root.after(0,label.config,{"text":f"{pct}% {mb}/{tmb}MB","fg":self.C["warning"]})
            shutil.move(str(tmp),str(dest))
            return True
        except Exception as e:
            print(f"Download error: {e}")
            return False

    def _check_models(self):
        """Check model status on startup."""
        ready=sum(1 for m in MODELS.values() if (self.settings.model_path/m["file"]).exists())
        total=len(MODELS)
        missing=total-ready
        if missing>0:
            self._chat("system",f"◈ {ready}/{total} models ready. {missing} missing.\n")
            self._chat("system","◈ Click '⬇ Models' button to download missing models.\n\n")
        else:
            self._chat("system",f"◈ All {total} brain models ready!\n\n")
        # Try import llama_cpp
        try:
            import llama_cpp
            self._chat("system","◈ AI Engine: llama.cpp active ✓\n\n")
        except:
            self._chat("system","◈ AI Engine: Using expert knowledge mode\n")
            self._chat("system","◈ For full AI: pip install llama-cpp-python\n\n")

    # ── Helpers ───────────────────────────────────────────────

    def _finish(self,msg,dur):
        self._busy=False
        self.root.after(0,self.send_btn.config,{"state":"normal","text":"▶ SEND"})
        self.root.after(0,self.status_bar.config,{"text":msg,"fg":self.C["green"]})

    def _chat(self,tag,text):
        def _d():
            self.chat.config(state="normal")
            self.chat.insert("end",text,tag)
            self.chat.see("end")
            self.chat.config(state="disabled")
        self.root.after(0,_d)

    def _dot(self,key,color):
        if key in self.dots: self.dots[key].config(fg=color)

    def _all_dots(self,color):
        for d in self.dots.values(): d.config(fg=color)

    def _upd_active(self,key):
        m=MODELS.get(key,{})
        self.active_lbl.config(text=f"{m.get('name','?')}\nSpeed:{m.get('speed_s')}s Acc:{m.get('accuracy')}%\nRAM:{m.get('ram_mb')}MB")

    def _clear(self):
        self.chat.config(state="normal")
        self.chat.delete("1.0","end")
        self.chat.config(state="disabled")
        self._chat("system","Chat cleared.\n")

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
        except: pass
        self.root.after(3000,self._upd_ram)

    def run(self):
        self._upd_ram()
        self.root.mainloop()
