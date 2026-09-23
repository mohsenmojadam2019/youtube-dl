@echo off
python -m pip install -r requirements.txt
pyinstaller --noconfirm --clean --onefile --windowed --add-data "app_icon.png;." --name DownloadCenter app.py
echo EXE created in dist\DownloadCenter.exe
