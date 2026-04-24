#!/usr/bin/env python3
import os,sys,json,time,shutil,platform,subprocess,urllib.request,urllib.error
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent.parent))
from config.settings import Settings,BRAIN_ROOT
from config.models import MODELS,TOTAL_GB

BANNER="""
╔══════════════════════════════════════════════════════════╗
║      GP PRO AGENT — Brain Installer v1.0.0             ║
║      Downloading 40GB Professional AI Brain            ║
║      11 Specialist Models — Auto Install               ║
╚══════════════════════════════════════════════════════════╝
"""

KNOWLEDGE={
    "plc/ladder.json":{
        "elements":{"NO_contact":"Normally Open bit=1","NC_contact":"Normally Closed bit=0","output_coil":"Sets bit when rung true","timer_TON":"On-delay timer","timer_TOF":"Off-delay timer","timer_RTO":"Retentive timer","counter_CTU":"Count up","counter_CTD":"Count down","compare_EQU":"Equal A=B","compare_GRT":"Greater A>B","compare_LES":"Less A<B","math_ADD":"Addition","math_SUB":"Subtraction","math_MUL":"Multiplication","math_DIV":"Division","jump_JSR":"Jump subroutine","jump_RET":"Return subroutine"},
        "safety":{"estop":"NC hardwired in series","interlock":"Prevents unsafe ops","safety_relay":"Monitors circuit","watchdog":"Fault on missed scan","SIL1":"Low risk","SIL2":"Medium risk","SIL3":"High risk","LOTO":"Lockout Tagout"},
        "controllers":{"Allen_Bradley":"Studio 5000 RSLogix","Siemens":"TIA Portal S7","Schneider":"Unity Pro Modicon","Mitsubishi":"GX Works MELSEC","Omron":"Sysmac NX NJ","Beckhoff":"TwinCAT PC-based"},
        "networking":{"Modbus_RTU":"Serial RS-485","Modbus_TCP":"Ethernet Modbus","Profibus":"Siemens field bus","Profinet":"Siemens Ethernet","EtherNet_IP":"Rockwell Ethernet","OPC_UA":"Universal standard"},
        "troubleshoot":{"IO_fault":"Check wiring fuse power","comm_fault":"Check cables termination","watchdog_fault":"Scan too long optimize","battery_low":"Replace battery urgent"}
    },
    "gui/automation.json":{
        "pyautogui":{"click":"pyautogui.click(x,y)","double_click":"pyautogui.doubleClick(x,y)","right_click":"pyautogui.rightClick(x,y)","type_text":"pyautogui.typewrite('text')","key_press":"pyautogui.press('enter')","hotkey":"pyautogui.hotkey('ctrl','c')","screenshot":"pyautogui.screenshot()","locate":"pyautogui.locateOnScreen('img.png')"},
        "shortcuts":{"copy":"Ctrl+C","paste":"Ctrl+V","undo":"Ctrl+Z","save":"Ctrl+S","select_all":"Ctrl+A","find":"Ctrl+F","task_manager":"Ctrl+Shift+Esc","run":"Win+R","explorer":"Win+E"}
    },
    "software/studio5000.json":{
        "operations":{"new_project":"File→New→Controller Type→Select PLC","add_rung":"Right-click ladder→Insert Rung","add_contact":"Right-click rung→Add Element→Examine if Closed","add_coil":"Right-click rung→Add Element→Output Energize","go_online":"Communications→Who Active→Download","force_io":"Controller Tags→Force I/O","monitor":"Controller Tags→Monitor Tags"}
    },
    "software/tia_portal.json":{
        "operations":{"new_project":"Create new→Select PLC→Configure IP","add_network":"LAD editor→New Network","compile":"Project→Compile→Hardware Software","download":"Online→Download to device","go_online":"Online→Go online","monitor":"Online tools→Monitor Modify"}
    },
    "engineering/standards.json":{
        "IEC_61131":{"LD":"Ladder Diagram","FBD":"Function Block Diagram","ST":"Structured Text","IL":"Instruction List","SFC":"Sequential Function Chart"},
        "safety":{"IEC_61508":"Functional safety E/E/PE","IEC_61511":"Process safety","ISO_13849":"Machine safety","IEC_62061":"Functional safety machines"},
        "instrumentation":{"4_20mA":"4mA=0% 20mA=100%","RTD":"PT100 PT1000 temperature","thermocouple":"Type J K T E","pressure_tx":"Process pressure","flow_meter":"Process flow","level_sensor":"Tank level"}
    },
}

class BrainInstaller:
    def __init__(self):
        self.settings = Settings()
        self.done=[]
        self.skipped=[]
        self.errors=[]

    def run(self):
        print(BANNER)
        print(f"  System  : {platform.system()} {platform.machine()}")
        print(f"  Path    : {self.settings.brain_root}")
        print(f"  Models  : {len(MODELS)}")
        print(f"  Size    : ~{TOTAL_GB:.1f}GB")
        print(f"  RAM max : 600MB\n")
        steps=[
            ("Creating directories",     self._dirs),
            ("Installing packages",      self._packages),
            ("Installing knowledge",     self._knowledge),
            ("Downloading AI models",    self._models),
            ("Building router",          self._router),
            ("Creating launchers",       self._launchers),
            ("Verifying",                self._verify),
        ]
        for i,(label,fn) in enumerate(steps,1):
            print(f"[{i}/{len(steps)}] {label}...")
            try:
                fn()
                print(f"  ✓ Done\n")
            except Exception as e:
                print(f"  ⚠ {e}\n")
                self.errors.append(str(e))
        self._summary()

    def _dirs(self):
        for d in [self.settings.model_path,
                  self.settings.knowledge_path/"plc",
                  self.settings.knowledge_path/"gui",
                  self.settings.knowledge_path/"software",
                  self.settings.knowledge_path/"engineering",
                  self.settings.cache_path,
                  self.settings.log_path]:
            d.mkdir(parents=True,exist_ok=True)
            print(f"  ✓ {d}")

    def _packages(self):
        pkgs=["llama-cpp-python","pyautogui","Pillow","psutil","onnxruntime"]
        for pkg in pkgs:
            print(f"  {pkg}...",end=" ",flush=True)
            try:
                r=subprocess.run([sys.executable,"-m","pip","install",pkg,"--quiet"],capture_output=True,timeout=120)
                print("✓" if r.returncode==0 else "⚠")
            except Exception as e:
                print(f"⚠ {e}")

    def _knowledge(self):
        for fname,data in KNOWLEDGE.items():
            p=self.settings.knowledge_path/fname
            p.parent.mkdir(parents=True,exist_ok=True)
            with open(p,"w",encoding="utf-8") as f:
                json.dump(data,f,indent=2)
            print(f"  ✓ {fname} ({p.stat().st_size/1024:.1f}KB)")

    def _models(self):
        total=len(MODELS)
        for i,(key,model) in enumerate(MODELS.items(),1):
            dest=self.settings.model_path/model["file"]
            print(f"\n  [{i}/{total}] {model['name']}")
            print(f"         {model['size_gb']}GB | {model['ram_mb']}MB RAM | {model['speed_s']}s | {model['accuracy']}%")
            if dest.exists():
                gb=dest.stat().st_size/(1024**3)
                if gb>model["size_gb"]*0.8:
                    print(f"         Already installed ({gb:.2f}GB) ✓")
                    self.skipped.append(key)
                    continue
                dest.unlink()
            if self._download(model["url"],dest):
                self.done.append(key)
            else:
                self.errors.append(f"{key} failed")

    def _download(self,url,dest):
        tmp=Path(str(dest)+".part")
        headers={"User-Agent":"GP-PRO-AGENT/1.0"}
        resume=tmp.stat().st_size if tmp.exists() else 0
        if resume>0:
            headers["Range"]=f"bytes={resume}-"
            print(f"         Resuming from {resume/(1024**2):.1f}MB...")
        try:
            req=urllib.request.Request(url,headers=headers)
            with urllib.request.urlopen(req,timeout=30) as resp:
                total=int(resp.headers.get("Content-Length",0))+resume
                mode="ab" if resume>0 else "wb"
                downloaded=resume
                with open(tmp,mode) as f:
                    while True:
                        chunk=resp.read(1024*1024)
                        if not chunk: break
                        f.write(chunk)
                        downloaded+=len(chunk)
                        if total>0:
                            pct=downloaded/total*100
                            bar="█"*int(pct/2)+"░"*(50-int(pct/2))
                            print(f"\r         [{bar}] {pct:.1f}% {downloaded/(1024**2):.0f}/{total/(1024**2):.0f}MB",end="",flush=True)
            print()
            shutil.move(str(tmp),str(dest))
            print(f"         ✓ {dest.stat().st_size/(1024**3):.2f}GB")
            return True
        except Exception as e:
            print(f"\n         ✗ {e}")
            return False

    def _router(self):
        router={"version":"1.0.0","brain_path":str(self.settings.brain_root),"models":{},"routing":{}}
        for key,model in MODELS.items():
            dest=self.settings.model_path/model["file"]
            router["models"][key]={"name":model["name"],"file":str(dest),"role":model["role"],"ram_mb":model["ram_mb"],"speed_s":model["speed_s"],"accuracy":model["accuracy"],"ready":dest.exists(),"size_gb":model["size_gb"]}
            for t in model.get("triggers",[]):
                router["routing"][t]=key
        path=self.settings.brain_root/"model_router.json"
        with open(path,"w") as f:
            json.dump(router,f,indent=2)
        print(f"  ✓ Router: {path}")

    def _launchers(self):
        if platform.system()=="Windows":
            bat=Path("GP_PRO_AGENT.bat")
            bat.write_text("@echo off\ntitle GP PRO AGENT\ncd /d %~dp0\npython main.py --mode gui\npause\n")
            try:
                desk=Path.home()/"Desktop"/"GP PRO AGENT.bat"
                shutil.copy(bat,desk)
                print(f"  ✓ Desktop shortcut created")
            except: pass
        else:
            sh=Path("gp_pro_agent.sh")
            sh.write_text("#!/bin/bash\ncd \"$(dirname \"$0\")\"\npython3 main.py --mode gui\n")
            sh.chmod(0o755)

    def _verify(self):
        ready=sum(1 for m in MODELS.values() if (self.settings.model_path/m["file"]).exists())
        print(f"  Models ready: {ready}/{len(MODELS)}")
        for key,model in MODELS.items():
            p=self.settings.model_path/model["file"]
            s="✓" if p.exists() else "✗"
            gb=p.stat().st_size/(1024**3) if p.exists() else 0
            print(f"  {s} [{key:8s}] {model['name'][:30]} {gb:.1f}GB")

    def _summary(self):
        gb=sum((self.settings.model_path/MODELS[k]["file"]).stat().st_size for k in self.done+self.skipped if (self.settings.model_path/MODELS[k]["file"]).exists())/(1024**3)
        print()
        print("═"*56)
        print("  GP PRO AGENT — INSTALLATION COMPLETE")
        print("═"*56)
        print(f"  Installed : {len(self.done)} models")
        print(f"  Skipped   : {len(self.skipped)} already existed")
        print(f"  Total GB  : {gb:.1f}GB on {self.settings.brain_root}")
        print(f"  Max RAM   : 600MB")
        print(f"  Errors    : {len(self.errors)}")
        print("═"*56)
        print("  LAUNCH: Double-click GP_PRO_AGENT.bat")
        print("  OR RUN: python main.py --mode gui")
        print("═"*56)

if __name__=="__main__":
    BrainInstaller().run()
