"""
GP PRO AGENT - Gesture Control
Control GP PRO AGENT with hand gestures via webcam.
Wave, point, thumbs up - all recognized and executed.
"""
import threading, time, json, queue
from pathlib import Path
from typing import Callable, Optional

class GestureCommand:
    WAVE_HELLO      = "wave_hello"
    THUMBS_UP       = "thumbs_up"
    THUMBS_DOWN     = "thumbs_down"
    POINT_UP        = "point_up"
    POINT_DOWN      = "point_down"
    OPEN_HAND       = "open_hand"
    FIST            = "fist"
    PEACE           = "peace"
    OK_SIGN         = "ok_sign"
    SWIPE_LEFT      = "swipe_left"
    SWIPE_RIGHT     = "swipe_right"

    # Map gestures to commands
    ACTIONS = {
        WAVE_HELLO:   "Hello! How can I help?",
        THUMBS_UP:    "Confirm last action",
        THUMBS_DOWN:  "Cancel last action",
        POINT_UP:     "Scroll up",
        POINT_DOWN:   "Scroll down",
        OPEN_HAND:    "Take a screenshot",
        FIST:         "Stop current operation",
        PEACE:        "Show status",
        OK_SIGN:      "Confirm",
        SWIPE_LEFT:   "Go back",
        SWIPE_RIGHT:  "Go forward",
    }


class GestureController:
    """
    Webcam-based gesture recognition.
    Uses MediaPipe (if available) or falls back to
    motion detection for basic gestures.
    """
    def __init__(self, brain_root: str,
                 command_callback: Callable,
                 notify_callback: Callable):
        self._path      = Path(brain_root) / "gesture"
        self._path.mkdir(parents=True, exist_ok=True)
        self._on_command = command_callback
        self._notify    = notify_callback
        self._running   = False
        self._cap       = None
        self._thread    = None
        self._gesture_queue = queue.Queue()
        self._last_gesture  = None
        self._gesture_cooldown = 2.0
        self._last_gesture_time = 0
        self._custom_gestures = {}
        self._load_config()

    def _load_config(self):
        try:
            cfg = self._path / "config.json"
            if cfg.exists():
                with open(cfg) as f:
                    data = json.load(f)
                self._custom_gestures = data.get("custom", {})
        except Exception:
            pass

    def start(self) -> tuple:
        """Start gesture recognition."""
        try:
            import cv2
            self._cap = cv2.VideoCapture(0)
            if not self._cap.isOpened():
                return False, "No webcam found"
            self._running = True
            self._thread  = threading.Thread(
                target=self._recognition_loop, daemon=True)
            self._thread.start()
            self._notify("[GESTURE] Webcam gesture control active")
            return True, "Gesture control started"
        except ImportError:
            return False, "Install opencv: pip install opencv-python"
        except Exception as e:
            return False, str(e)

    def stop(self):
        self._running = False
        if self._cap:
            self._cap.release()
            self._cap = None

    def _recognition_loop(self):
        """Main recognition loop."""
        try:
            self._run_mediapipe()
        except ImportError:
            self._run_motion_detection()
        except Exception as e:
            self._run_motion_detection()

    def _run_mediapipe(self):
        """Full gesture recognition with MediaPipe."""
        import cv2
        import mediapipe as mp

        mp_hands = mp.solutions.hands
        hands    = mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.5)

        self._notify("[GESTURE] MediaPipe hands active - full gesture support")

        while self._running:
            ret, frame = self._cap.read()
            if not ret:
                break
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results   = hands.process(frame_rgb)

            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    gesture = self._classify_hand(hand_landmarks)
                    if gesture:
                        self._process_gesture(gesture)
            time.sleep(0.05)

        hands.close()

    def _classify_hand(self, landmarks) -> Optional[str]:
        """Classify hand gesture from landmarks."""
        lm = landmarks.landmark

        # Finger tips and bases
        tips   = [8, 12, 16, 20]
        bases  = [6, 10, 14, 18]
        thumb_tip  = lm[4]
        thumb_base = lm[2]
        index_tip  = lm[8]
        middle_tip = lm[12]
        wrist      = lm[0]

        # Check which fingers are up
        fingers_up = []
        for tip, base in zip(tips, bases):
            if lm[tip].y < lm[base].y:
                fingers_up.append(True)
            else:
                fingers_up.append(False)

        thumb_up = thumb_tip.y < thumb_base.y
        n_up     = sum(fingers_up)

        # Classify based on finger positions
        if thumb_up and n_up == 0:
            return GestureCommand.THUMBS_UP
        if not thumb_up and n_up == 0:
            return GestureCommand.THUMBS_DOWN
        if n_up == 4:
            return GestureCommand.OPEN_HAND
        if n_up == 0 and not thumb_up:
            return GestureCommand.FIST
        if fingers_up[0] and not fingers_up[1]:
            return GestureCommand.POINT_UP
        if fingers_up[0] and fingers_up[1] and not fingers_up[2]:
            return GestureCommand.PEACE
        if n_up == 1 and fingers_up[2]:
            return GestureCommand.OK_SIGN
        return None

    def _run_motion_detection(self):
        """Fallback: simple motion detection."""
        import cv2
        import numpy as np

        self._notify(
            "[GESTURE] Basic motion detection mode\n"
            "Install mediapipe for full gesture support:\n"
            "pip install mediapipe")

        prev_frame = None
        while self._running:
            ret, frame = self._cap.read()
            if not ret:
                break

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.GaussianBlur(gray, (21,21), 0)

            if prev_frame is None:
                prev_frame = gray
                continue

            diff = cv2.absdiff(prev_frame, gray)
            _, thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)
            motion = thresh.sum() / (thresh.size * 255)

            if motion > 0.1:  # Significant motion
                self._process_gesture(GestureCommand.WAVE_HELLO)

            prev_frame = gray
            time.sleep(0.1)

    def _process_gesture(self, gesture: str):
        """Process detected gesture with cooldown."""
        now = time.time()
        if now - self._last_gesture_time < self._gesture_cooldown:
            return
        if gesture == self._last_gesture:
            return

        self._last_gesture      = gesture
        self._last_gesture_time = now

        # Get command for gesture
        action = self._custom_gestures.get(gesture,
            GestureCommand.ACTIONS.get(gesture))

        if action:
            self._notify(f"[GESTURE] Detected: {gesture}")
            self._on_command(action)

    def add_custom_gesture(self, gesture_id: str,
                           command: str):
        """Map a gesture to a custom command."""
        self._custom_gestures[gesture_id] = command
        try:
            cfg = self._path / "config.json"
            with open(cfg,"w") as f:
                json.dump({"custom": self._custom_gestures}, f, indent=2)
        except Exception:
            pass

    def get_gesture_list(self) -> list:
        gestures = []
        for gesture, action in GestureCommand.ACTIONS.items():
            custom = self._custom_gestures.get(gesture)
            gestures.append({
                "gesture": gesture,
                "default": action,
                "custom":  custom,
            })
        return gestures

    @property
    def is_running(self):
        return self._running
