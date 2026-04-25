#!/usr/bin/env python3
import sys, os
BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", default="gui")
    args = parser.parse_args()
    from config.settings import Settings
    s = Settings()
    if not s.is_installed() or args.mode=="install":
        from gui.installer_window import InstallerWindow
        InstallerWindow().run()
    else:
        from gui.main_window import MainWindow
        MainWindow().run()
if __name__ == "__main__":
    main()
