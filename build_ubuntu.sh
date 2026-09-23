#!/usr/bin/env bash
set -e
python3 -m pip install -r requirements.txt
pyinstaller --noconfirm --clean --onefile --windowed --add-data "app_icon.png:." --name DownloadCenter app.py
echo "Binary created in dist/DownloadCenter"
