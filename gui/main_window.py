import tkinter as tk
from tkinter import ttk, scrolledtext
import threading, time, sys, os, json, gc
from pathlib import Path
BASE = Path(__file__).parent.parent
sys.path.insert(0, str(BASE))
from config.settings import Settings
from config.models import MODELS

class MainWindow:
    def __init__(self):
        self.settings = Settings()
        self.settings.ensure_dirs()
        self._busy = False
        self._qcount = 0
        self._ttime = 0.0
        self._llm = None
        self._llm_key = None
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
        self.ram_lbl=tk.Label(h,text="RAM: --MB",bg=self.C["panel"],fg=self.C["green"],font=self.F["small"])
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
        self._chat("system","◈ GP PRO AGENT v1.0.0 — Online\n◈ 11 Specialist AI Brains | PLC | GUI | Software Learning\n◈ 100% Offline | Self-Modifying UI\n◈ Type your query and press Enter.\n◈ Say 'change theme to blue' to modify UI.\n\n")

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
        # Check which models are ready
        for key,model in MODELS.items():
            p2=self.settings.model_path/model["file"]
            if p2.exists():
                self.dots[key].config(fg=self.C["green"],text="●")
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
        for i,(lbl,cmd) in enumerate([("PLC Basics","Explain PLC ladder logic basics"),("Safety Check","What are the main safety protocols?"),("GUI Help","How do I automate GUI clicks?"),("Code Help","How do I write a Python script?")]):
            tk.Button(f,text=lbl,bg=self.C["button"],fg=self.C["white"],font=self.F["small"],relief="flat",cursor="hand2",command=lambda c=cmd:self._quick(c)).grid(row=10+i,column=0,sticky="ew",padx=12,pady=2)

    def _input_panel(self,p):
        f=tk.Frame(p,bg=self.C["panel"],highlightbackground=self.C["border"],highlightthickness=1)
        f.grid(row=2,column=0,columnspan=2,sticky="ew",pady=(4,0))
        f.grid_columnconfigure(0,weight=1)
        tk.Label(f,text="Ask anything: PLC logic, GUI automation, calculations, software help...",bg=self.C["panel"],fg=self.C["dim"],font=self.F["small"],anchor="w").grid(row=0,column=0,columnspan=2,sticky="ew",padx=12,pady=(8,2))
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
            self._chat("model",f"[{key.upper()} | {dur}s | {model['accuracy']}% accuracy]\n")
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
            score+=(matched/max(len(triggers),1))*50
            score+=(model["accuracy"]/100)*30
            score+=(1/max(model["speed_s"],0.1))*20
            if pri=="speed": score+=(1/max(model["speed_s"],0.1))*30
            elif pri=="accuracy": score+=(model["accuracy"]/100)*30
            dest=self.settings.model_path/model["file"]
            if not dest.exists(): score*=0.1
            scores[key]=score
        return max(scores,key=scores.get)

    def _ask(self,key,query):
        model=MODELS[key]
        dest=self.settings.model_path/model["file"]
        if not dest.exists(): return self._fallback(query)
        try:
            from llama_cpp import Llama
            if self._llm_key!=key:
                if self._llm:
                    del self._llm
                    gc.collect()
                self._llm=Llama(model_path=str(dest),n_ctx=self.settings.context_size,n_threads=self.settings.cpu_threads,n_gpu_layers=0,verbose=False,use_mmap=True)
                self._llm_key=key
            prompts={"master":"You are GP PRO AGENT Senior Engineering AI. Professional precise answers.","reflex":"You are GP PRO AGENT. Direct answers max 3 sentences.","plc":"You are GP PRO AGENT PLC Expert — ladder logic Allen Bradley Siemens SCADA specialist.","coder":"You are GP PRO AGENT Code Expert — write clean efficient code.","screen":"You are GP PRO AGENT GUI Expert — precise screen automation steps.","safety":"You are GP PRO AGENT Safety Engineer — prioritize safety above all.","memory":"You are GP PRO AGENT Memory — recall information accurately.","docs":"You are GP PRO AGENT Documentation Expert — professional technical writing.","learner":"You are GP PRO AGENT Software Expert — teach step by step clearly.","ocr":"You are GP PRO AGENT Vision Expert — extract text accurately.","math":"You are GP PRO AGENT Calculator — precise engineering math."}
            sys_p=prompts.get(key,prompts["master"])
            prompt=f"<|system|>{sys_p}<|end|>\n<|user|>{query}<|end|>\n<|assistant|>"
            resp=self._llm(prompt,max_tokens=self.settings.max_tokens,temperature=self.settings.temperature,stop=["<|end|>","<|user|>"],echo=False)
            return resp["choices"][0]["text"].strip()
        except ImportError:
            return self._fallback(query)
        except Exception as e:
            return self._fallback(query)

    def _fallback(self,query):
        q=query.lower()
        if any(w in q for w in ["ladder","plc","rung","coil"]):
            return "PLC Ladder Logic:\n• NO Contact: passes when bit=1\n• NC Contact: passes when bit=0\n• Output Coil: sets bit when rung true\n• Timer TON: On-delay | TOF: Off-delay\n• Counter CTU: Up | CTD: Down\n• Check I/O mapping and scan cycle."
        if any(w in q for w in ["safety","estop","emergency"]):
            return "Safety Protocol:\n1. E-stop must be NC hardwired in series\n2. Verify safety relay status\n3. Check all interlocks\n4. Follow LOTO before maintenance\n5. SIL rating must match risk assessment"
        if any(w in q for w in ["python","code","script"]):
            return "Python Best Practice:\n• Modular design\n• Handle exceptions with try/except\n• Use type hints\n• Write docstrings\n• Follow PEP8"
        if any(w in q for w in ["click","screen","gui"]):
            return "GUI Automation:\n1. Identify target element\n2. Get pixel coordinates\n3. Verify element visible\n4. pyautogui.click(x, y)\n5. Verify result"
        return f"GP PRO AGENT ready. Ask me about PLC, safety, coding, GUI automation, or any engineering topic."

    def _is_ui_cmd(self,query):
        q=query.lower()
        return any(k in q for k in ["change theme","make font","change color","change accent","modify ui","change ui","make it bigger","make it smaller"])

    def _handle_ui(self,query):
        q=query.lower()
        changes=[]
        colors={"blue":"#0066ff","red":"#ff3333","green":"#00ff88","purple":"#bf5fff","orange":"#ff6b2b","yellow":"#ffdd00","pink":"#ff66cc","cyan":"#00e5ff","teal":"#00ccaa"}
        if "color" in q or "theme" in q or "accent" in q:
            for name,hex_v in colors.items():
                if name in q:
                    self.C["cyan"]=hex_v
                    self.settings.ui["accent_color"]=hex_v
                    self.send_btn.config(bg=hex_v)
                    self.chat.tag_config("user",foreground=hex_v)
                    changes.append(f"Accent color → {name} ({hex_v})")
                    break
        if "font" in q:
            if any(w in q for w in ["bigger","larger","increase"]):
                s=min(self.F["body"][1]+1,16)
                self.F["body"]=("Consolas",s)
                self.settings.ui["font_size"]=s
                self.chat.config(font=self.F["body"])
                changes.append(f"Font size → {s}")
            elif any(w in q for w in ["smaller","decrease"]):
                s=max(self.F["body"][1]-1,8)
                self.F["body"]=("Consolas",s)
                self.settings.ui["font_size"]=s
                self.chat.config(font=self.F["body"])
                changes.append(f"Font size → {s}")
        if changes:
            self.settings.save_ui()
            self._chat("ui_msg","◈ UI Updated:\n"+"".join(f"  • {c}\n" for c in changes)+"\n")
        else:
            self._chat("ui_msg","◈ Try: 'change theme to blue' or 'make font bigger'\n\n")
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
