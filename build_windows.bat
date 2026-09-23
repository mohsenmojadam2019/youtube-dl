@echo off
python -m pip install -r requirements.txt
pyinstaller --noconfirm --clean --onefile --windowed --name DownloadCenter app.py
echo EXE created in dist\DownloadCenter.exe
