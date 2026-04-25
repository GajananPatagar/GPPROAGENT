#!/bin/bash
set -e
echo "GP PRO AGENT — Auto Installer"
command -v python3 &>/dev/null || (sudo apt-get install -y python3 python3-pip)
python3 -m pip install --upgrade pip --quiet
python3 installer/brain_installer.py
python3 main.py --mode gui
