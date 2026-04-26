#!/usr/bin/env python3
import sys, os

# Fix Windows encoding FIRST before anything else
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    os.environ["PYTHONIOENCODING"] = "utf-8"

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", default="gui")
    args = parser.parse_args()

    from config.settings import Settings
    s = Settings()

    if args.mode == "install" or not s.is_installed():
        from gui.installer_window import InstallerWindow
        InstallerWindow().run()
    else:
        from gui.main_window import MainWindow
        MainWindow().run()

if __name__ == "__main__":
    main()
