"""
GP PRO AGENT — Voice Module
Speak to AI, AI speaks back. 100% offline.
"""
import threading, sys, os
from pathlib import Path

class VoiceEngine:
    def __init__(self, on_text_callback):
        self.on_text   = on_text_callback
        self._active   = False
        self._tts      = None
        self._listener = None
        self._ready    = False
        threading.Thread(target=self._init, daemon=True).start()

    def _init(self):
        try:
            import pyttsx3
            self._tts = pyttsx3.init()
            self._tts.setProperty("rate", 165)
            self._tts.setProperty("volume", 0.9)
            voices = self._tts.getProperty("voices")
            # Prefer female voice
            for v in voices:
                if "female" in v.name.lower() or "zira" in v.name.lower():
                    self._tts.setProperty("voice", v.id)
                    break
            self._ready = True
            print("[VOICE] TTS engine ready")
        except ImportError:
            print("[VOICE] pyttsx3 not installed")

    def speak(self, text):
        if not self._ready or not self._tts:
            return
        def _do():
            try:
                clean = text.replace(">>","").replace("-","").replace("```","")
                # Limit to 300 chars for speed
                if len(clean) > 300:
                    clean = clean[:300] + "..."
                self._tts.say(clean)
                self._tts.runAndWait()
            except Exception as e:
                print(f"[VOICE] TTS error: {e}")
        threading.Thread(target=_do, daemon=True).start()

    def start_listening(self, callback):
        self._active = True
        threading.Thread(target=self._listen_loop,
                        args=(callback,), daemon=True).start()

    def stop_listening(self):
        self._active = False

    def _listen_loop(self, callback):
        try:
            import speech_recognition as sr
            r  = sr.Recognizer()
            r.energy_threshold = 300
            r.dynamic_energy_threshold = True
            mic = sr.Microphone()
            print("[VOICE] Microphone ready")
            with mic as source:
                r.adjust_for_ambient_noise(source, duration=1)
            while self._active:
                try:
                    with mic as source:
                        audio = r.listen(source, timeout=5,
                                        phrase_time_limit=10)
                    text = r.recognize_sphinx(audio)  # Offline
                    if text.strip():
                        print(f"[VOICE] Heard: {text}")
                        callback(text)
                except sr.WaitTimeoutError:
                    pass
                except Exception as e:
                    # Try google if sphinx fails (needs internet)
                    try:
                        text = r.recognize_google(audio)
                        if text.strip():
                            callback(text)
                    except:
                        pass
        except ImportError:
            print("[VOICE] speech_recognition not installed")
        except Exception as e:
            print(f"[VOICE] Listen error: {e}")

    @property
    def is_ready(self):
        return self._ready
