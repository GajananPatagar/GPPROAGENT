import tkinter as tk
from tkinter import ttk, scrolledtext
import threading, time, sys, os, gc
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core.agent import GPProAgent
from config.models import MODELS

C = {
    "bg":"#0a0f1a","panel":"#0d1526","border":"#1a3a5c",
    "cyan":"#00e5ff","green":"#00ff88","orange":"#ff6b2b",
    "purple":"#bf5fff","white":"#d0e8ff","dim":"#3a5a7a",
    "input_bg":"#071020","button":"#0a2a4a","error":"#ff4444",
    "warning":"#ffaa00",
}
F = {
    "title":  ("Consolas",16,"bold"),
    "head":   ("Consolas",11,"bold"),
    "body":   ("Consolas",10),
    "small":  ("Consolas",9),
    "input":  ("Consolas",11),
}

class GPProWindow:
    def __init__(self):
        self.agent    = GPProAgent()
        self.priority = tk.StringVar(value="balanced")
        self._busy    = False
        self._qcount  = 0
        self._ttime   = 0.0
        self._setup()
        self._build()

    def _setup(self):
        self.root = tk.Tk()
        self.root.title("GP PRO AGENT — Professional AI System v1.0.0")
        self.root.geometry("1280x820")
        self.root.minsize(960,640)
        self.root.configure(bg=C["bg"])
        self.root.grid_rowconfigure(0,weight=1)
        self.root.grid_columnconfigure(0,weight=1)

    def _build(self):
        m = tk.Frame(self.root,bg=C["bg"])
        m.grid(row=0,column=0,sticky="nsew",padx=8,pady=8)
        m.grid_rowconfigure(1,weight=1)
        m.grid_columnconfigure(0,weight=3)
        m.grid_columnconfigure(1,weight=1)
        self._header(m)
        self._chat_panel(m)
        self._status_panel(m)
        self._input_panel(m)

    def _header(self,p):
        h = tk.Frame(p,bg=C["panel"],highlightbackground=C["border"],highlightthickness=1)
        h.grid(row=0,column=0,columnspan=2,sticky="ew",pady=(0,4))
        h.grid_columnconfigure(1,weight=1)
        tk.Label(h,text="⬡ GP PRO AGENT",bg=C["panel"],fg=C["cyan"],font=F["title"]).grid(row=0,column=0,padx=16,pady=10)
        tk.Label(h,text="Multi-Brain AI | PLC + GUI + Software Learning | 100% Offline",bg=C["panel"],fg=C["dim"],font=F["small"]).grid(row=0,column=1,padx=8,sticky="w")
        self.ram_lbl = tk.Label(h,text="RAM: -- MB",bg=C["panel"],fg=C["green"],font=F["small"])
        self.ram_lbl.grid(row=0,column=2,padx=8)
        pf = tk.Frame(h,bg=C["panel"])
        pf.grid(row=0,column=3,padx=16)
        tk.Label(pf,text="Priority:",bg=C["panel"],fg=C["dim"],font=F["small"]).pack(side="left")
        for v,l in [("speed","⚡Speed"),("balanced","⚖Balance"),("accuracy","🎯Accuracy")]:
            tk.Radiobutton(pf,text=l,variable=self.priority,value=v,bg=C["panel"],fg=C["white"],selectcolor=C["button"],activebackground=C["panel"],font=F["small"]).pack(side="left",padx=3)

    def _chat_panel(self,p):
        f = tk.Frame(p,bg=C["panel"],highlightbackground=C["border"],highlightthickness=1)
        f.grid(row=1,column=0,sticky="nsew",padx=(0,4),pady=4)
        f.grid_rowconfigure(1,weight=1)
        f.grid_columnconfigure(0,weight=1)
        tk.Label(f,text="◈ CONVERSATION",bg=C["panel"],fg=C["cyan"],font=F["head"]).grid(row=0,column=0,sticky="w",padx=12,pady=6)
        self.chat = scrolledtext.ScrolledText(f,bg=C["input_bg"],fg=C["white"],font=F["body"],wrap=tk.WORD,state="disabled",borderwidth=0,highlightthickness=0,padx=12,pady=8)
        self.chat.grid(row=1,column=0,sticky="nsew",padx=8,pady=(0,8))
        self.chat.tag_config("user",   foreground=C["cyan"])
        self.chat.tag_config("agent",  foreground=C["green"])
        self.chat.tag_config("model",  foreground=C["orange"])
        self.chat.tag_config("system", foreground=C["dim"])
        self.chat.tag_config("error",  foreground=C["error"])
        self._chat_add("system","GP PRO AGENT v1.0.0 — 11 Specialist AI Brains Ready\nPLC Engineering | GUI Automation | Software Learning | 100% Offline\nType your query and press Enter or click SEND.\n")

    def _status_panel(self,p):
        f = tk.Frame(p,bg=C["panel"],highlightbackground=C["border"],highlightthickness=1)
        f.grid(row=1,column=1,sticky="nsew",padx=(4,0),pady=4)
        f.grid_columnconfigure(0,weight=1)
        tk.Label(f,text="◈ BRAIN STATUS",bg=C["panel"],fg=C["cyan"],font=F["head"]).grid(row=0,column=0,sticky="w",padx=12,pady=6)
        canvas = tk.Canvas(f,bg=C["panel"],highlightthickness=0)
        sb = ttk.Scrollbar(f,orient="vertical",command=canvas.yview)
        self.mf = tk.Frame(canvas,bg=C["panel"])
        canvas.configure(yscrollcommand=sb.set)
        canvas.grid(row=1,column=0,sticky="nsew",padx=4)
        sb.grid(row=1,column=1,sticky="ns")
        f.grid_rowconfigure(1,weight=1)
        cw = canvas.create_window((0,0),window=self.mf,anchor="nw")
        self.mf.bind("<Configure>",lambda e:canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>",lambda e:canvas.itemconfig(cw,width=e.width))
        self.dots = {}
        for key,model in MODELS.items():
            fr = tk.Frame(self.mf,bg=C["panel"],padx=6,pady=2)
            fr.pack(fill="x",padx=4,pady=1)
            dot = tk.Label(fr,text="●",bg=C["panel"],fg=C["dim"],font=F["small"])
            dot.pack(side="left")
            tk.Label(fr,text=f"[{key}]",bg=C["panel"],fg=C["orange"],font=F["small"],width=8,anchor="w").pack(side="left")
            tk.Label(fr,text=f"{model['speed_s']}s|{model['accuracy']}%",bg=C["panel"],fg=C["dim"],font=F["small"]).pack(side="right")
            self.dots[key] = dot
        tk.Label(f,text="◈ ACTIVE MODEL",bg=C["panel"],fg=C["cyan"],font=F["head"]).grid(row=2,column=0,columnspan=2,sticky="w",padx=12,pady=(8,2))
        self.active_lbl = tk.Label(f,text="None",bg=C["panel"],fg=C["orange"],font=F["small"],wraplength=200,justify="left")
        self.active_lbl.grid(row=3,column=0,columnspan=2,sticky="w",padx=12)
        tk.Label(f,text="◈ SESSION",bg=C["panel"],fg=C["cyan"],font=F["head"]).grid(row=4,column=0,columnspan=2,sticky="w",padx=12,pady=(8,2))
        self.stats_lbl = tk.Label(f,text="Queries: 0\nAvg: --\nLast: --",bg=C["panel"],fg=C["white"],font=F["small"],justify="left")
        self.stats_lbl.grid(row=5,column=0,columnspan=2,sticky="w",padx=12,pady=(0,8))

    def _input_panel(self,p):
        f = tk.Frame(p,bg=C["panel"],highlightbackground=C["border"],highlightthickness=1)
        f.grid(row=2,column=0,columnspan=2,sticky="ew",pady=(4,0))
        f.grid_columnconfigure(0,weight=1)
        inf = tk.Frame(f,bg=C["panel"])
        inf.grid(row=0,column=0,columnspan=2,sticky="ew",padx=8,pady=8)
        inf.grid_columnconfigure(0,weight=1)
        self.inp = tk.Text(inf,bg=C["input_bg"],fg=C["white"],font=F["input"],height=3,wrap=tk.WORD,insertbackground=C["cyan"],borderwidth=0,highlightthickness=1,highlightcolor=C["cyan"],highlightbackground=C["border"],padx=8,pady=6)
        self.inp.grid(row=0,column=0,sticky="ew",padx=(0,8))
        self.inp.bind("<Return>",self._enter)
        bf = tk.Frame(inf,bg=C["panel"])
        bf.grid(row=0,column=1)
        self.send_btn = tk.Button(bf,text="▶ SEND",bg=C["cyan"],fg=C["bg"],font=F["head"],width=10,relief="flat",cursor="hand2",command=self._send)
        self.send_btn.pack(pady=(0,4))
        tk.Button(bf,text="⊘ CLEAR",bg=C["button"],fg=C["white"],font=F["small"],width=10,relief="flat",cursor="hand2",command=self._clear).pack()
        self.status_bar = tk.Label(f,text="Ready — Enter your query",bg=C["panel"],fg=C["dim"],font=F["small"],anchor="w")
        self.status_bar.grid(row=1,column=0,columnspan=2,sticky="ew",padx=12,pady=(0,6))

    def _enter(self,e):
        if not e.state & 0x1:
            self._send()
            return "break"

    def _send(self):
        if self._busy: return
        q = self.inp.get("1.0","end-1c").strip()
        if not q: return
        self.inp.delete("1.0","end")
        self._busy = True
        self.send_btn.config(state="disabled",text="⏳...")
        self.status_bar.config(text="Thinking...",fg=C["warning"])
        threading.Thread(target=self._process,args=(q,),daemon=True).start()

    def _process(self,q):
        self._chat_add("user",f"You: {q}\n")
        self._all_dots(C["dim"])
        try:
            r = self.agent.query(q,self.priority.get())
            self.root.after(0,self._upd_model,r.model_used)
            self.root.after(0,self._set_dot,r.model_used,C["green"])
            self._chat_add("model",f"[{r.model_used.upper()} | {r.duration_s}s | {r.confidence*100:.0f}%]\n")
            self._chat_add("agent",f"{r.answer}\n\n")
            self._qcount += 1
            self._ttime  += r.duration_s
            avg = self._ttime / self._qcount
            self.root.after(0,self.stats_lbl.config,{"text":f"Queries: {self._qcount}\nAvg: {avg:.1f}s\nLast: {r.duration_s}s"})
            self.root.after(0,self.status_bar.config,{"text":f"Done {r.duration_s}s | {r.model_used}","fg":C["green"]})
        except Exception as e:
            self._chat_add("error",f"Error: {e}\n\n")
            self.root.after(0,self.status_bar.config,{"text":f"Error: {e}","fg":C["error"]})
        finally:
            self._busy = False
            self.root.after(0,self.send_btn.config,{"state":"normal","text":"▶ SEND"})
            self.root.after(2000,self._all_dots,C["dim"])

    def _chat_add(self,tag,text):
        def _do():
            self.chat.config(state="normal")
            self.chat.insert("end",text,tag)
            self.chat.see("end")
            self.chat.config(state="disabled")
        self.root.after(0,_do)

    def _upd_model(self,key):
        m = MODELS.get(key,{})
        self.active_lbl.config(text=f"{m.get('name','?')}\nSpeed:{m.get('speed_s')}s Acc:{m.get('accuracy')}%\nRAM:{m.get('ram_mb')}MB")

    def _set_dot(self,key,color):
        if key in self.dots: self.dots[key].config(fg=color)

    def _all_dots(self,color):
        for d in self.dots.values(): d.config(fg=color)

    def _clear(self):
        self.chat.config(state="normal")
        self.chat.delete("1.0","end")
        self.chat.config(state="disabled")
        self._chat_add("system","Chat cleared.\n")

    def _upd_ram(self):
        try:
            import psutil, os
            mb = psutil.Process(os.getpid()).memory_info().rss/(1024*1024)
            c  = C["green"] if mb<500 else C["warning"]
            self.ram_lbl.config(text=f"RAM:{mb:.0f}MB",fg=c)
        except: pass
        self.root.after(3000,self._upd_ram)

    def run(self):
        self._upd_ram()
        self.root.mainloop()
