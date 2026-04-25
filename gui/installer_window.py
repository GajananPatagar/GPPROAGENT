import tkinter as tk
from tkinter import ttk
import threading, time, sys, os, json, shutil, urllib.request, subprocess
from pathlib import Path
BASE = Path(__file__).parent.parent
sys.path.insert(0, str(BASE))
from config.settings import Settings
from config.models import MODELS, TOTAL_GB

BG="#0a0f1a"; PANEL="#0d1526"; BORDER="#1a3a5c"; CYAN="#00e5ff"
GREEN="#00ff88"; ORANGE="#ff6b2b"; WHITE="#d0e8ff"; DIM="#3a5a7a"
ERROR="#ff4444"; WARNING="#ffaa00"; DARK="#050c18"

class InstallerWindow:
    def __init__(self):
        self.settings = Settings()
        self._setup()
        self._build()

    def _setup(self):
        self.root = tk.Tk()
        self.root.title("GP PRO AGENT — Installer")
        self.root.geometry("820x600")
        self.root.resizable(False, False)
        self.root.configure(bg=BG)
        self.root.update_idletasks()
        x=(self.root.winfo_screenwidth()-820)//2
        y=(self.root.winfo_screenheight()-600)//2
        self.root.geometry(f"820x600+{x}+{y}")
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._done = False

    def _build(self):
        left=tk.Frame(self.root,bg=DARK,width=280)
        left.pack(side="left",fill="y")
        left.pack_propagate(False)
        tk.Label(left,text="⬡",bg=DARK,fg=CYAN,font=("Consolas",48)).pack(pady=(50,10))
        tk.Label(left,text="GP PRO\nAGENT",bg=DARK,fg=WHITE,font=("Consolas",22,"bold"),justify="center").pack()
        tk.Label(left,text="v1.0.0",bg=DARK,fg=DIM,font=("Consolas",10)).pack(pady=(4,20))
        for f in ["✓ 11 AI Brain Models","✓ ~40GB Knowledge","✓ PLC Engineering","✓ GUI Automation","✓ Software Learning","✓ 600MB RAM Max","✓ 100% Offline","✓ Self-Modifying UI"]:
            tk.Label(left,text=f,bg=DARK,fg=GREEN,font=("Consolas",9),anchor="w").pack(fill="x",padx=24,pady=1)
        tk.Label(left,text="IHTM Department",bg=DARK,fg=DIM,font=("Consolas",8)).pack(side="bottom",pady=20)

        right=tk.Frame(self.root,bg=BG)
        right.pack(side="right",fill="both",expand=True)
        tk.Label(right,text="Installing GP PRO AGENT",bg=BG,fg=WHITE,font=("Consolas",16,"bold")).pack(anchor="w",padx=30,pady=(30,4))
        tk.Label(right,text="Downloading 11 AI brain models (~40GB)\nDownloads resume automatically if interrupted.",bg=BG,fg=DIM,font=("Consolas",9),justify="left").pack(anchor="w",padx=30)
        tk.Frame(right,bg=BORDER,height=1).pack(fill="x",padx=30,pady=12)

        self.model_lbl=tk.Label(right,text="Preparing...",bg=BG,fg=CYAN,font=("Consolas",10,"bold"),anchor="w")
        self.model_lbl.pack(fill="x",padx=30)
        self.model_pct=tk.Label(right,text="0%",bg=BG,fg=WHITE,font=("Consolas",9),anchor="w")
        self.model_pct.pack(fill="x",padx=30,pady=(2,4))

        bf=tk.Frame(right,bg=BORDER,height=14)
        bf.pack(fill="x",padx=30,pady=(0,12))
        bf.pack_propagate(False)
        self.model_bar=tk.Frame(bf,bg=CYAN,width=0)
        self.model_bar.pack(side="left",fill="y")

        tk.Label(right,text="Overall Progress",bg=BG,fg=DIM,font=("Consolas",9),anchor="w").pack(fill="x",padx=30)
        self.overall_pct=tk.Label(right,text="0 / 11 models",bg=BG,fg=WHITE,font=("Consolas",9),anchor="w")
        self.overall_pct.pack(fill="x",padx=30,pady=(2,4))
        of=tk.Frame(right,bg=BORDER,height=20)
        of.pack(fill="x",padx=30,pady=(0,12))
        of.pack_propagate(False)
        self.overall_bar=tk.Frame(of,bg=GREEN,width=0)
        self.overall_bar.pack(side="left",fill="y")

        tk.Label(right,text="Brain Models:",bg=BG,fg=DIM,font=("Consolas",9),anchor="w").pack(fill="x",padx=30,pady=(0,4))
        lf=tk.Frame(right,bg=PANEL)
        lf.pack(fill="x",padx=30)
        self.dots={}
        for key,model in MODELS.items():
            row=tk.Frame(lf,bg=PANEL,pady=1)
            row.pack(fill="x",padx=6)
            dot=tk.Label(row,text="○",bg=PANEL,fg=DIM,font=("Consolas",9))
            dot.pack(side="left")
            tk.Label(row,text=f"[{key:8s}]",bg=PANEL,fg=ORANGE,font=("Consolas",8),width=9,anchor="w").pack(side="left")
            tk.Label(row,text=f"{model['name'][:26]}",bg=PANEL,fg=WHITE,font=("Consolas",8),anchor="w").pack(side="left")
            tk.Label(row,text=f"{model['size_gb']}GB",bg=PANEL,fg=DIM,font=("Consolas",8)).pack(side="right",padx=6)
            self.dots[key]=dot

        self.status_lbl=tk.Label(right,text="Starting...",bg=BG,fg=DIM,font=("Consolas",8),anchor="w")
        self.status_lbl.pack(fill="x",padx=30,pady=(8,0))
        self.launch_btn=tk.Button(right,text="▶  LAUNCH GP PRO AGENT",bg=CYAN,fg=BG,font=("Consolas",12,"bold"),relief="flat",cursor="hand2",command=self._launch)
        threading.Thread(target=self._install,daemon=True).start()

    def _install(self):
        try:
            self.settings.ensure_dirs()
            self._lbl("Installing packages...")
            self._packages()
            self._knowledge()
            total=len(MODELS)
            for i,(key,model) in enumerate(MODELS.items()):
                self._overall(int(i/total*100),i,total)
                self._dot(key,WARNING,"⟳")
                self._lbl(f"Downloading: {model['name']}")
                dest=self.settings.model_path/model["file"]
                if dest.exists() and dest.stat().st_size/(1024**3)>model["size_gb"]*0.8:
                    self._dot(key,GREEN,"✓")
                    self._bar(100)
                    continue
                if self._download(model["url"],dest):
                    self._dot(key,GREEN,"✓")
                else:
                    self._dot(key,ERROR,"✗")
            self._build_router()
            self._overall(100,total,total)
            self._lbl("✓ Installation Complete!")
            self._bar(100)
            self._done=True
            self.root.after(0,self._show_launch)
        except Exception as e:
            self.root.after(0,self.status_lbl.config,{"text":f"Error: {e}","fg":ERROR})

    def _download(self,url,dest):
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
                        if total>0:
                            pct=int(dl/total*100)
                            self._bar(pct)
                            self.root.after(0,self.model_pct.config,{"text":f"{pct}% — {dl//1048576}MB/{total//1048576}MB"})
            shutil.move(str(tmp),str(dest))
            return True
        except Exception as e:
            self._lbl(f"Failed: {e}")
            return False

    def _packages(self):
        for pkg in ["llama-cpp-python","pyautogui","Pillow","psutil","onnxruntime"]:
            try:
                subprocess.run([sys.executable,"-m","pip","install",pkg,"--quiet"],capture_output=True,timeout=120)
            except: pass

    def _knowledge(self):
        data={"NO_contact":"Normally Open bit=1","NC_contact":"Normally Closed bit=0","timer_TON":"On-delay timer","timer_TOF":"Off-delay timer","estop":"NC hardwired emergency stop","interlock":"Prevents unsafe operations","Allen_Bradley":"Studio 5000 RSLogix","Siemens":"TIA Portal S7","Modbus_TCP":"Ethernet Modbus","Profinet":"Siemens industrial Ethernet"}
        p=self.settings.knowledge_path/"plc/ladder.json"
        p.parent.mkdir(parents=True,exist_ok=True)
        with open(p,"w") as f: json.dump(data,f,indent=2)

    def _build_router(self):
        router={"version":"1.0.0","installed":time.strftime("%Y-%m-%d %H:%M:%S"),"models":{},"routing":{}}
        for key,model in MODELS.items():
            dest=self.settings.model_path/model["file"]
            router["models"][key]={"name":model["name"],"file":str(dest),"role":model["role"],"ram_mb":model["ram_mb"],"speed_s":model["speed_s"],"accuracy":model["accuracy"],"ready":dest.exists()}
            for t in model.get("triggers",[]): router["routing"][t]=key
        with open(self.settings.brain_root/"model_router.json","w") as f: json.dump(router,f,indent=2)

    def _lbl(self,t):
        self.root.after(0,self.model_lbl.config,{"text":t})
        self.root.after(0,self.status_lbl.config,{"text":t[:80]})

    def _bar(self,pct):
        def _d():
            self.model_bar.config(width=max(int(460*pct/100),0))
        self.root.after(0,_d)

    def _overall(self,pct,done,total):
        def _d():
            self.overall_bar.config(width=max(int(460*pct/100),0))
            self.overall_pct.config(text=f"{done}/{total} models ({pct}%)")
        self.root.after(0,_d)

    def _dot(self,key,color,sym):
        def _d():
            if key in self.dots: self.dots[key].config(text=sym,fg=color)
        self.root.after(0,_d)

    def _show_launch(self):
        self.launch_btn.pack(fill="x",padx=30,pady=12,ipady=8)
        self.status_lbl.config(text="✓ Done! Click to launch.",fg=GREEN)

    def _launch(self):
        self.root.destroy()
        from gui.main_window import MainWindow
        MainWindow().run()

    def _on_close(self):
        import tkinter.messagebox as mb
        if self._done or mb.askyesno("Quit?","Downloads will resume next time. Quit?"):
            self.root.destroy()

    def run(self):
        self.root.mainloop()
