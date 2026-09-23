@echo off
if not exist .venv\Scripts\python.exe python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --onefile --windowed --add-data "app_icon.png;." --name DownloadCenter app.py
if exist dist\DownloadCenter.exe (echo EXE created in dist\DownloadCenter.exe) else (echo Build failed & exit /b 1)
