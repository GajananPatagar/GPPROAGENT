import tkinter as tk
from tkinter import ttk, scrolledtext
import threading, time, sys, os, json, gc, subprocess
from pathlib import Path
BASE = Path(__file__).parent.parent
sys.path.insert(0, str(BASE))
from config.settings import Settings
from config.models import MODELS

PROMPTS = {
    "master":  "You are GP PRO AGENT — Senior Engineering AI. Give precise professional detailed answers.",
    "reflex":  "You are GP PRO AGENT. Give instant direct accurate answers in 2-3 sentences.",
    "plc":     "You are GP PRO AGENT PLC Expert. Specialize in ladder logic, Allen Bradley Studio 5000, Siemens TIA Portal, SCADA, Modbus, Profibus. Give detailed professional PLC engineering answers.",
    "coder":   "You are GP PRO AGENT Code Expert. Write clean, efficient, well-commented code. Always explain what the code does.",
    "screen":  "You are GP PRO AGENT GUI Automation Expert. Give precise step-by-step instructions for screen and GUI operations using pyautogui.",
    "safety":  "You are GP PRO AGENT Safety Engineer. Prioritize safety above everything. Give clear safety procedures and risk assessments.",
    "memory":  "You are GP PRO AGENT Memory System. Recall and search information accurately from context.",
    "docs":    "You are GP PRO AGENT Documentation Expert. Write clear professional technical documentation and reports.",
    "learner": "You are GP PRO AGENT Software Learning Expert. Teach software operations step by step with clear instructions.",
    "ocr":     "You are GP PRO AGENT Vision Expert. Help read text from screens, describe what you see, and extract information.",
    "math":    "You are GP PRO AGENT Engineering Calculator. Solve math problems and engineering calculations with precision.",
}

RICH_FALLBACKS = {
    "plc": """PLC Ladder Logic — Expert Answer:

BASIC ELEMENTS:
• Examine If Closed (XIC) — NO Contact: energizes when bit=1
• Examine If Open (XIO)  — NC Contact: energizes when bit=0  
• Output Energize (OTE)  — Coil: sets bit when rung true
• Output Latch (OTL)     — Latches output ON
• Output Unlatch (OTU)   — Unlatches output

TIMERS:
• TON (Timer On-Delay)   — Delays turning ON
• TOF (Timer Off-Delay)  — Delays turning OFF
• RTO (Retentive Timer)  — Holds value on power loss

COUNTERS:
• CTU (Count Up)  — Increments on rising edge
• CTD (Count Down)— Decrements on rising edge
• RES            — Resets timer/counter

CONTROLLERS:
• Allen Bradley  → Studio 5000 / RSLogix 5000
• Siemens        → TIA Portal / S7-1200/1500
• Schneider      → Unity Pro / Modicon
• Mitsubishi     → GX Works / MELSEC

NETWORKING:
• Modbus TCP/RTU, Profibus, Profinet, EtherNet/IP, OPC-UA""",

    "safety": """Safety Engineering — Expert Answer:

EMERGENCY STOP (E-STOP):
• Must be NC (Normally Closed) hardwired in series
• Cannot be controlled by PLC software alone
• Must require manual reset after activation
• Category 0: immediate power removal
• Category 1: controlled stop then power removal

SAFETY INTEGRITY LEVELS:
• SIL 1: Risk reduction 10-100x   (low demand)
• SIL 2: Risk reduction 100-1000x (medium demand)
• SIL 3: Risk reduction 1000-10000x (high demand)

LOTO PROCEDURE:
1. Notify affected personnel
2. Identify all energy sources
3. Isolate energy sources
4. Lockout/Tagout all isolation points
5. Release stored energy
6. Verify de-energized state
7. Perform work
8. Remove locks in reverse order

KEY STANDARDS:
• IEC 61508 — Functional Safety
• IEC 61511 — Process Industry Safety
• ISO 13849 — Machine Safety
• IEC 62061 — Machinery Functional Safety""",

    "screen": """GUI Automation — Expert Answer:

PYAUTOGUI COMMANDS:
• pyautogui.click(x, y)           — Left click
• pyautogui.doubleClick(x, y)     — Double click
• pyautogui.rightClick(x, y)      — Right click
• pyautogui.moveTo(x, y, duration=0.5) — Move mouse
• pyautogui.typewrite('text')     — Type text
• pyautogui.press('enter')        — Press key
• pyautogui.hotkey('ctrl','c')    — Key combination
• pyautogui.screenshot()          — Take screenshot
• pyautogui.locateOnScreen('img.png') — Find image

FIND SCREEN COORDINATES:
1. Open Paint or any app
2. Move mouse to element
3. Check bottom bar for X,Y coordinates
4. Use those in pyautogui.click(x, y)

WINDOWS SHORTCUTS:
• Win+R  → Run dialog
• Win+E  → File Explorer  
• Ctrl+Shift+Esc → Task Manager
• Alt+Tab → Switch windows
• Win+D  → Show desktop""",

    "coder": """Python Expert — Code Answer:

BEST PRACTICES:
• Use virtual environments: python -m venv env
• Handle exceptions: try/except with specific types
• Type hints: def func(x: int) -> str:
• Docstrings: document every public function
• Follow PEP8 style guide

USEFUL PATTERNS:
# Read file safely
with open('file.txt', 'r') as f:
    content = f.read()

# Handle errors properly  
try:
    result = risky_operation()
except ValueError as e:
    print(f"Value error: {e}")
except Exception as e:
    print(f"Unexpected: {e}")

# List comprehension
squares = [x**2 for x in range(10)]

# Dictionary comprehension
mapping = {k: v for k, v in zip(keys, values)}""",

    "math": """Engineering Calculator — Math Answer:

COMMON FORMULAS:
• Ohm's Law:     V = I × R
• Power:         P = V × I = I²R = V²/R
• 4-20mA:        Value% = (mA - 4) / 16 × 100
• PID:           Output = Kp×e + Ki∫e + Kd(de/dt)
• Flow (orifice):Q = Cd × A × √(2ΔP/ρ)

UNIT CONVERSIONS:
• PSI to Bar:    Bar = PSI × 0.0689476
• Bar to PSI:    PSI = Bar × 14.5038
• °C to °F:      F = (C × 9/5) + 32
• °F to °C:      C = (F - 32) × 5/9
• kPa to PSI:    PSI = kPa × 0.14504

Please provide specific values for calculation.""",
}

class MainWindow:
    def __init__(self):
        self.settings = Settings()
        self.settings.ensure_dirs()
        self._busy = False
        self._qcount = 0
        self._ttime = 0.0
        self._llm = None
        self._llm_key = None
        self._llm_available = None
        self.C = {
            "bg":"#0a0f1a","panel":"#0d1526","border":"#1a3a5c",
            "cyan":self.settings.ui.get("accent_color","#00e5ff"),
            "green":"#00ff88","orange":"#ff6b2b","purple":"#bf5fff",
            "white":"#d0e8ff","dim":"#3a5a7a","input_bg":"#071020",
            "button":"#0a2a4a","error":"#ff4444","warning":"#ffaa00",
        }
        self.F = {
            "title":("Consolas",16,"bold"),
            "head":("Consolas",11,"bold"),
            "body":("Consolas",self.settings.ui.get("font_size",10)),
            "small":("Consolas",9),
            "input":("Consolas",11),
        }
        self._setup()
        self._build()
        threading.Thread(target=self._check_llm,daemon=True).start()

    def _check_llm(self):
        try:
            import llama_cpp
            self._llm_available = True
            self._chat("system","◈ AI Engine: llama.cpp loaded ✓ — Full intelligence active\n\n")
        except ImportError:
            self._llm_available = False
            self._chat("system","◈ AI Engine: Installing llama.cpp...\n")
            try:
                subprocess.run([sys.executable,"-m","pip","install","llama-cpp-python","--prefer-binary","--quiet"],timeout=300)
                import llama_cpp
                self._llm_available = True
                self._chat("system","◈ AI Engine: Installed successfully ✓\n\n")
            except:
                self._llm_available = False
                self._chat("system","◈ AI Engine: Using built-in expert knowledge (fast mode)\n\n")

    def _setup(self):
        self.root = tk.Tk()
        self.root.title(self.settings.ui.get("window_title","GP PRO AGENT v1.0.0"))
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
        self._header(m)
        self._chat_panel(m)
        self._sidebar(m)
        self._input_panel(m)

    def _header(self,p):
        h=tk.Frame(p,bg=self.C["panel"],highlightbackground=self.C["border"],highlightthickness=1)
        h.grid(row=0,column=0,columnspan=2,sticky="ew",pady=(0,4))
        h.grid_columnconfigure(2,weight=1)
        tk.Label(h,text="⬡ GP PRO AGENT",bg=self.C["panel"],fg=self.C["cyan"],font=self.F["title"]).grid(row=0,column=0,padx=16,pady=10)
        tk.Label(h,text="PLC Engineering | GUI Automation | Software Learning | 100% Offline",bg=self.C["panel"],fg=self.C["dim"],font=self.F["small"]).grid(row=0,column=1,padx=8,sticky="w")
        tk.Frame(h,bg=self.C["panel"]).grid(row=0,column=2,sticky="ew")
        self.ram_lbl=tk.Label(h,text="RAM:--MB",bg=self.C["panel"],fg=self.C["green"],font=self.F["small"])
        self.ram_lbl.grid(row=0,column=3,padx=8)
        self.priority=tk.StringVar(value="balanced")
        pf=tk.Frame(h,bg=self.C["panel"])
        pf.grid(row=0,column=4,padx=16)
        tk.Label(pf,text="Priority:",bg=self.C["panel"],fg=self.C["dim"],font=self.F["small"]).pack(side="left")
        for v,l in [("speed","⚡Speed"),("balanced","⚖Balance"),("accuracy","🎯Accuracy")]:
            tk.Radiobutton(pf,text=l,variable=self.priority,value=v,bg=self.C["panel"],fg=self.C["white"],selectcolor=self.C["button"],activebackground=self.C["panel"],font=self.F["small"]).pack(side="left",padx=3)

    def _chat_panel(self,p):
        f=tk.Frame(p,bg=self.C["panel"],highlightbackground=self.C["border"],highlightthickness=1)
        f.grid(row=1,column=0,sticky="nsew",padx=(0,4),pady=4)
        f.grid_rowconfigure(1,weight=1)
        f.grid_columnconfigure(0,weight=1)
        tk.Label(f,text="◈ CONVERSATION",bg=self.C["panel"],fg=self.C["cyan"],font=self.F["head"]).grid(row=0,column=0,sticky="w",padx=12,pady=6)
        self.chat=scrolledtext.ScrolledText(f,bg=self.C["input_bg"],fg=self.C["white"],font=self.F["body"],wrap=tk.WORD,state="disabled",borderwidth=0,highlightthickness=0,padx=14,pady=10)
        self.chat.grid(row=1,column=0,sticky="nsew",padx=8,pady=(0,8))
        self.chat.tag_config("user",foreground=self.C["cyan"],font=("Consolas",10,"bold"))
        self.chat.tag_config("agent",foreground=self.C["green"])
        self.chat.tag_config("model",foreground=self.C["orange"])
        self.chat.tag_config("system",foreground=self.C["dim"])
        self.chat.tag_config("error",foreground=self.C["error"])
        self.chat.tag_config("ui_msg",foreground=self.C["purple"])
        self._chat("system","◈ GP PRO AGENT v1.0.0 — Starting up...\n◈ Loading AI Engine...\n\n")

    def _sidebar(self,p):
        f=tk.Frame(p,bg=self.C["panel"],highlightbackground=self.C["border"],highlightthickness=1)
        f.grid(row=1,column=1,sticky="nsew",padx=(4,0),pady=4)
        f.grid_columnconfigure(0,weight=1)
        tk.Label(f,text="◈ BRAIN STATUS",bg=self.C["panel"],fg=self.C["cyan"],font=self.F["head"]).grid(row=0,column=0,sticky="w",padx=12,pady=6)
        canvas=tk.Canvas(f,bg=self.C["panel"],highlightthickness=0,height=220)
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
        for key,model in MODELS.items():
            if (self.settings.model_path/model["file"]).exists():
                self.dots[key].config(fg=self.C["green"])
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
        for i,(lbl,cmd) in enumerate([("PLC Basics","Explain PLC ladder logic basics with all elements"),("Safety Check","What are the main safety protocols for industrial systems?"),("GUI Help","How do I automate GUI clicks using pyautogui?"),("Code Help","Show me Python best practices and useful code patterns"),("Math Help","Show me common engineering formulas and conversions")]):
            tk.Button(f,text=lbl,bg=self.C["button"],fg=self.C["white"],font=self.F["small"],relief="flat",cursor="hand2",command=lambda c=cmd:self._quick(c)).grid(row=10+i,column=0,sticky="ew",padx=12,pady=2)

    def _input_panel(self,p):
        f=tk.Frame(p,bg=self.C["panel"],highlightbackground=self.C["border"],highlightthickness=1)
        f.grid(row=2,column=0,columnspan=2,sticky="ew",pady=(4,0))
        f.grid_columnconfigure(0,weight=1)
        tk.Label(f,text="Ask anything: PLC logic, GUI automation, calculations, software help, safety protocols...",bg=self.C["panel"],fg=self.C["dim"],font=self.F["small"],anchor="w").grid(row=0,column=0,columnspan=2,sticky="ew",padx=12,pady=(8,2))
        inf=tk.Frame(f,bg=self.C["panel"])
        inf.grid(row=1,column=0,columnspan=2,sticky="ew",padx=8,pady=(0,8))
        inf.grid_columnconfigure(0,weight=1)
        self.inp=tk.Text(inf,bg=self.C["input_bg"],fg=self.C["white"],font=self.F["input"],height=3,wrap=tk.WORD,insertbackground=self.C["cyan"],borderwidth=0,highlightthickness=1,highlightcolor=self.C["cyan"],highlightbackground=self.C["border"],padx=10,pady=8)
        self.inp.grid(row=0,column=0,sticky="ew",padx=(0,8))
        self.inp.bind("<Return>",self._enter)
        bf=tk.Frame(inf,bg=self.C["panel"])
        bf.grid(row=0,column=1)
        self.send_btn=tk.Button(bf,text="▶ SEND",bg=self.C["cyan"],fg=self.C["bg"],font=self.F["head"],width=11,relief="flat",cursor="hand2",command=self._send)
        self.send_btn.pack(pady=(0,4))
        tk.Button(bf,text="⊘ CLEAR",bg=self.C["button"],fg=self.C["white"],font=self.F["small"],width=11,relief="flat",cursor="hand2",command=self._clear).pack()
        self.status_bar=tk.Label(f,text="Ready — GP PRO AGENT Online",bg=self.C["panel"],fg=self.C["dim"],font=self.F["small"],anchor="w")
        self.status_bar.grid(row=2,column=0,columnspan=2,sticky="ew",padx=12,pady=(0,6))

    def _enter(self,e):
        if not(e.state&0x1):
            self._send()
            return "break"

    def _send(self):
        if self._busy: return
        q=self.inp.get("1.0","end-1c").strip()
        if not q: return
        self.inp.delete("1.0","end")
        self._busy=True
        self.send_btn.config(state="disabled",text="⏳ ...")
        self.status_bar.config(text="Thinking...",fg=self.C["warning"])
        threading.Thread(target=self._process,args=(q,),daemon=True).start()

    def _process(self,query):
        self._chat("user",f"You: {query}\n")
        self._all_dots(self.C["dim"])
        if self._is_ui_cmd(query):
            self._handle_ui(query)
            return
        try:
            start=time.time()
            key=self._pick(query)
            model=MODELS[key]
            self.root.after(0,self._upd_active,key)
            self.root.after(0,self._dot,key,self.C["warning"])
            answer=self._ask(key,query)
            dur=round(time.time()-start,2)
            self.root.after(0,self._dot,key,self.C["green"])
            self._chat("model",f"[{key.upper()} BRAIN | {dur}s | {model['accuracy']}% accuracy]\n")
            self._chat("agent",f"{answer}\n\n")
            self._qcount+=1
            self._ttime+=dur
            avg=round(self._ttime/self._qcount,1)
            self.root.after(0,self.stats_lbl.config,{"text":f"Queries  : {self._qcount}\nAvg time : {avg}s\nLast     : {dur}s"})
            self.root.after(0,self.status_bar.config,{"text":f"Done in {dur}s | Brain: {key}","fg":self.C["green"]})
        except Exception as e:
            self._chat("error",f"Error: {e}\n\n")
            self.root.after(0,self.status_bar.config,{"text":f"Error: {e}","fg":self.C["error"]})
        finally:
            self._busy=False
            self.root.after(0,self.send_btn.config,{"state":"normal","text":"▶ SEND"})
            self.root.after(2500,self._all_dots,self.C["dim"])

    def _pick(self,query):
        q=query.lower()
        scores={}
        pri=self.priority.get()
        for key,model in MODELS.items():
            score=0.0
            triggers=model.get("triggers",[])
            matched=sum(1 for t in triggers if t in q)
            score+=(matched/max(len(triggers),1))*60
            score+=(model["accuracy"]/100)*25
            score+=(1/max(model["speed_s"],0.1))*15
            if pri=="speed": score+=(1/max(model["speed_s"],0.1))*30
            elif pri=="accuracy": score+=(model["accuracy"]/100)*30
            dest=self.settings.model_path/model["file"]
            if not dest.exists(): score*=0.05
            scores[key]=score
        best=max(scores,key=scores.get)
        print(f"[GP PRO] Query:'{query[:30]}' → Brain:{best} Score:{scores[best]:.1f}")
        return best

    def _ask(self,key,query):
        model=MODELS[key]
        dest=self.settings.model_path/model["file"]
        if not dest.exists():
            return self._smart_fallback(key,query)
        if self._llm_available==False:
            return self._smart_fallback(key,query)
        try:
            from llama_cpp import Llama
            if self._llm_key!=key:
                if self._llm:
                    del self._llm
                    gc.collect()
                self.root.after(0,self.status_bar.config,{"text":f"Loading {model['name']}...","fg":self.C["warning"]})
                self._llm=Llama(
                    model_path=str(dest),
                    n_ctx=self.settings.context_size,
                    n_threads=self.settings.cpu_threads,
                    n_gpu_layers=0,
                    verbose=False,
                    use_mmap=True,
                )
                self._llm_key=key
            sys_p=PROMPTS.get(key,PROMPTS["master"])
            prompt=f"<|system|>{sys_p}<|end|>\n<|user|>{query}<|end|>\n<|assistant|>"
            resp=self._llm(prompt,max_tokens=self.settings.max_tokens,temperature=self.settings.temperature,stop=["<|end|>","<|user|>"],echo=False)
            result=resp["choices"][0]["text"].strip()
            return result if result else self._smart_fallback(key,query)
        except ImportError:
            self._llm_available=False
            return self._smart_fallback(key,query)
        except Exception as e:
            print(f"LLM error: {e}")
            return self._smart_fallback(key,query)

    def _smart_fallback(self,key,query):
        """Rich expert knowledge fallback — different for each brain."""
        q=query.lower()
        # Use rich fallbacks based on brain key
        if key=="plc" or any(w in q for w in ["ladder","plc","rung","coil","allen","siemens","modbus","scada","hmi"]):
            return RICH_FALLBACKS["plc"]
        if key=="safety" or any(w in q for w in ["safety","estop","emergency","sil","loto","interlock"]):
            return RICH_FALLBACKS["safety"]
        if key=="screen" or any(w in q for w in ["click","screen","gui","button","automate","pyautogui","navigate"]):
            return RICH_FALLBACKS["screen"]
        if key=="coder" or any(w in q for w in ["python","code","script","function","debug","program"]):
            return RICH_FALLBACKS["coder"]
        if key=="math" or any(w in q for w in ["calculate","formula","math","convert","equation"]):
            return RICH_FALLBACKS["math"]
        if any(w in q for w in ["open","launch","run","start","software","application","windows"]):
            return ("Software Operations:\n"
                    "• Open app: Win+S → type name → Enter\n"
                    "• File Explorer: Win+E\n"
                    "• Run dialog: Win+R → type command\n"
                    "• Task Manager: Ctrl+Shift+Esc\n"
                    "• Settings: Win+I\n\n"
                    "For automation use pyautogui:\n"
                    "import pyautogui\n"
                    "pyautogui.hotkey('win','r')  # Open run\n"
                    "pyautogui.typewrite('notepad')  # Type app\n"
                    "pyautogui.press('enter')  # Launch")
        if any(w in q for w in ["watch","learn","observe","screen"]):
            return ("Screen Learning Mode:\n"
                    "GP PRO AGENT can watch your screen using:\n"
                    "import pyautogui, PIL\n"
                    "screenshot = pyautogui.screenshot()\n"
                    "screenshot.save('screen.png')\n\n"
                    "For continuous monitoring:\n"
                    "while True:\n"
                    "    img = pyautogui.screenshot()\n"
                    "    # analyze image\n"
                    "    time.sleep(1)")
        if any(w in q for w in ["hi","hello","hey","name","who","what are you"]):
            return ("Hello! I am GP PRO AGENT v1.0.0\n\n"
                    "I am a professional AI system specialized in:\n"
                    "• PLC & Industrial Automation\n"
                    "• GUI & Screen Automation\n"
                    "• Software Learning & Operation\n"
                    "• Engineering Calculations\n"
                    "• Safety Protocols\n\n"
                    "I have 11 specialist AI brains working together.\n"
                    "Ask me anything about engineering or automation!")
        return (f"GP PRO AGENT [{key.upper()} BRAIN] processing: '{query}'\n\n"
                f"I specialize in: {MODELS[key]['role']}\n\n"
                f"Ask me specifically about:\n"
                f"• PLC ladder logic and industrial automation\n"
                f"• GUI automation and screen control\n"
                f"• Safety systems and protocols\n"
                f"• Python code and scripts\n"
                f"• Engineering calculations")

    def _is_ui_cmd(self,query):
        q=query.lower()
        return any(k in q for k in ["change theme","make font","change color","change accent","modify ui","change ui","change the color","make it bigger","make it smaller","change window"])

    def _handle_ui(self,query):
        q=query.lower()
        changes=[]
        colors={"blue":"#0066ff","red":"#ff3333","green":"#00ff88","purple":"#bf5fff","orange":"#ff6b2b","yellow":"#ffdd00","pink":"#ff66cc","cyan":"#00e5ff","teal":"#00ccaa","white":"#ffffff","gold":"#ffd700"}
        if any(w in q for w in ["color","theme","accent"]):
            for name,hex_v in colors.items():
                if name in q:
                    self.C["cyan"]=hex_v
                    self.settings.ui["accent_color"]=hex_v
                    self.root.after(0,self.send_btn.config,{"bg":hex_v})
                    self.chat.tag_config("user",foreground=hex_v)
                    changes.append(f"Accent color → {name} ({hex_v})")
                    break
        if "font" in q:
            if any(w in q for w in ["bigger","larger","increase","up"]):
                s=min(self.F["body"][1]+1,16)
                self.F["body"]=("Consolas",s)
                self.settings.ui["font_size"]=s
                self.root.after(0,self.chat.config,{"font":self.F["body"]})
                changes.append(f"Font size → {s}")
            elif any(w in q for w in ["smaller","decrease","down"]):
                s=max(self.F["body"][1]-1,8)
                self.F["body"]=("Consolas",s)
                self.settings.ui["font_size"]=s
                self.root.after(0,self.chat.config,{"font":self.F["body"]})
                changes.append(f"Font size → {s}")
        if changes:
            self.settings.save_ui()
            self._chat("ui_msg",f"◈ UI Updated by AI command:\n"+"".join(f"  • {c}\n" for c in changes)+"\nChanges saved permanently.\n\n")
        else:
            self._chat("ui_msg","◈ UI command recognized.\nTry: 'change theme to blue' or 'make font bigger'\n\n")
        self._busy=False
        self.root.after(0,self.send_btn.config,{"state":"normal","text":"▶ SEND"})

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
        self.active_lbl.config(text=f"{m.get('name','?')}\nSpeed:{m.get('speed_s')}s\nAcc:{m.get('accuracy')}%\nRAM:{m.get('ram_mb')}MB")

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
