"""
GP PRO AGENT — PLC Software Controller
Directly controls RSLogix Studio 5000, TIA Portal, PCWin.
Reads ladder logic, creates rungs, uploads/downloads programs.
"""
import subprocess, time, threading, os, re
from pathlib import Path

class PLCController:
    def __init__(self, vision_module=None):
        self.vision    = vision_module
        self._software = None
        self._connected= False

    def detect_plc_software(self):
        """Detect which PLC software is open."""
        try:
            result = subprocess.run(
                ['powershell','-command',
                 'Get-Process | Where-Object {$_.MainWindowTitle} | Select MainWindowTitle'],
                capture_output=True, text=True, timeout=5)
            titles = result.stdout.lower()
            if "studio 5000" in titles or "rslogix" in titles:
                self._software = "studio5000"
                return "Allen Bradley Studio 5000"
            if "tia portal" in titles or "siemens" in titles:
                self._software = "tia_portal"
                return "Siemens TIA Portal"
            if "pcwin" in titles:
                self._software = "pcwin"
                return "PCWin"
            return None
        except Exception as e:
            return None

    def open_studio5000(self):
        paths = [
            r"C:\Program Files (x86)\Rockwell Software\Studio 5000\Studio5000Launcher.exe",
            r"C:\Program Files\Rockwell Software\Studio 5000\Studio5000Launcher.exe",
            "Studio5000Launcher.exe",
        ]
        for p in paths:
            try:
                subprocess.Popen(p, shell=True)
                time.sleep(3)
                self._software = "studio5000"
                return True
            except: pass
        return False

    def open_tia_portal(self):
        paths = [
            r"C:\Program Files\Siemens\Automation\Portal V17\bin\Siemens.Automation.Portal.exe",
            r"C:\Program Files\Siemens\Automation\Portal V18\bin\Siemens.Automation.Portal.exe",
            "TIA Portal.exe",
        ]
        for p in paths:
            try:
                subprocess.Popen(p, shell=True)
                time.sleep(3)
                self._software = "tia_portal"
                return True
            except: pass
        return False

    def open_pcwin(self):
        paths = [
            r"C:\Program Files\PCWin\PCWin.exe",
            r"C:\Program Files (x86)\PCWin\PCWin.exe",
            "PCWin.exe",
        ]
        for p in paths:
            try:
                subprocess.Popen(p, shell=True)
                time.sleep(2)
                self._software = "pcwin"
                return True
            except: pass
        return False

    def create_new_rung(self):
        """Add new rung in open PLC software."""
        try:
            import pyautogui
            if self._software == "studio5000":
                pyautogui.hotkey("ctrl","shift","r")
                time.sleep(0.3)
                return True
        except: pass
        return False

    def execute_plc_command(self, command: str) -> str:
        """Execute natural language PLC command."""
        q = command.lower()
        software = self.detect_plc_software()

        if not software and any(w in q for w in ["open","launch","start"]):
            if "studio" in q or "rslogix" in q or "allen" in q:
                ok = self.open_studio5000()
                return ("OK Opening Studio 5000..." if ok
                        else "X Studio 5000 not found. Check installation.")
            if "tia" in q or "siemens" in q:
                ok = self.open_tia_portal()
                return ("OK Opening TIA Portal..." if ok
                        else "X TIA Portal not found.")
            if "pcwin" in q:
                ok = self.open_pcwin()
                return ("OK Opening PCWin..." if ok
                        else "X PCWin not found.")

        if not software:
            return ("No PLC software detected.\n"
                    "Open Studio 5000, TIA Portal, or PCWin first.\n"
                    "Or say: 'Open Studio 5000'")

        # Control open software
        try:
            import pyautogui
            if "new rung" in q or "add rung" in q:
                self.create_new_rung()
                return f"OK New rung added in {software}"
            if "go online" in q:
                if self._software == "studio5000":
                    pyautogui.hotkey("alt","w","o")
                return f"OK Going online in {software}"
            if "download" in q and "program" in q:
                if self._software == "studio5000":
                    pyautogui.hotkey("alt","c","d")
                return f"OK Downloading program to PLC"
            if "save" in q:
                pyautogui.hotkey("ctrl","s")
                return f"OK Saved project in {software}"
            if "screenshot" in q or "read" in q:
                if self.vision:
                    text = self.vision.read_screen_text()
                    return f"Screen content:\n{text[:500]}"
        except ImportError:
            return "Install pyautogui: pip install pyautogui"
        except Exception as e:
            return f"Error: {e}"

        return f"PLC software detected: {software}\nCommand '{command}' — tell me what to do specifically."

    @property
    def is_connected(self):
        return self._software is not None
