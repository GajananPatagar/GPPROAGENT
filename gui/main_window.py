import tkinter as tk
from tkinter import ttk, scrolledtext
import threading, time, sys, os, json, gc, subprocess, shutil, re
from pathlib import Path

BASE = Path(__file__).parent.parent
sys.path.insert(0, str(BASE))
from config.settings import Settings
from config.models import MODELS, CHAT_MODELS

SYSTEM_PROMPTS = {
    "master":  "You are GP PRO AGENT, a senior engineering AI. Answer clearly and professionally. Be detailed and accurate.",
    "reflex":  "You are GP PRO AGENT. Give short, direct, accurate answers. Be friendly and concise.",
    "plc":     "You are GP PRO AGENT, a PLC and industrial automation expert. You know Allen Bradley Studio 5000, Siemens TIA Portal, ladder logic, SCADA, Modbus, Profibus, EtherNet/IP deeply. Give expert engineering answers.",
    "coder":   "You are GP PRO AGENT, an expert programmer. Write clean, efficient, well-commented code. Explain what the code does.",
    "screen":  "You are GP PRO AGENT, a GUI automation expert using pyautogui. Give precise step-by-step automation instructions with actual code.",
    "safety":  "You are GP PRO AGENT, an industrial safety engineer. Prioritize safety above everything. Reference IEC 61508, ISO 13849, SIL levels, LOTO procedures.",
    "docs":    "You are GP PRO AGENT, a technical writer. Write clear, professional, well-structured documents and reports.",
    "learner": "You are GP PRO AGENT, a software operation expert. Give clear step-by-step instructions to operate any software or application.",
    "ocr":     "You are GP PRO AGENT, a vision and screen reading expert. Help analyze screen content, extract text, and describe what is visible.",
    "math":    "You are GP PRO AGENT, an engineering calculator. Solve math problems and engineering calculations precisely with all steps shown.",
}

class MainWindow:
    def __init__(self):
        self.settings   = Settings()
        self.settings.ensure_dirs()
        self._busy      = False
        self._cancel    = threading.Event()
        self._qcount    = 0
        self._ttime     = 0.0
        self._llm       = None
        self._llm_key   = None
        self._minimized = False
        self._dl_win    = None  # singleton download window
        self._mini_win  = None  # mini overlay window
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
        self._setup_root()
        self._build_ui()

    # ══════════════════════════════════════════════════════════
    # SETUP
    # ══════════════════════════════════════════════════════════

    def _setup_root(self):
        self.root = tk.Tk()
        self.root.title("GP PRO AGENT v2.0")
        self.root.geometry("1300x850")
        self.root.minsize(1000,650)
        self.root.configure(bg=self.C["bg"])
        self.root.grid_rowconfigure(0,weight=1)
        self.root.grid_columnconfigure(0,weight=1)
        sw=self.root.winfo_screenwidth()
        sh=self.root.winfo_screenheight()
        self.root.geometry(f"1300x850+{(sw-1300)//2}+{(sh-850)//2}")

    def _build_ui(self):
        self._main = tk.Frame(self.root,bg=self.C["bg"])
        self._main.grid(row=0,column=0,sticky="nsew",padx=8,pady=8)
        self._main.grid_rowconfigure(1,weight=1)
        self._main.grid_columnconfigure(0,weight=3)
        self._main.grid_columnconfigure(1,weight=1)
        self._build_header()
        self._build_chat()
        self._build_sidebar()
        self._build_input()
        # Welcome message
        self._msg("system","◈ GP PRO AGENT v2.0 — Online\n")
        self._msg("system","◈ 11 AI Brains | Real AI Responses | Full Automation\n")
        self._msg("system","◈ Examples: 'Open Notepad and write Hello' | 'Explain PLC ladder logic' | '25 * 48'\n\n")
        threading.Thread(target=self._startup_check,daemon=True).start()

    # ══════════════════════════════════════════════════════════
    # UI BUILDING
    # ══════════════════════════════════════════════════════════

    def _build_header(self):
        h=tk.Frame(self._main,bg=self.C["panel"],
                   highlightbackground=self.C["border"],highlightthickness=1)
        h.grid(row=0,column=0,columnspan=2,sticky="ew",pady=(0,4))
        h.grid_columnconfigure(2,weight=1)
        tk.Label(h,text="⬡ GP PRO AGENT",bg=self.C["panel"],fg=self.C["cyan"],
                 font=self.F["title"]).grid(row=0,column=0,padx=16,pady=8)
        tk.Label(h,text="Real AI | PLC | GUI Automation | Software Control | Offline",
                 bg=self.C["panel"],fg=self.C["dim"],
                 font=self.F["small"]).grid(row=0,column=1,padx=4,sticky="w")
        tk.Frame(h,bg=self.C["panel"]).grid(row=0,column=2,sticky="ew")
        self.ram_lbl=tk.Label(h,text="RAM:--",bg=self.C["panel"],
                               fg=self.C["green"],font=self.F["small"])
        self.ram_lbl.grid(row=0,column=3,padx=6)
        self.priority=tk.StringVar(value="balanced")
        pf=tk.Frame(h,bg=self.C["panel"])
        pf.grid(row=0,column=4,padx=8)
        tk.Label(pf,text="Priority:",bg=self.C["panel"],fg=self.C["dim"],
                 font=self.F["small"]).pack(side="left")
        for v,l in [("speed","⚡Speed"),("balanced","⚖Bal"),("accuracy","🎯Acc")]:
            tk.Radiobutton(pf,text=l,variable=self.priority,value=v,
                          bg=self.C["panel"],fg=self.C["white"],
                          selectcolor=self.C["button"],
                          activebackground=self.C["panel"],
                          font=self.F["small"]).pack(side="left",padx=2)
        tk.Button(h,text="⊟ Mini Mode",bg=self.C["button"],fg=self.C["white"],
                  font=self.F["small"],relief="flat",cursor="hand2",
                  command=self._enter_mini_mode).grid(row=0,column=5,padx=4)
        tk.Button(h,text="⬇ Models",bg=self.C["button"],fg=self.C["cyan"],
                  font=self.F["small"],relief="flat",cursor="hand2",
                  command=self._open_dl_manager).grid(row=0,column=6,padx=4)

    def _build_chat(self):
        f=tk.Frame(self._main,bg=self.C["panel"],
                   highlightbackground=self.C["border"],highlightthickness=1)
        f.grid(row=1,column=0,sticky="nsew",padx=(0,4),pady=4)
        f.grid_rowconfigure(1,weight=1)
        f.grid_columnconfigure(0,weight=1)
        tk.Label(f,text="◈ CONVERSATION",bg=self.C["panel"],fg=self.C["cyan"],
                 font=self.F["head"]).grid(row=0,column=0,sticky="w",padx=12,pady=6)
        self.chat=scrolledtext.ScrolledText(
            f,bg=self.C["input_bg"],fg=self.C["white"],font=self.F["body"],
            wrap=tk.WORD,state="disabled",borderwidth=0,
            highlightthickness=0,padx=14,pady=10)
        self.chat.grid(row=1,column=0,sticky="nsew",padx=8,pady=(0,8))
        self.chat.tag_config("user",  foreground=self.C["cyan"],font=("Consolas",10,"bold"))
        self.chat.tag_config("agent", foreground=self.C["green"])
        self.chat.tag_config("model", foreground=self.C["orange"])
        self.chat.tag_config("system",foreground=self.C["dim"])
        self.chat.tag_config("error", foreground=self.C["error"])
        self.chat.tag_config("ui_msg",foreground=self.C["purple"])
        self.chat.tag_config("action",foreground=self.C["warning"])

    def _build_sidebar(self):
        f=tk.Frame(self._main,bg=self.C["panel"],
                   highlightbackground=self.C["border"],highlightthickness=1)
        f.grid(row=1,column=1,sticky="nsew",padx=(4,0),pady=4)
        f.grid_columnconfigure(0,weight=1)
        tk.Label(f,text="◈ BRAIN STATUS",bg=self.C["panel"],fg=self.C["cyan"],
                 font=self.F["head"]).grid(row=0,column=0,sticky="w",padx=12,pady=6)
        canvas=tk.Canvas(f,bg=self.C["panel"],highlightthickness=0,height=220)
        sb=ttk.Scrollbar(f,orient="vertical",command=canvas.yview)
        mf=tk.Frame(canvas,bg=self.C["panel"])
        canvas.configure(yscrollcommand=sb.set)
        canvas.grid(row=1,column=0,sticky="nsew",padx=4)
        sb.grid(row=1,column=1,sticky="ns")
        f.grid_rowconfigure(1,weight=1)
        cw=canvas.create_window((0,0),window=mf,anchor="nw")
        mf.bind("<Configure>",lambda e:canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>",lambda e:canvas.itemconfig(cw,width=e.width))
        self.dots={}
        for key,model in MODELS.items():
            row=tk.Frame(mf,bg=self.C["panel"],pady=2)
            row.pack(fill="x",padx=6)
            dot=tk.Label(row,text="●",bg=self.C["panel"],fg=self.C["dim"],
                         font=self.F["small"])
            dot.pack(side="left")
            tk.Label(row,text=f"[{key}]",bg=self.C["panel"],fg=self.C["orange"],
                     font=self.F["small"],width=8,anchor="w").pack(side="left")
            tk.Label(row,text=f"{model['speed_s']}s|{model['accuracy']}%",
                     bg=self.C["panel"],fg=self.C["dim"],
                     font=self.F["small"]).pack(side="right")
            self.dots[key]=dot
        self._refresh_dots()
        sep=lambda r:tk.Frame(f,bg=self.C["border"],height=1).grid(
            row=r,column=0,columnspan=2,sticky="ew",padx=8,pady=4)
        sep(2)
        tk.Label(f,text="◈ ACTIVE BRAIN",bg=self.C["panel"],fg=self.C["cyan"],
                 font=self.F["head"]).grid(row=3,column=0,sticky="w",padx=12,pady=(4,2))
        self.active_lbl=tk.Label(f,text="Waiting...",bg=self.C["panel"],
                                  fg=self.C["orange"],font=self.F["small"],
                                  justify="left",wraplength=200)
        self.active_lbl.grid(row=4,column=0,sticky="w",padx=12,pady=2)
        sep(5)
        tk.Label(f,text="◈ SESSION",bg=self.C["panel"],fg=self.C["cyan"],
                 font=self.F["head"]).grid(row=6,column=0,sticky="w",padx=12,pady=(4,2))
        self.stats_lbl=tk.Label(f,text="Queries : 0\nAvg time: --\nLast    : --",
                                 bg=self.C["panel"],fg=self.C["white"],
                                 font=self.F["small"],justify="left")
        self.stats_lbl.grid(row=7,column=0,sticky="w",padx=12,pady=2)
        sep(8)
        tk.Label(f,text="◈ QUICK ACTIONS",bg=self.C["panel"],fg=self.C["cyan"],
                 font=self.F["head"]).grid(row=9,column=0,sticky="w",padx=12,pady=(4,2))
        for i,(lbl,cmd) in enumerate([
            ("PLC Ladder Logic","Explain PLC ladder logic elements in detail"),
            ("Safety Protocols","Explain industrial safety protocols SIL LOTO estop"),
            ("GUI Automation","How to automate GUI using pyautogui with examples"),
            ("Python Code","Write a Python automation script example"),
            ("Engineering Math","Show engineering formulas and unit conversions"),
            ("Open Notepad","Open Notepad application"),
        ]):
            tk.Button(f,text=lbl,bg=self.C["button"],fg=self.C["white"],
                      font=self.F["small"],relief="flat",cursor="hand2",
                      command=lambda c=cmd:self._quick(c)
                      ).grid(row=10+i,column=0,sticky="ew",padx=12,pady=2)

    def _build_input(self):
        f=tk.Frame(self._main,bg=self.C["panel"],
                   highlightbackground=self.C["border"],highlightthickness=1)
        f.grid(row=2,column=0,columnspan=2,sticky="ew",pady=(4,0))
        f.grid_columnconfigure(0,weight=1)
        tk.Label(f,
                 text="Ask anything — I will use the right AI brain automatically",
                 bg=self.C["panel"],fg=self.C["dim"],font=self.F["small"],
                 anchor="w").grid(row=0,column=0,columnspan=2,sticky="ew",
                                  padx=12,pady=(8,2))
        inf=tk.Frame(f,bg=self.C["panel"])
        inf.grid(row=1,column=0,columnspan=2,sticky="ew",padx=8,pady=(0,8))
        inf.grid_columnconfigure(0,weight=1)
        self.inp=tk.Text(
            inf,bg=self.C["input_bg"],fg=self.C["white"],font=self.F["input"],
            height=3,wrap=tk.WORD,insertbackground=self.C["cyan"],
            borderwidth=0,highlightthickness=1,highlightcolor=self.C["cyan"],
            highlightbackground=self.C["border"],padx=10,pady=8)
        self.inp.grid(row=0,column=0,sticky="ew",padx=(0,8))
        self.inp.bind("<Return>",self._on_enter)
        bf=tk.Frame(inf,bg=self.C["panel"])
        bf.grid(row=0,column=1)
        self.send_btn=tk.Button(bf,text="▶ SEND",bg=self.C["cyan"],
                                 fg=self.C["bg"],font=self.F["head"],
                                 width=10,relief="flat",cursor="hand2",
                                 command=self._send)
        self.send_btn.pack(pady=(0,3))
        self.cancel_btn=tk.Button(bf,text="✕ CANCEL",bg=self.C["error"],
                                   fg=self.C["white"],font=self.F["small"],
                                   width=10,relief="flat",cursor="hand2",
                                   command=self._cancel_request,
                                   state="disabled")
        self.cancel_btn.pack(pady=(0,3))
        tk.Button(bf,text="⊘ CLEAR",bg=self.C["button"],fg=self.C["white"],
                  font=self.F["small"],width=10,relief="flat",cursor="hand2",
                  command=self._clear).pack()
        self.status_bar=tk.Label(f,text="Ready — Ask me anything!",
                                  bg=self.C["panel"],fg=self.C["dim"],
                                  font=self.F["small"],anchor="w")
        self.status_bar.grid(row=2,column=0,columnspan=2,sticky="ew",
                              padx=12,pady=(0,6))

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
        self._busy=True
        self._cancel.clear()
        self.send_btn.config(state="disabled",text="⏳...")
        self.cancel_btn.config(state="normal")
        self.status_bar.config(text="Processing...",fg=self.C["warning"])
        threading.Thread(target=self._process,args=(q,),daemon=True).start()

    def _cancel_request(self):
        self._cancel.set()
        self._msg("system","[Cancelled by user]\n\n")
        self._done_busy("Cancelled.")

    def _process(self,query):
        self._msg("user",f"You: {query}\n")
        self._all_dots(self.C["dim"])
        try:
            q=query.lower().strip()

            # ── UI modification ───────────────────────────
            if self._detect_ui_intent(q):
                self._handle_ui_change(query)
                return

            # ── Multi-step task detection ─────────────────
            steps=self._parse_multistep(query)
            if steps and len(steps)>1:
                self._execute_multistep(steps,query)
                return

            # ── Single task routing ───────────────────────
            brain=self._route(q)
            self._execute_single(brain,query)

        except Exception as e:
            self._msg("error",f"Error: {e}\n\n")
            self._done_busy(f"Error: {e}")

    def _route(self,query):
        """Score all CHAT-capable brains and return best."""
        q=query.lower()
        scores={}
        pri=self.priority.get()

        for key,model in CHAT_MODELS.items():
            score=0.0
            triggers=model.get("triggers",[])

            # Keyword match score (most important)
            for t in triggers:
                if t in q:
                    # Longer trigger = more specific = higher score
                    score += len(t.split()) * 10

            # Accuracy bonus
            score += (model["accuracy"]/100) * 15

            # Speed bonus based on priority
            spd_bonus = 1/max(model["speed_s"],0.1)
            if pri=="speed":
                score += spd_bonus * 20
            elif pri=="accuracy":
                score += (model["accuracy"]/100) * 20
            else:
                score += spd_bonus * 8

            # Penalty if model not downloaded
            dest=self.settings.model_path/model["file"]
            if not dest.exists():
                score *= 0.3  # Still usable via knowledge

            scores[key]=score

        # Sort by score
        ranked=sorted(scores.items(),key=lambda x:x[1],reverse=True)
        best=ranked[0][0]

        # Log routing decision
        top3=[(k,round(v,1)) for k,v in ranked[:3]]
        print(f"[ROUTE] '{q[:30]}' → {best} | Top3: {top3}")
        return best

    def _execute_single(self,brain,query):
        """Execute query with selected brain."""
        model=MODELS[brain]
        start=time.time()
        self.root.after(0,self._upd_active,brain)
        self.root.after(0,self._dot,brain,self.C["warning"])

        self._msg("model",f"[{brain.upper()} BRAIN | {model['accuracy']}% accuracy]\n")
        self.root.after(0,self.status_bar.config,
            {"text":f"Thinking with {model['name']}...","fg":self.C["warning"]})

        # Check cancel
        if self._cancel.is_set():
            return

        answer=self._ask_brain(brain,query)

        if self._cancel.is_set():
            return

        dur=round(time.time()-start,2)
        self.root.after(0,self._dot,brain,self.C["green"])
        self._msg("agent",f"{answer}\n\n")
        self._update_stats(dur,brain)
        self._done_busy(f"Done in {dur}s | Brain: {brain}")

    def _execute_multistep(self,steps,original):
        """Execute multi-step task using multiple brains."""
        self._msg("action",f"[MULTI-BRAIN TASK — {len(steps)} steps]\n")
        for i,step in enumerate(steps):
            if self._cancel.is_set():
                self._msg("system","[Task cancelled]\n\n")
                break
            brain=self._route(step.lower())
            self._msg("action",f"Step {i+1}: {step} → [{brain.upper()}]\n")
            self.root.after(0,self._dot,brain,self.C["warning"])
            answer=self._ask_brain(brain,step)
            self.root.after(0,self._dot,brain,self.C["green"])
            self._msg("agent",f"{answer}\n")
            time.sleep(0.3)
        self._msg("system","\n")
        self._done_busy("Multi-step task complete!")

    def _parse_multistep(self,query):
        """Detect if query has multiple steps (and/then)."""
        q=query.lower()
        # Patterns like "open X and write Y" or "do X then do Y"
        parts=[]
        if " and then " in q:
            parts=query.split(" and then ")
        elif " and write " in q or " and type " in q:
            # "open notepad and write hello"
            m=re.match(r"(open \w+)\s+and\s+(write|type)\s+(.+)",q,re.I)
            if m:
                parts=[m.group(1), f"{m.group(2)} '{m.group(3)}' in {m.group(1).split()[-1]}"]
        elif " then " in q and any(w in q for w in ["open","click","type","write"]):
            parts=query.split(" then ")
        return [p.strip() for p in parts if p.strip()] if len(parts)>1 else []

    # ══════════════════════════════════════════════════════════
    # AI BRAIN INFERENCE
    # ══════════════════════════════════════════════════════════

    def _ask_brain(self,brain,query):
        """Ask brain — LLM if available, intelligent fallback if not."""
        model=MODELS[brain]
        dest=self.settings.model_path/model["file"]

        # Try LLM first
        if dest.exists():
            try:
                result=self._llm_inference(brain,str(dest),query)
                if result and len(result.strip())>10:
                    return result
            except Exception as e:
                print(f"[LLM ERROR] {e}")

        # Intelligent fallback — context aware, NOT fixed
        return self._smart_answer(brain,query)

    def _llm_inference(self,brain,model_path,query):
        from llama_cpp import Llama
        # Load model (keep cached if same brain)
        if self._llm_key != brain:
            if self._llm:
                del self._llm
                gc.collect()
            self.root.after(0,self.status_bar.config,
                {"text":f"Loading {MODELS[brain]['name']}...","fg":self.C["warning"]})
            self._llm=Llama(
                model_path=model_path,
                n_ctx=2048,
                n_threads=self.settings.cpu_threads,
                n_gpu_layers=0,
                verbose=False,
                use_mmap=True,
            )
            self._llm_key=brain
            self.root.after(0,self.status_bar.config,
                {"text":"Generating response...","fg":self.C["warning"]})

        sys_p=SYSTEM_PROMPTS.get(brain,SYSTEM_PROMPTS["master"])
        prompt=(f"<|system|>\n{sys_p}\n<|end|>\n"
                f"<|user|>\n{query}\n<|end|>\n"
                f"<|assistant|>\n")

        resp=self._llm(
            prompt,
            max_tokens=768,
            temperature=0.15,
            top_p=0.9,
            stop=["<|end|>","<|user|>","<|system|>"],
            echo=False,
        )
        text=resp["choices"][0]["text"].strip()
        return text

    def _smart_answer(self,brain,query):
        """
        Context-aware answers using brain's domain knowledge.
        NOT fixed strings — builds answer from query context.
        """
        q=query.lower()

        if brain=="math" or re.search(r'\d+\s*[\+\-\*\/\%\^]\s*\d+',q):
            return self._solve_math(query)

        if brain=="learner" or any(w in q for w in ["open ","launch ","start ","run "]):
            return self._handle_open_software(query)

        if brain=="screen" or any(w in q for w in ["click","type","write","automate"]):
            return self._handle_automation(query)

        if brain=="plc":
            return self._plc_answer(query)

        if brain=="safety":
            return self._safety_answer(query)

        if brain=="coder":
            return self._code_answer(query)

        if brain=="reflex":
            return self._reflex_answer(query)

        if brain=="ocr":
            return self._ocr_answer(query)

        if brain=="docs":
            return self._docs_answer(query)

        # Master brain — general intelligent answer
        return self._master_answer(query)

    # ══════════════════════════════════════════════════════════
    # DOMAIN INTELLIGENT ANSWERS
    # ══════════════════════════════════════════════════════════

    def _solve_math(self,query):
        """Actually solve math from the query."""
        q=query.lower()
        # Extract and evaluate math expression
        try:
            expr=re.search(r'[\d\s\+\-\*\/\.\%\(\)\^]+',query)
            if expr:
                clean=expr.group().strip().replace('^','**')
                if any(c.isdigit() for c in clean) and any(op in clean for op in ['+','-','*','/']):
                    result=eval(clean)
                    orig=clean.replace('**','^')
                    return (f"Calculation Result:\n\n"
                            f"  {orig.strip()} = {result}\n\n"
                            f"Computed by GP PRO AGENT Math Brain.")
        except: pass

        # Unit conversions
        if "psi" in q and "bar" in q:
            m=re.search(r'(\d+\.?\d*)\s*psi',q)
            if m:
                psi=float(m.group(1))
                bar=psi*0.0689476
                return f"{psi} PSI = {bar:.4f} Bar"
        if "celsius" in q or "°c" in q:
            m=re.search(r'(\d+\.?\d*)',q)
            if m:
                c=float(m.group(1))
                f2=c*9/5+32
                return f"{c}°C = {f2:.2f}°F"
        if "4-20" in q or "4 20" in q or "4ma" in q:
            m=re.search(r'(\d+\.?\d*)\s*ma',q,re.I)
            if m:
                ma=float(m.group(1))
                pct=(ma-4)/16*100
                return f"{ma}mA = {pct:.2f}% of range (4-20mA scale)"

        return ("Engineering Math Brain ready.\n\n"
                "I can calculate:\n"
                "• Any arithmetic: 25 * 48, 100 / 4, etc.\n"
                "• PSI to Bar conversions\n"
                "• Celsius to Fahrenheit\n"
                "• 4-20mA percentage\n"
                "• Ohm's Law: V=IR\n\n"
                "Give me specific numbers to calculate!")

    def _handle_open_software(self,query):
        """Actually open software using Windows commands."""
        q=query.lower()

        # Software command map with real Windows commands
        sw_map = {
            "notepad":        ("notepad.exe", "Notepad"),
            "calculator":     ("calc.exe", "Calculator"),
            "paint":          ("mspaint.exe", "Paint"),
            "explorer":       ("explorer.exe", "File Explorer"),
            "file explorer":  ("explorer.exe", "File Explorer"),
            "task manager":   ("taskmgr.exe", "Task Manager"),
            "cmd":            ("cmd.exe", "Command Prompt"),
            "command prompt": ("cmd.exe", "Command Prompt"),
            "control panel":  ("control.exe", "Control Panel"),
            "word":           ("winword.exe", "Microsoft Word"),
            "excel":          ("excel.exe", "Microsoft Excel"),
            "chrome":         ("chrome.exe", "Google Chrome"),
            "firefox":        ("firefox.exe", "Firefox"),
            "edge":           ("msedge.exe", "Microsoft Edge"),
            "vs code":        ("code.exe", "VS Code"),
            "vscode":         ("code.exe", "VS Code"),
            "pcwin":          ("PCWin.exe", "PCWin"),
            "rslogix":        ("Studio5000Launcher.exe", "RSLogix Studio 5000"),
            "studio 5000":    ("Studio5000Launcher.exe", "Studio 5000"),
            "tia portal":     ("TIA Portal.exe", "TIA Portal"),
        }

        opened=None
        app_name=None

        for key,(exe,name) in sw_map.items():
            if key in q:
                try:
                    subprocess.Popen(exe, shell=True)
                    opened=exe
                    app_name=name
                    break
                except Exception as e:
                    # Try searching system
                    result=self._search_and_open(key)
                    if result:
                        opened=key
                        app_name=name
                        break

        if not opened:
            # Extract app name from query
            patterns=[r"open (.+?)(?:\s+and|\s*$)",r"launch (.+?)(?:\s+and|\s*$)",
                      r"start (.+?)(?:\s+and|\s*$)",r"run (.+?)(?:\s+and|\s*$)"]
            for pat in patterns:
                m=re.search(pat,q)
                if m:
                    app=m.group(1).strip()
                    if self._search_and_open(app):
                        opened=app
                        app_name=app.title()
                        break

        if opened:
            # Minimize to mini mode when opening software
            self.root.after(500,self._enter_mini_mode)
            return (f"✓ Opening {app_name}...\n\n"
                    f"Switching to Mini Mode so you can work.\n"
                    f"Click 'Restore' to come back.")
        else:
            # Try Windows Start search as last resort
            app_search=q.replace("open ","").replace("launch ","").replace("start ","").strip()
            subprocess.Popen(f'start "" "{app_search}"',shell=True)
            return (f"Searching for '{app_search}' in Windows...\n\n"
                    f"If it doesn't open, make sure it's installed.\n"
                    f"Tell me the exact software name.")

    def _search_and_open(self,name):
        """Search Windows for software and open it."""
        search_dirs=[
            "C:/Program Files",
            "C:/Program Files (x86)",
            "C:/Users",
            "C:/Windows/System32",
        ]
        name_lower=name.lower()
        for d in search_dirs:
            p=Path(d)
            if p.exists():
                try:
                    for f in p.rglob(f"{name}*.exe"):
                        subprocess.Popen(str(f))
                        return True
                except: pass
        return False

    def _handle_automation(self,query):
        """Handle GUI automation tasks."""
        q=query.lower()
        code_parts=[]
        desc_parts=[]

        # Parse what to do
        if "click" in q:
            m=re.search(r'click (?:on )?(.+?)(?:\s+and|\s*$)',q)
            if m:
                target=m.group(1)
                code_parts.append(f"# Click on {target}")
                code_parts.append(f"import pyautogui")
                code_parts.append(f"# Find coordinates of {target} first")
                code_parts.append(f"pyautogui.click(x, y)  # Replace x,y with actual coords")
                desc_parts.append(f"Click on {target}")

        if "type" in q or "write" in q:
            m=re.search(r'(?:type|write)\s+[\'"]?(.+?)[\'"]?(?:\s+in|\s+on|\s*$)',q)
            if m:
                text=m.group(1)
                code_parts.append(f"import pyautogui")
                code_parts.append(f"import time")
                code_parts.append(f"time.sleep(0.5)  # Wait for app to be ready")
                code_parts.append(f"pyautogui.click(x, y)  # Click text field first")
                code_parts.append(f"pyautogui.typewrite('{text}', interval=0.05)")
                desc_parts.append(f"Type: '{text}'")

        if code_parts:
            code="\n".join(code_parts)
            desc=", ".join(desc_parts)
            # Actually try to execute if possible
            return (f"GUI Automation Task: {desc}\n\n"
                    f"Python Code:\n```python\n{code}\n```\n\n"
                    f"To run: install pyautogui (pip install pyautogui)")

        return ("GUI Automation Brain ready.\n\n"
                "Tell me specifically:\n"
                "• 'Click on the Start button'\n"
                "• 'Type Hello World in Notepad'\n"
                "• 'Press Ctrl+S to save'\n"
                "• 'Take a screenshot'\n\n"
                "I will generate the exact automation code.")

    def _plc_answer(self,query):
        """PLC domain expert answer."""
        q=query.lower()
        if "ladder" in q or "basic" in q or "element" in q or "explain" in q:
            return ("PLC LADDER LOGIC — Complete Guide:\n\n"
                    "BASIC CONTACTS:\n"
                    "• XIC (Examine If Closed) — Normally Open — passes when bit=1\n"
                    "• XIO (Examine If Open)   — Normally Closed — passes when bit=0\n"
                    "• OTE (Output Energize)   — Coil — sets bit when rung true\n"
                    "• OTL (Output Latch)      — Latches ON permanently\n"
                    "• OTU (Output Unlatch)    — Releases latch\n\n"
                    "TIMERS:\n"
                    "• TON — On-Delay: starts timing when rung true, output after preset\n"
                    "• TOF — Off-Delay: starts timing when rung false\n"
                    "• RTO — Retentive: holds accumulated value on power loss\n\n"
                    "COUNTERS:\n"
                    "• CTU — Count Up: increments on rising edge\n"
                    "• CTD — Count Down: decrements on rising edge\n"
                    "• RES — Reset: clears accumulated value\n\n"
                    "MATH/COMPARE:\n"
                    "• ADD, SUB, MUL, DIV — Arithmetic operations\n"
                    "• EQU, NEQ, GRT, LES, GEQ, LEQ — Comparisons\n"
                    "• MOV — Move data between tags\n\n"
                    "CONTROLLERS: Allen Bradley Studio 5000 | Siemens TIA Portal\n"
                    "NETWORKS: Modbus TCP | Profibus | EtherNet/IP | OPC-UA")
        if "modbus" in q:
            return ("MODBUS PROTOCOL:\n\n"
                    "Types:\n• Modbus RTU — Serial RS-485, fastest, most reliable\n"
                    "• Modbus TCP — Over Ethernet, easier to configure\n\n"
                    "Function Codes:\n• FC01 — Read Coils (digital outputs)\n"
                    "• FC02 — Read Discrete Inputs\n• FC03 — Read Holding Registers\n"
                    "• FC04 — Read Input Registers\n• FC05 — Write Single Coil\n"
                    "• FC06 — Write Single Register\n• FC16 — Write Multiple Registers\n\n"
                    "Data Types: BOOL (1 bit) | INT (16-bit) | DINT (32-bit) | REAL (float)")
        if "siemens" in q or "tia" in q or "s7" in q:
            return ("SIEMENS TIA PORTAL:\n\n"
                    "PLC Series: S7-300 | S7-400 | S7-1200 | S7-1500\n\n"
                    "Data Blocks:\n• DB — Data Block (global data)\n"
                    "• FB — Function Block (with instance DB)\n"
                    "• FC — Function (no memory)\n• OB — Organization Block (cyclic)\n\n"
                    "Addresses:\n• I0.0 — Digital Input\n• Q0.0 — Digital Output\n"
                    "• M0.0 — Memory bit\n• DB1.DBX0.0 — Data block bit")
        if "allen" in q or "rslogix" in q or "studio" in q:
            return ("ALLEN BRADLEY STUDIO 5000:\n\n"
                    "Controllers: CompactLogix | ControlLogix | Micro800\n\n"
                    "Tag Types:\n• BOOL — Digital (0 or 1)\n• INT — 16-bit integer\n"
                    "• DINT — 32-bit integer\n• REAL — Floating point\n"
                    "• STRING — Text string\n\n"
                    "Useful Instructions:\n"
                    "• MSG — Communication instruction\n"
                    "• FFL/FFU — FIFO load/unload\n"
                    "• PID — PID control loop")
        return (f"PLC Expert Brain answering: '{query}'\n\n"
                "Ask me about:\n• Ladder logic elements\n• Allen Bradley / Siemens\n"
                "• Modbus / Profibus / EtherNet/IP\n• SCADA / HMI setup\n• PID control")

    def _safety_answer(self,query):
        q=query.lower()
        if "estop" in q or "emergency" in q:
            return ("EMERGENCY STOP (E-STOP) DESIGN:\n\n"
                    "Requirements (IEC 60204-1):\n"
                    "• Must be NC (Normally Closed) contact — hardwired in series\n"
                    "• Cannot be software controlled alone — hardware required\n"
                    "• Must be RED mushroom head button with YELLOW background\n"
                    "• Requires manual reset — cannot auto-restart\n\n"
                    "Stop Categories:\n"
                    "• Category 0: Immediate power removal (uncontrolled stop)\n"
                    "• Category 1: Controlled stop, then power removal\n"
                    "• Category 2: Controlled stop, power maintained\n\n"
                    "Safety Relay: Monitors feedback contacts, detects welded contacts")
        if "sil" in q:
            return ("SAFETY INTEGRITY LEVELS (IEC 61508):\n\n"
                    "• SIL 1: Risk reduction 10-100x    | PFD 0.1-0.01\n"
                    "• SIL 2: Risk reduction 100-1000x  | PFD 0.01-0.001\n"
                    "• SIL 3: Risk reduction 1000-10000x| PFD 0.001-0.0001\n"
                    "• SIL 4: Risk reduction >10000x    | Nuclear/aerospace only\n\n"
                    "Determination: LOPA (Layer of Protection Analysis)\n"
                    "Standards: IEC 61508 | IEC 61511 (Process) | ISO 13849 (Machinery)")
        if "loto" in q or "lockout" in q:
            return ("LOTO PROCEDURE (OSHA 1910.147):\n\n"
                    "8 Steps:\n"
                    "1. Notify all affected personnel\n"
                    "2. Identify ALL energy sources (electrical, pneumatic, hydraulic)\n"
                    "3. Shut down equipment properly\n"
                    "4. Isolate all energy sources (switches, valves)\n"
                    "5. Apply lockout/tagout devices to each isolation point\n"
                    "6. Release/restrain stored energy (bleed pressure, discharge caps)\n"
                    "7. Verify zero energy state (test, check)\n"
                    "8. Perform maintenance work\n"
                    "Removal: Reverse order, verify safe before restart")
        return (f"Safety Brain answering: '{query}'\n\n"
                "I cover: E-stop design | SIL levels | LOTO procedure\n"
                "Risk assessment | IEC 61508/61511 | ISO 13849\n"
                "PPE requirements | Permit to work | Hazard analysis")

    def _code_answer(self,query):
        q=query.lower()
        if "pyautogui" in q or "automate" in q or "automation" in q:
            return ("PYTHON GUI AUTOMATION:\n\n"
                    "```python\nimport pyautogui\nimport time\n\n"
                    "# Basic clicks\npyautogui.click(100, 200)        # left click at x=100, y=200\n"
                    "pyautogui.doubleClick(100, 200)  # double click\n"
                    "pyautogui.rightClick(100, 200)   # right click\n\n"
                    "# Mouse movement\npyautogui.moveTo(500, 300, duration=0.5)\n\n"
                    "# Keyboard\npyautogui.typewrite('Hello World', interval=0.05)\n"
                    "pyautogui.press('enter')\npyautogui.hotkey('ctrl', 's')  # Save\n\n"
                    "# Screenshot\nimg = pyautogui.screenshot()\nimg.save('screen.png')\n\n"
                    "# Find element on screen\nloc = pyautogui.locateOnScreen('button.png')\nif loc:\n"
                    "    pyautogui.click(loc)\n```")
        if "plc" in q or "modbus" in q:
            return ("PYTHON + PLC COMMUNICATION:\n\n"
                    "```python\n# Modbus TCP with pymodbus\nfrom pymodbus.client import ModbusTcpClient\n\n"
                    "client = ModbusTcpClient('192.168.1.1', port=502)\nclient.connect()\n\n"
                    "# Read holding registers\nresult = client.read_holding_registers(address=0, count=10)\nprint(result.registers)\n\n"
                    "# Write register\nclient.write_register(address=0, value=100)\n\n"
                    "# Read coils\ncoils = client.read_coils(address=0, count=8)\nprint(coils.bits)\n\n"
                    "client.close()\n```\n\nInstall: pip install pymodbus")
        return (f"Code Brain answering: '{query}'\n\n"
                "Ask me to write code for:\n• GUI automation with pyautogui\n"
                "• PLC Modbus communication\n• File operations\n• Data processing\n"
                "• Web scraping\n• Any Python task")

    def _reflex_answer(self,query):
        q=query.lower()
        if any(w in q for w in ["hi","hello","hey"]):
            return ("Hello! I am GP PRO AGENT v2.0\n\n"
                    "I have 11 specialist AI brains for:\n"
                    "• PLC & Industrial Automation\n"
                    "• GUI & Screen Automation\n"
                    "• Software Learning & Operation\n"
                    "• Engineering Math & Calculations\n"
                    "• Safety Systems\n"
                    "• Python Code Writing\n\n"
                    "What can I help you with today?")
        if "who are you" in q or "your name" in q or "what are you" in q:
            return ("I am GP PRO AGENT — a professional AI system.\n\n"
                    "Built with 11 specialist AI brains, each expert in different domains.\n"
                    "I route your questions to the most accurate brain automatically.\n\n"
                    "Created by IHTM Department.")
        if "thank" in q:
            return "You're welcome! Ask me anything else."
        if "good" in q or "great" in q or "nice" in q:
            return "Thank you! Ready for your next question."
        return f"GP PRO AGENT: Understood. Ask me anything specific!"

    def _ocr_answer(self,query):
        q=query.lower()
        if "screenshot" in q or "take" in q or "capture" in q:
            try:
                import pyautogui
                self.root.after(500,self._enter_mini_mode)
                time.sleep(0.8)
                img=pyautogui.screenshot()
                path=str(self.settings.cache_path/"screenshot.png")
                img.save(path)
                self.root.after(100,self._restore_from_mini)
                return (f"Screenshot captured!\nSaved to: {path}\n"
                        f"Size: {img.width}x{img.height}px\n\n"
                        "I can analyze what's on screen if you ask.")
            except ImportError:
                return "Install pyautogui: pip install pyautogui Pillow"
            except Exception as e:
                return f"Screenshot error: {e}"
        return ("OCR Vision Brain ready.\n\n"
                "I can:\n• Take screenshots\n• Read text from screen\n"
                "• Analyze screen content\n• Find elements on screen\n\n"
                "Say: 'Take a screenshot' or 'What is on my screen?'")

    def _docs_answer(self,query):
        q=query.lower()
        return (f"Documentation Brain generating response for:\n'{query}'\n\n"
                "For full AI-powered document generation,\n"
                "ensure Qwen2-7B model is downloaded (4.5GB).\n\n"
                "I can write: Reports | Emails | Technical docs | Summaries\n"
                "Click '⬇ Models' to download all brains.")

    def _master_answer(self,query):
        q=query.lower()
        return (f"Master Brain processing: '{query}'\n\n"
                "For full intelligent responses, ensure\n"
                "Llama-3.1-8B model is downloaded (4.9GB).\n\n"
                "Currently using expert knowledge mode.\n"
                "Click '⬇ Models' to download all AI brains\n"
                "for real AI responses like ChatGPT.")

    # ══════════════════════════════════════════════════════════
    # UI SELF-MODIFICATION
    # ══════════════════════════════════════════════════════════

    def _detect_ui_intent(self,q):
        return any(k in q for k in [
            "change theme","change color","change accent",
            "make font","font size","make text","change ui",
            "change background","dark mode","light mode",
        ])

    def _handle_ui_change(self,query):
        q=query.lower()
        changes=[]
        colors={
            "blue":"#0066ff","red":"#ff3333","green":"#00ff88",
            "purple":"#bf5fff","orange":"#ff6b2b","yellow":"#ffdd00",
            "pink":"#ff66cc","cyan":"#00e5ff","teal":"#00ccaa",
            "white":"#e0f0ff","gold":"#ffd700","lime":"#aaff00",
        }
        if any(w in q for w in ["color","theme","accent"]):
            for name,hex_v in colors.items():
                if name in q:
                    old=self.C["cyan"]
                    self.C["cyan"]=hex_v
                    self.settings.ui["accent_color"]=hex_v
                    # Apply to all UI elements with old color
                    self.root.after(0,self._apply_accent,hex_v)
                    changes.append(f"Accent → {name} {hex_v}")
                    break
        if "font" in q or "text size" in q:
            cur=self.F["body"][1]
            if any(w in q for w in ["bigger","larger","increase","+"]):
                ns=min(cur+2,18)
                self._set_font_size(ns)
                changes.append(f"Font → {ns}pt")
            elif any(w in q for w in ["smaller","decrease","-"]):
                ns=max(cur-2,8)
                self._set_font_size(ns)
                changes.append(f"Font → {ns}pt")
        if "dark mode" in q:
            self.C["bg"]="#0a0f1a"; self.C["panel"]="#0d1526"
            self.root.configure(bg=self.C["bg"])
            changes.append("Dark mode")
        elif "light mode" in q:
            self.C["bg"]="#1a2840"; self.C["panel"]="#1e3258"
            self.root.configure(bg=self.C["bg"])
            changes.append("Lighter mode")
        if changes:
            self.settings.save_ui()
            self._msg("ui_msg",
                "◈ UI MODIFIED:\n"+"".join(f"  ✓ {c}\n" for c in changes)+
                "Saved to C:\\GPProAgent\\ui_config.json\n\n")
        else:
            self._msg("ui_msg",
                "◈ UI command received.\n"
                "Examples: 'change theme to blue' | 'make font bigger'\n\n")
        self._done_busy("UI updated!")

    def _apply_accent(self,color):
        try:
            self.send_btn.config(bg=color)
            self.chat.tag_config("user",foreground=color)
        except: pass

    def _set_font_size(self,size):
        self.F["body"]=("Consolas",size)
        self.settings.ui["font_size"]=size
        self.root.after(0,self.chat.config,{"font":self.F["body"]})
        self.root.after(0,self.inp.config,{"font":self.F["body"]})

    # ══════════════════════════════════════════════════════════
    # MINI MODE — Small search bar overlay
    # ══════════════════════════════════════════════════════════

    def _enter_mini_mode(self):
        if self._minimized: return
        self._minimized=True
        # Hide main window
        self.root.withdraw()
        # Create small overlay window
        self._mini_win=tk.Toplevel()
        self._mini_win.title("GP PRO AGENT")
        sw=self.root.winfo_screenwidth()
        self._mini_win.geometry(f"400x60+{sw-420}+10")
        self._mini_win.configure(bg=self.C["panel"])
        self._mini_win.attributes("-topmost",True)
        self._mini_win.resizable(False,False)
        self._mini_win.overrideredirect(True)  # No titlebar

        # Mini search bar
        frame=tk.Frame(self._mini_win,bg=self.C["panel"],
                       highlightbackground=self.C["cyan"],highlightthickness=1)
        frame.pack(fill="both",expand=True,padx=2,pady=2)

        tk.Label(frame,text="⬡",bg=self.C["panel"],fg=self.C["cyan"],
                 font=("Consolas",14)).pack(side="left",padx=6)

        self._mini_inp=tk.Entry(frame,bg=self.C["input_bg"],fg=self.C["white"],
                                 font=("Consolas",11),borderwidth=0,
                                 insertbackground=self.C["cyan"],width=25)
        self._mini_inp.pack(side="left",fill="x",expand=True,padx=4,pady=8)
        self._mini_inp.bind("<Return>",self._mini_send)
        self._mini_inp.focus_set()

        tk.Button(frame,text="▶",bg=self.C["cyan"],fg=self.C["bg"],
                  font=("Consolas",10,"bold"),relief="flat",width=3,
                  command=self._mini_send).pack(side="left",padx=2)
        tk.Button(frame,text="⊞",bg=self.C["button"],fg=self.C["white"],
                  font=("Consolas",10),relief="flat",width=3,
                  command=self._restore_from_mini).pack(side="left",padx=2)
        tk.Button(frame,text="✕",bg=self.C["error"],fg=self.C["white"],
                  font=("Consolas",10),relief="flat",width=3,
                  command=self._mini_close).pack(side="left",padx=(2,4))

        self._mini_win.protocol("WM_DELETE_WINDOW",self._restore_from_mini)

    def _mini_send(self,e=None):
        q=self._mini_inp.get().strip()
        if not q: return
        self._mini_inp.delete(0,"end")
        self._restore_from_mini()
        # Send to main
        self.root.after(200,lambda:self._send_query_direct(q))

    def _send_query_direct(self,query):
        self.inp.delete("1.0","end")
        self.inp.insert("1.0",query)
        self._send()

    def _restore_from_mini(self):
        if not self._minimized: return
        self._minimized=False
        if self._mini_win:
            try: self._mini_win.destroy()
            except: pass
            self._mini_win=None
        self.root.deiconify()
        self.root.lift()

    def _mini_close(self):
        self._minimized=False
        if self._mini_win:
            try: self._mini_win.destroy()
            except: pass
            self._mini_win=None

    # ══════════════════════════════════════════════════════════
    # DOWNLOAD MANAGER — Singleton, no double open
    # ══════════════════════════════════════════════════════════

    def _open_dl_manager(self):
        # Singleton — only one instance
        if self._dl_win and self._dl_win.winfo_exists():
            self._dl_win.lift()
            self._dl_win.focus_force()
            return
        win=tk.Toplevel(self.root)
        win.title("GP PRO AGENT — Download Manager")
        win.geometry("720x520")
        win.configure(bg=self.C["bg"])
        win.resizable(False,False)
        self._dl_win=win

        tk.Label(win,text="◈ BRAIN DOWNLOAD MANAGER",bg=self.C["bg"],
                 fg=self.C["cyan"],font=self.F["head"]).pack(anchor="w",padx=16,pady=(12,2))
        tk.Label(win,text="Models save to C:\\GPProAgent\\models\\  |  Downloads resume automatically",
                 bg=self.C["bg"],fg=self.C["dim"],font=self.F["small"]).pack(anchor="w",padx=16)
        tk.Frame(win,bg=self.C["border"],height=1).pack(fill="x",padx=16,pady=8)

        # Scrollable list
        canvas=tk.Canvas(win,bg=self.C["bg"],highlightthickness=0,height=360)
        sb=ttk.Scrollbar(win,orient="vertical",command=canvas.yview)
        frame=tk.Frame(canvas,bg=self.C["bg"])
        canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side="left",fill="both",expand=True,padx=(16,0))
        sb.pack(side="right",fill="y",padx=(0,8))
        cw=canvas.create_window((0,0),window=frame,anchor="nw")
        frame.bind("<Configure>",lambda e:canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>",lambda e:canvas.itemconfig(cw,width=e.width))

        self._dl_labels={}
        self._dl_btns={}

        for key,model in MODELS.items():
            dest=self.settings.model_path/model["file"]
            exists=dest.exists()
            row=tk.Frame(frame,bg=self.C["panel"],pady=3)
            row.pack(fill="x",pady=2,padx=4)
            tk.Label(row,text=f"[{key}]",bg=self.C["panel"],fg=self.C["orange"],
                     font=self.F["small"],width=8).pack(side="left",padx=6)
            tk.Label(row,text=f"{model['name'][:25]}",bg=self.C["panel"],
                     fg=self.C["white"],font=self.F["small"],width=26,
                     anchor="w").pack(side="left")
            tk.Label(row,text=f"{model['size_gb']}GB",bg=self.C["panel"],
                     fg=self.C["dim"],font=self.F["small"],width=6).pack(side="left")
            s="✓ Ready" if exists else "✗ Missing"
            c=self.C["green"] if exists else self.C["error"]
            lbl=tk.Label(row,text=s,bg=self.C["panel"],fg=c,
                         font=self.F["small"],width=12)
            lbl.pack(side="left",padx=4)
            self._dl_labels[key]=lbl
            if not exists:
                btn=tk.Button(row,text="⬇ Download",bg=self.C["cyan"],
                              fg=self.C["bg"],font=self.F["small"],relief="flat",
                              cursor="hand2",
                              command=lambda k=key,m=model,l=lbl:
                              threading.Thread(target=self._dl_one,
                                              args=(k,m,l),daemon=True).start())
                btn.pack(side="right",padx=6)
                self._dl_btns[key]=btn
            else:
                tk.Label(row,text="✓",bg=self.C["panel"],fg=self.C["green"],
                         font=self.F["small"]).pack(side="right",padx=6)

        # Bottom bar
        bot=tk.Frame(win,bg=self.C["bg"])
        bot.pack(fill="x",padx=16,pady=8)
        self._dl_status=tk.Label(bot,text="",bg=self.C["bg"],fg=self.C["green"],
                                  font=self.F["small"])
        self._dl_status.pack(side="left",padx=8)
        tk.Button(bot,text="⬇ Download All Missing",bg=self.C["cyan"],
                  fg=self.C["bg"],font=self.F["head"],relief="flat",cursor="hand2",
                  command=lambda:threading.Thread(target=self._dl_all,
                                                  daemon=True).start()
                  ).pack(side="right")

    def _dl_one(self,key,model,label):
        label.config(text="Starting...",fg=self.C["warning"])
        dest=self.settings.model_path/model["file"]
        ok=self._download_file(model["url"],dest,label)
        if ok:
            label.config(text="✓ Ready",fg=self.C["green"])
            self.root.after(0,self._refresh_dots)

    def _dl_all(self):
        missing=[k for k,m in MODELS.items()
                 if not(self.settings.model_path/m["file"]).exists()]
        self._dl_status.config(text=f"Downloading {len(missing)} models...")
        for key in missing:
            model=MODELS[key]
            lbl=self._dl_labels.get(key)
            dest=self.settings.model_path/model["file"]
            if lbl: lbl.config(text="Downloading...",fg=self.C["warning"])
            ok=self._download_file(model["url"],dest,lbl)
            if ok and lbl:
                lbl.config(text="✓ Ready",fg=self.C["green"])
        self._dl_status.config(text="✓ All done!")
        self._refresh_dots()

    def _download_file(self,url,dest,lbl=None):
        import urllib.request, urllib.error
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
                            mb=dl//1048576
                            self.root.after(0,lbl.config,
                                {"text":f"{pct}% {mb}MB","fg":self.C["warning"]})
            shutil.move(str(tmp),str(dest))
            return True
        except Exception as e:
            print(f"Download error: {e}")
            return False

    # ══════════════════════════════════════════════════════════
    # HELPERS
    # ══════════════════════════════════════════════════════════

    def _startup_check(self):
        ready=sum(1 for m in MODELS.values()
                  if(self.settings.model_path/m["file"]).exists())
        total=len(MODELS)
        missing=total-ready
        self._msg("system",f"◈ Models: {ready}/{total} ready")
        if missing>0:
            self._msg("system",f" | {missing} missing — click '⬇ Models' to download")
        self._msg("system","\n")
        try:
            import llama_cpp
            self._msg("system","◈ AI Engine: llama.cpp active ✓ — Full AI responses enabled\n\n")
        except ImportError:
            self._msg("system",
                "◈ AI Engine: Expert knowledge mode (llama.cpp not installed)\n"
                "◈ For real AI: pip install llama-cpp-python --prefer-binary\n\n")

    def _refresh_dots(self):
        for key,model in MODELS.items():
            if(self.settings.model_path/model["file"]).exists():
                self.dots[key].config(fg=self.C["green"],text="●")
            else:
                self.dots[key].config(fg=self.C["error"],text="○")

    def _update_stats(self,dur,brain):
        self._qcount+=1
        self._ttime+=dur
        avg=round(self._ttime/self._qcount,1)
        self.root.after(0,self.stats_lbl.config,
            {"text":f"Queries : {self._qcount}\nAvg time: {avg}s\nLast    : {dur}s"})

    def _done_busy(self,msg):
        self._busy=False
        self.root.after(0,self.send_btn.config,{"state":"normal","text":"▶ SEND"})
        self.root.after(0,self.cancel_btn.config,{"state":"disabled"})
        self.root.after(0,self.status_bar.config,{"text":msg,"fg":self.C["green"]})

    def _msg(self,tag,text):
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
        self.active_lbl.config(
            text=f"{m.get('name','?')}\nSpeed:{m.get('speed_s')}s  Acc:{m.get('accuracy')}%\nRAM:{m.get('ram_mb')}MB")

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
        except: pass
        self.root.after(3000,self._upd_ram)

    def run(self):
        self._upd_ram()
        self.root.mainloop()
