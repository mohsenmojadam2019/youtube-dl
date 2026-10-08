# Download Center

دانلودر دسکتاپ فارسی برای YouTube، Instagram و سایت‌های پشتیبانی‌شده توسط `yt-dlp`.

## اجرا

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Ubuntu: source .venv/bin/activate
# Ubuntu (اگر Tkinter نصب نیست): sudo apt install python3-tk
python -m pip install -r requirements.txt
python app.py
```

در لینوکس، متن فارسی با shaping و RTL درست نمایش داده می‌شود. برنامه همچنین پراکسی‌های محلی رایج مثل Hiddify را به‌صورت خودکار شناسایی می‌کند.

برای تبدیل به فایل اجرایی، روی همان سیستم مقصد اجرا کنید:

- Windows: `build_windows.bat` → `dist/DownloadCenter.exe`
- Ubuntu: `chmod +x build_ubuntu.sh && ./build_ubuntu.sh` → `dist/DownloadCenter`

برای تبدیل ویدئو به MP3، نصب بودن `ffmpeg` روی سیستم ضروری است. Instagram ممکن است برای لینک‌های خصوصی یا محدود به فایل cookies/login نیاز داشته باشد.


## افزونه Chrome

نسخه افزونه Chrome به برنامه دسکتاپ اضافه شده است. رابط افزونه در پوشه
extension/ و سرویس محلی در bridge/server.py قرار دارد.

- اجرا: bash start.sh
- نصب افزونه: chrome://extensions → Developer mode → Load unpacked → extension/
- پشتیبانی: وب‌سایت‌های قابل پشتیبانی توسط yt-dlp و لینک‌های مستقیم
- انتخاب کیفیت‌های 1080p، 720p، 480p و 360p و استخراج صدا به MP3
- مدیریت صف دانلود و لغو دانلودهای فعال
- ذخیره پیش‌فرض: ~/Downloads/DownloadCenter

جزئیات و محدودیت‌ها: docs/CHROME.md
