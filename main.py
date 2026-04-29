#!/usr/bin/env python3
"""
GP PRO AGENT v4.0
Auto-installs everything. No manual steps.
"""
import sys, os

# Fix Windows encoding safely
if sys.platform == "win32":
    try:
        if sys.stdout and hasattr(sys.stdout,'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        if sys.stderr and hasattr(sys.stderr,'reconfigure'):
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
    os.environ["PYTHONIOENCODING"] = "utf-8"

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", default="gui")
    parser.add_argument("--skip-setup", action="store_true")
    args = parser.parse_args()

    from config.settings import Settings
    s = Settings()

    if args.mode == "install":
        from gui.setup_window import SetupWindow
        SetupWindow().run()
        return

    # Check if Ollama is running
    ollama_ready = False
    try:
        import urllib.request
        with urllib.request.urlopen(
                "http://localhost:11434/api/tags",
                timeout=2) as r:
            ollama_ready = r.status == 200
    except Exception:
        pass

    # Show setup window if needed
    needs_setup = (
        not s.is_installed() or
        not ollama_ready
    ) and not args.skip_setup

    if needs_setup:
        from gui.setup_window import SetupWindow
        SetupWindow().run()
    else:
        from gui.main_window import MainWindow
        MainWindow().run()

if __name__ == "__main__":
    main()
