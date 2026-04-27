"""
GP PRO AGENT - Screen Vision Module
Sees screen, reads text, finds buttons, clicks accurately.
"""
import threading, time, os, re
from pathlib import Path

class ScreenVision:
    def __init__(self, cache_path):
        self.cache_path = Path(cache_path)
        self.cache_path.mkdir(parents=True, exist_ok=True)
        self._last_screenshot = None
        self._last_text       = ""
        self._ocr_ready       = False
        threading.Thread(target=self._init, daemon=True).start()

    def _init(self):
        try:
            import pytesseract
            from PIL import Image
            self._ocr_ready = True
            print("[VISION] OCR engine ready")
        except ImportError:
            print("[VISION] pytesseract not installed")

    def take_screenshot(self):
        try:
            import pyautogui
            img  = pyautogui.screenshot()
            path = self.cache_path / "latest_screen.png"
            img.save(str(path))
            self._last_screenshot = img
            return img, str(path)
        except Exception as e:
            print(f"[VISION] Screenshot error: {e}")
            return None, None

    def read_screen_text(self):
        img, path = self.take_screenshot()
        if not img:
            return ""
        try:
            import pytesseract
            text = pytesseract.image_to_string(img)
            self._last_text = text
            return text
        except ImportError:
            return "[Install pytesseract for OCR]"
        except Exception as e:
            return f"[OCR error: {e}]"

    def find_text_on_screen(self, search_text):
        try:
            import pytesseract
            img, _ = self.take_screenshot()
            if not img:
                return None
            data = pytesseract.image_to_data(
                img, output_type=pytesseract.Output.DICT)
            for i, word in enumerate(data["text"]):
                if search_text.lower() in word.lower():
                    x = data["left"][i] + data["width"][i]//2
                    y = data["top"][i]  + data["height"][i]//2
                    return (x, y)
        except Exception as e:
            print(f"[VISION] Find text error: {e}")
        return None

    def find_and_click(self, search_text):
        coords = self.find_text_on_screen(search_text)
        if coords:
            try:
                import pyautogui
                pyautogui.click(coords[0], coords[1])
                return True, coords
            except Exception:
                return False, None
        return False, None

    def describe_screen(self):
        text = self.read_screen_text()
        if not text.strip():
            return "Screen is empty or could not read text."
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        return "Screen content:\n" + "\n".join(lines[:15])

    def detect_open_windows(self):
        try:
            import subprocess
            result = subprocess.run(
                ['powershell', '-command',
                 'Get-Process | Where-Object {$_.MainWindowTitle} | Select-Object MainWindowTitle'],
                capture_output=True, text=True, timeout=5)
            lines = [l.strip() for l in result.stdout.split('\n')
                    if l.strip() and 'MainWindowTitle' not in l and '---' not in l]
            return lines[:10]
        except Exception:
            return []

    @property
    def is_ready(self):
        return self._ocr_ready
