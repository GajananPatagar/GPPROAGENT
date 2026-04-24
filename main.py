#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config.settings import Settings

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["gui","cli","status","install"], default="gui")
    args = parser.parse_args()

    if args.mode == "install":
        from installer.brain_installer import BrainInstaller
        BrainInstaller().run()
        return
    if args.mode == "status":
        from core.agent import GPProAgent
        GPProAgent().print_status()
        return
    if args.mode == "cli":
        from core.agent import GPProAgent
        GPProAgent().run_cli()
        return
    from gui.main_window import GPProWindow
    GPProWindow().run()

if __name__ == "__main__":
    main()
