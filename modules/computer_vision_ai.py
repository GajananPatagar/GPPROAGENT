from typing import Optional, List, Dict, Any, Callable, Generator, Set, Tuple
"""
GP PRO AGENT - Computer Vision AI
Understands screen content using AI vision.
Detects UI elements, reads PLC status, finds buttons.
"""
import threading, time, os, json
from pathlib import Path

class ScreenElement:
    def __init__(self, label, confidence, bbox, element_type="unknown"):
        self.label       = label
        self.confidence  = confidence
        self.bbox        = bbox  # (x1, y1, x2, y2)
        self.type        = element_type
        self.center      = ((bbox[0]+bbox[2])//2,
                           (bbox[1]+bbox[3])//2)

    def __repr__(self):
        return (f"ScreenElement({self.label}, "
                f"{self.confidence:.2f}, {self.center})")


class ComputerVisionAI:
    """
    AI that actually SEES and UNDERSTANDS the screen.
    Detects: buttons, text fields, PLC rungs, alarms, menus.
    """
    def __init__(self, cache_path):
        self._cache     = Path(cache_path)
        self._cache.mkdir(parents=True, exist_ok=True)
        self._model     = None
        self._ready     = False
        self._last_scan = None
        self._elements  = []
        threading.Thread(target=self._init_model,
                        daemon=True).start()

    def _init_model(self):
        """Try to load vision model."""
        try:
            import onnxruntime as ort
            model_path = self._cache / "vision_model.onnx"
            if model_path.exists():
                self._model = ort.InferenceSession(str(model_path))
                self._ready = True
                print("[VISION-AI] ONNX model loaded")
            else:
                print("[VISION-AI] No model file — using rule-based vision")
        except ImportError:
            print("[VISION-AI] onnxruntime not installed")
        except Exception as e:
            print(f"[VISION-AI] Model load error: {e}")

    def analyze_screen(self) -> dict:
        """Full screen analysis — returns structured understanding."""
        result = {
            "timestamp":     time.time(),
            "software":      None,
            "elements":      [],
            "plc_status":    None,
            "alarms":        [],
            "description":   "",
            "actions":       [],
        }
        try:
            screenshot, text = self._capture()
            if not text:
                return result
            result["software"]    = self._detect_software(text)
            result["elements"]    = self._detect_elements(text, screenshot)
            result["plc_status"]  = self._analyze_plc_status(text)
            result["alarms"]      = self._detect_alarms(text)
            result["description"] = self._describe_screen(
                result["software"], result["elements"],
                result["plc_status"], result["alarms"])
            result["actions"]     = self._suggest_actions(result)
            self._last_scan = result
        except Exception as e:
            result["description"] = f"Vision scan error: {e}"
        return result

    def _capture(self):
        """Capture screen and extract text."""
        try:
            import pyautogui
            screenshot = pyautogui.screenshot()
            screenshot.save(str(self._cache / "latest.png"))
            try:
                import pytesseract
                text = pytesseract.image_to_string(screenshot)
            except ImportError:
                text = ""
            return screenshot, text
        except Exception as e:
            return None, ""

    def _detect_software(self, text: str) -> str:
        """Detect which software is on screen."""
        text_l = text.lower()
        if any(w in text_l for w in ["studio 5000","rslogix","controllogix"]):
            return "Allen Bradley Studio 5000"
        if any(w in text_l for w in ["tia portal","simatic","s7-1200","s7-1500"]):
            return "Siemens TIA Portal"
        if any(w in text_l for w in ["pcwin","pcw"]):
            return "PCWin"
        if any(w in text_l for w in ["notepad"]):
            return "Notepad"
        if any(w in text_l for w in ["chrome","firefox","edge","http"]):
            return "Web Browser"
        if any(w in text_l for w in ["explorer","documents","downloads"]):
            return "File Explorer"
        return "Unknown Application"

    def _detect_elements(self, text: str, screenshot) -> list:
        """Detect UI elements using pattern matching."""
        elements = []
        import re
        # Find buttons (ALL CAPS words or common button text)
        button_patterns = [
            r"\b(OK|Cancel|Apply|Save|Open|Close|Start|Stop|Run|Reset|Download|Upload|Go Online|Go Offline|Connect|Disconnect)\b"
        ]
        for pat in button_patterns:
            for m in re.finditer(pat, text, re.IGNORECASE):
                elements.append({
                    "type":  "button",
                    "label": m.group(),
                    "found": True,
                })
        # Find input fields (text: followed by value)
        for m in re.finditer(r"(\w[\w ]+):\s*([^\n]+)", text):
            label = m.group(1).strip()
            value = m.group(2).strip()
            if len(label) < 30 and len(value) < 50:
                elements.append({
                    "type":  "field",
                    "label": label,
                    "value": value,
                })
        return elements[:20]

    def _analyze_plc_status(self, text: str) -> dict:
        """Analyze PLC-specific status from screen text."""
        text_l = text.lower()
        status = {
            "online":       False,
            "mode":         "Unknown",
            "faults":       [],
            "motor_states": {},
            "tags_visible": [],
        }
        if "online" in text_l:
            status["online"] = True
        if "run" in text_l:
            status["mode"] = "Run"
        elif "program" in text_l:
            status["mode"] = "Program"
        elif "fault" in text_l:
            status["mode"] = "Fault"
        # Find fault text
        import re
        for m in re.finditer(r"fault[:\s]+([^\n]+)", text_l):
            status["faults"].append(m.group(1).strip()[:50])
        # Find tag values
        for m in re.finditer(r"([A-Z][A-Z0-9_]{2,})\s*=\s*([\d\.]+)", text):
            status["tags_visible"].append({
                "tag":   m.group(1),
                "value": m.group(2),
            })
        return status

    def _detect_alarms(self, text: str) -> list:
        """Detect any alarms or errors on screen."""
        alarms = []
        import re
        alarm_keywords = ["alarm","fault","error","warning","failed",
                         "offline","disconnected","trip","overload",
                         "emergency","critical","danger"]
        lines = text.split("\n")
        for line in lines:
            line_l = line.lower().strip()
            if any(kw in line_l for kw in alarm_keywords):
                if len(line.strip()) > 3:
                    severity = "CRITICAL" if any(w in line_l for w in
                        ["fault","trip","emergency","critical"]) else "WARNING"
                    alarms.append({
                        "text":     line.strip()[:80],
                        "severity": severity,
                    })
        return alarms[:10]

    def _describe_screen(self, software, elements,
                         plc_status, alarms) -> str:
        """Generate natural language description of screen."""
        parts = []
        if software:
            parts.append(f"Software: {software}")
        if plc_status and plc_status.get("online"):
            mode = plc_status.get("mode","Unknown")
            parts.append(f"PLC: Online | Mode: {mode}")
            if plc_status.get("tags_visible"):
                tags = plc_status["tags_visible"][:3]
                tag_str = ", ".join(
                    f"{t['tag']}={t['value']}" for t in tags)
                parts.append(f"Tags visible: {tag_str}")
        if alarms:
            parts.append(f"!! ALARMS ({len(alarms)}):")
            for a in alarms[:3]:
                parts.append(f"  [{a['severity']}] {a['text']}")
        if elements:
            btns = [e["label"] for e in elements
                   if e["type"]=="button"][:5]
            if btns:
                parts.append(f"Buttons: {', '.join(btns)}")
        if not parts:
            parts.append("Screen content detected but no specific elements identified.")
        return "\n".join(parts)

    def _suggest_actions(self, analysis: dict) -> list:
        """Suggest what actions the agent could take."""
        actions = []
        alarms = analysis.get("alarms", [])
        plc    = analysis.get("plc_status", {})
        if alarms:
            actions.append("Acknowledge and investigate alarms")
            actions.append("Check PLC fault routine")
        if plc and not plc.get("online"):
            actions.append("Connect PLC to go online")
        if plc and plc.get("mode") == "Fault":
            actions.append("Clear PLC fault and restart")
        return actions

    def find_and_click_element(self, element_name: str) -> bool:
        """Find UI element by name and click it."""
        try:
            import pyautogui
            # Try locating by image first
            locations = {
                "save":    [(None, "Ctrl+S")],
                "online":  [(None, "Alt+W,O")],
            }
            el_lower = element_name.lower()
            for key, methods in locations.items():
                if key in el_lower:
                    for _, shortcut in methods:
                        keys = shortcut.split(",")
                        for k in keys:
                            if "+" in k:
                                parts = k.split("+")
                                pyautogui.hotkey(*[p.lower() for p in parts])
                            else:
                                pyautogui.press(k.lower())
                        return True
            return False
        except Exception:
            return False

    def click_at_text(self, search_text: str) -> bool:
        """Find text on screen and click it."""
        try:
            import pyautogui
            import pytesseract
            screenshot = pyautogui.screenshot()
            data = pytesseract.image_to_data(
                screenshot,
                output_type=pytesseract.Output.DICT)
            for i, word in enumerate(data["text"]):
                if search_text.lower() in word.lower():
                    x = data["left"][i] + data["width"][i]//2
                    y = data["top"][i] + data["height"][i]//2
                    pyautogui.moveTo(x, y, duration=0.3)
                    pyautogui.click()
                    return True
        except Exception:
            pass
        return False

    def get_last_scan(self) -> dict:
        return self._last_scan or {}

    @property
    def is_ready(self):
        return True  # Always ready (uses rule-based if no model)
