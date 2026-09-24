import os
import json
import sys
import queue
import socket
import threading
import ctypes
import shutil
from pathlib import Path

try:
    import tkinter as tk
    import tkinter.font as tkfont
    from tkinter import filedialog, messagebox, ttk
except ModuleNotFoundError:
    tk_root = Path(__file__).resolve().parent / ".tkdeps" / "root"
    if not tk_root.exists():
        raise
    py_root = tk_root / "usr" / "lib" / "python3.10"
    sys.path[:0] = [str(py_root), str(py_root / "lib-dynload")]
    os.environ.setdefault("TCL_LIBRARY", "/usr/share/tcltk/tcl8.6")
    os.environ.setdefault("TK_LIBRARY", str(tk_root / "usr/share/tcltk/tk8.6"))
    ctypes.CDLL(str(tk_root / "usr/lib/x86_64-linux-gnu/libtk8.6.so"), mode=ctypes.RTLD_GLOBAL)
    ctypes.CDLL(str(tk_root / "usr/lib/libBLT.2.5.so.8.6"), mode=ctypes.RTLD_GLOBAL)
    import tkinter as tk
    import tkinter.font as tkfont
    from tkinter import filedialog, messagebox, ttk

import arabic_reshaper
from bidi.algorithm import get_display

try:
    import yt_dlp
except ImportError:
    yt_dlp = None


BG = "#0b1220"
PANEL = "#111c2e"
PANEL_2 = "#16243a"
TEXT = "#f3f7ff"
MUTED = "#8ea3bd"
ACCENT = "#4f8cff"
GREEN = "#20c997"
RED = "#ff6b81"


def fa(text):
    """Shape Persian/Arabic text for Tk on Linux."""
    if text is None:
        return ""
    value = str(text)
    return get_display(arabic_reshaper.reshape(value))


def pick_ui_font(root):
    families = set(tkfont.families(root))
    for family in ("Vazirmatn", "Noto Sans Arabic", "DejaVu Sans", "Ubuntu"):
        if family in families:
            return family
    return "TkDefaultFont"


def human_size(value):
    if not value:
        return "—"
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(value)
    for unit in units:
        if size < 1024 or unit == units[-1]:
            return f"{size:.1f} {unit}"
        size /= 1024


def human_time(seconds):
    if seconds is None or seconds < 0:
        return "—"
    seconds = int(seconds)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}" if hours else f"{minutes:02d}:{seconds:02d}"


class DownloadCenter(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("دانلودر حرفه‌ای | Download Center")
        self.geometry("980x680")
        self.minsize(820, 580)
        self.configure(bg=BG)
        self.ui_font = pick_ui_font(self)
        try:
            icon_root = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
            icon_path = icon_root / "app_icon.png"
            self.app_icon = tk.PhotoImage(file=str(icon_path))
            self.iconphoto(True, self.app_icon)
        except tk.TclError:
            self.app_icon = None
        self.events = queue.Queue()
        self.running = False
        self.download_queue = []
        self.history = []
        self.destination = tk.StringVar(value=str(Path.home() / "Downloads"))
        self.url = tk.StringVar()
        self.quality = tk.StringVar(value=fa("بهترین کیفیت"))
        self.cookies = tk.StringVar()
        self.active_proxy = tk.StringVar(value=fa("تشخیص خودکار"))
        self.active_profile = None
        self.auto_proxy = None
        self.status = tk.StringVar(value=fa("آماده دریافت لینک شما"))
        self.stats = tk.StringVar(value=fa("حجم: —   سرعت: —   زمان باقی‌مانده: —"))
        self.progress = tk.DoubleVar(value=0)
        self._setup_style()
        self._build_ui()
        self.auto_proxy = self._detect_local_proxy()
        if self.auto_proxy:
            self.active_proxy.set(fa(f"اتصال خودکار: {self.auto_proxy[0]}"))
            self.write_log(f"پراکسی محلی شناسایی شد: {self.auto_proxy[0]}")
        self.after(100, self._drain_events)

    def _detect_local_proxy(self):
        candidates = [
            ("Hiddify", "http://127.0.0.1:12334", 12334),
            ("BPB / Hiddify CLI", "http://127.0.0.1:12444", 12444),
            ("Clash", "http://127.0.0.1:7890", 7890),
            ("Local SOCKS", "socks5://127.0.0.1:1080", 1080),
        ]
        for name, url, port in candidates:
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=0.25):
                    return name, url
            except OSError:
                continue
        return None

    def _set_status(self, text):
        self.status.set(fa(text))

    def _set_stats(self, text):
        self.stats.set(fa(text))

    def _setup_style(self):
        for named in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont", "TkCaptionFont"):
            try:
                tkfont.nametofont(named).configure(family=self.ui_font)
            except tk.TclError:
                pass
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TProgressbar", troughcolor="#22334d", background=ACCENT, borderwidth=0, thickness=12)
        style.configure("Treeview", background=PANEL, fieldbackground=PANEL, foreground=TEXT, rowheight=34, borderwidth=0, font=(self.ui_font, 10))
        style.configure("Treeview.Heading", background=PANEL_2, foreground=MUTED, relief="flat", font=(self.ui_font, 10, "bold"))
        style.configure("TCombobox", font=(self.ui_font, 10))
        style.map("Treeview", background=[("selected", "#234879")])

    def _label(self, parent, text, size=11, color=TEXT, bold=False):
        return tk.Label(parent, text=fa(text), bg=parent.cget("bg"), fg=color,
                        justify="right", anchor="e",
                        font=(self.ui_font, size, "bold" if bold else "normal"))

    def _button(self, parent, text, command, primary=False):
        return tk.Button(parent, text=fa(text), command=command, bg=ACCENT if primary else PANEL_2,
                         fg="white", activebackground="#6da2ff", activeforeground="white",
                         relief="flat", borderwidth=0, padx=18, pady=10,
                         font=(self.ui_font, 10, "bold"), cursor="hand2")

    def _build_ui(self):
        header = tk.Frame(self, bg=BG)
        header.pack(fill="x", padx=34, pady=(28, 12))
        tk.Label(header, text="⬇", bg=ACCENT, fg="white", width=3, height=1,
                 font=(self.ui_font, 22, "bold")).pack(side="right", padx=(0, 12))
        title = tk.Frame(header, bg=BG)
        title.pack(side="right")
        self._label(title, "دانلود سنتر", 24, TEXT, True).pack(anchor="e")
        self._label(title, "دانلود سریع و ساده از یوتیوب و اینستاگرام", 10, MUTED).pack(anchor="e")
        self._label(header, "نسخه ۱.۰  •  Windows / Ubuntu", 10, MUTED).pack(side="left", pady=15)

        main = tk.Frame(self, bg=BG)
        main.pack(fill="both", expand=True, padx=34)
        card = tk.Frame(main, bg=PANEL, padx=24, pady=22)
        card.pack(fill="x")
        self._label(card, "لینک ویدئو یا پست را وارد کنید", 16, TEXT, True).pack(anchor="e")
        self._label(card, "پشتیبانی از YouTube، Instagram و صدها سایت دیگر با موتور yt-dlp", 10, MUTED).pack(anchor="e", pady=(3, 16))
        row = tk.Frame(card, bg=PANEL)
        row.pack(fill="x")
        self._button(row, "دریافت اطلاعات", self.inspect, primary=False).pack(side="left", padx=(0, 8))
        entry = tk.Entry(row, textvariable=self.url, bg="#1d2c43", fg=TEXT, insertbackground=TEXT,
                         relief="flat", justify="left", font=(self.ui_font, 12))
        entry.pack(side="right", fill="x", expand=True, ipady=12, padx=(0, 8))
        entry.focus_set()
        self._button(row, "چسباندن", self.paste_url).pack(side="right")
        self._button(row, "افزودن به صف", self.add_to_queue, primary=True).pack(side="right", padx=(8, 0))

        options = tk.Frame(main, bg=BG)
        options.pack(fill="x", pady=16)
        quality = tk.Frame(options, bg=PANEL, padx=18, pady=16)
        quality.pack(side="right", fill="both", expand=True, padx=(8, 0))
        self._label(quality, "کیفیت دانلود", 10, MUTED, True).pack(anchor="e")
        ttk.Combobox(quality, textvariable=self.quality,
                     values=[fa("بهترین کیفیت"), "1080p", "720p", "480p", fa("فقط صدا (MP3)")],
                     state="readonly", justify="right", font=(self.ui_font, 10)).pack(fill="x", pady=(8, 0), ipady=5)
        folder = tk.Frame(options, bg=PANEL, padx=18, pady=16)
        folder.pack(side="right", fill="both", expand=True, padx=(0, 8))
        self._label(folder, "مسیر ذخیره‌سازی", 10, MUTED, True).pack(anchor="e")
        frow = tk.Frame(folder, bg=PANEL)
        frow.pack(fill="x", pady=(8, 0))
        self._button(frow, "انتخاب", self.choose_folder).pack(side="left")
        tk.Entry(frow, textvariable=self.destination, bg="#1d2c43", fg=TEXT, relief="flat", justify="left",
                 font=(self.ui_font, 10)).pack(side="right", fill="x", expand=True, ipady=8, padx=(0, 8))

        bottom = tk.Frame(main, bg=BG)
        bottom.pack(fill="both", expand=True)
        left = tk.Frame(bottom, bg=PANEL, padx=18, pady=18)
        left.pack(side="left", fill="both", expand=True, padx=(8, 0))
        self._label(left, "صف دانلود", 15, TEXT, True).pack(anchor="e")
        self.progress_bar = ttk.Progressbar(left, variable=self.progress, maximum=100)
        self.progress_bar.pack(fill="x", pady=(18, 8))
        self._label(left, "آماده دریافت لینک شما", 10, MUTED).pack(anchor="e")
        self.status_label = tk.Label(left, textvariable=self.status, bg=PANEL, fg=TEXT,
                                     justify="right", anchor="e", font=(self.ui_font, 11))
        self.status_label.pack(fill="x", pady=(4, 18))
        self.stats_label = tk.Label(left, textvariable=self.stats, bg=PANEL, fg=MUTED,
                                    justify="right", anchor="e", font=(self.ui_font, 10))
        self.stats_label.pack(fill="x", pady=(0, 14))
        self._button(left, "شروع دانلود", self.start_download, primary=True).pack(fill="x")
        self._button(left, "نمایش صف دانلود", self.show_queue).pack(fill="x", pady=(8, 0))
        self._button(left, "پاک‌کردن صف", self.clear_log).pack(fill="x", pady=(8, 0))
        self._button(left, "مدیریت Proxy / VLESS", self.manage_proxies).pack(fill="x", pady=(8, 0))
        self._label(left, "ساخته شده توسط redcoweb.ir", 9, MUTED).pack(pady=(14, 0))

        right = tk.Frame(bottom, bg=PANEL, padx=18, pady=18)
        right.pack(side="right", fill="both", expand=True, padx=(0, 8))
        self._label(right, "گزارش فعالیت", 15, TEXT, True).pack(anchor="e")
        self.log = tk.Text(right, bg="#0e1727", fg=MUTED, relief="flat", height=10, wrap="word",
                           state="disabled", font=(self.ui_font, 10))
        self.log.tag_configure("rtl", justify="right")
        self.log.pack(fill="both", expand=True, pady=(12, 0))
        self.write_log("برنامه آماده است. یک لینک وارد کنید.")

    def paste_url(self):
        try:
            self.url.set(self.clipboard_get())
        except tk.TclError:
            self._set_status("متنی در کلیپ‌بورد نیست")

    def choose_folder(self):
        folder = filedialog.askdirectory(initialdir=self.destination.get())
        if folder:
            self.destination.set(folder)

    def manage_proxies(self):
        dialog = tk.Toplevel(self)
        dialog.title("مدیریت اتصال دانلود")
        dialog.geometry("620x440")
        dialog.configure(bg=PANEL)
        dialog.transient(self)
        dialog.grab_set()
        self._label(dialog, "افزودن کانفیگ اتصال", 16, TEXT, True).pack(anchor="e", padx=22, pady=(20, 4))
        self._label(dialog, "VLESS / VMess / Trojan / Shadowsocks یا HTTP / SOCKS", 10, MUTED).pack(anchor="e", padx=22)
        box = tk.Text(dialog, height=8, bg="#0e1727", fg=TEXT, insertbackground=TEXT, relief="flat", wrap="word")
        box.pack(fill="x", padx=22, pady=14)
        name = tk.StringVar(value="اتصال من جدید")
        tk.Entry(dialog, textvariable=name, bg="#1d2c43", fg=TEXT, insertbackground=TEXT, relief="flat", justify="right").pack(fill="x", padx=22, ipady=8)
        profiles = self._load_profiles()
        listbox = tk.Listbox(dialog, bg="#0e1727", fg=TEXT, selectbackground="#234879", relief="flat", height=5)
        listbox.pack(fill="both", expand=True, padx=22, pady=14)
        for profile in profiles:
            listbox.insert("end", f"{profile['name']}  •  {profile['scheme']}")
        def add_profile():
            raw = box.get("1.0", "end").strip()
            scheme = raw.split(":", 1)[0].lower() if ":" in raw else "unknown"
            allowed = {"vless", "vmess", "trojan", "ss", "ssr", "http", "https", "socks5", "socks5h"}
            if scheme not in allowed:
                messagebox.showwarning("کانفیگ نامعتبر", "فرمت پشتیبانی‌نشده یا لینک خالی است.", parent=dialog)
                return
            profiles.append({"name": name.get().strip() or "اتصال جدید", "scheme": scheme, "value": raw})
            self._save_profiles(profiles)
            listbox.insert("end", f"{profiles[-1]['name']}  •  {scheme}")
            box.delete("1.0", "end")
        def activate_profile():
            selected = listbox.curselection()
            if not selected:
                self.active_proxy.set("بدون پراکسی")
            else:
                profile = profiles[selected[0]]
                self.active_proxy.set(profile["name"])
                self.active_profile = profile
                self.write_log(f"اتصال انتخاب شد: {profile['name']} ({profile['scheme']})")
                if profile["scheme"] not in {"http", "https", "socks5", "socks5h"}:
                    messagebox.showinfo("نیاز به هستهٔ اتصال", "این کانفیگ ذخیره شد. برای استفادهٔ واقعی VLESS/VMess/Trojan باید sing-box یا Xray روی سیستم نصب و اجرا شود.", parent=dialog)
            dialog.destroy()
        actions = tk.Frame(dialog, bg=PANEL); actions.pack(fill="x", padx=22, pady=(0, 18))
        self._button(actions, "افزودن", add_profile, primary=True).pack(side="right", padx=(8, 0))
        self._button(actions, "فعال‌سازی انتخاب‌شده", activate_profile).pack(side="right")
        self._button(actions, "بستن", dialog.destroy).pack(side="left")

    def _profiles_path(self):
        return Path.home() / ".download-center-profiles.json"

    def _load_profiles(self):
        try:
            return json.loads(self._profiles_path().read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def _save_profiles(self, profiles):
        self._profiles_path().write_text(json.dumps(profiles, ensure_ascii=False, indent=2), encoding="utf-8")

    def clear_log(self):
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")
        self.progress.set(0)
        self._set_stats("حجم: —   سرعت: —   زمان باقی‌مانده: —")

    def add_to_queue(self):
        url = self.url.get().strip()
        if not url:
            messagebox.showwarning(fa("لینک لازم است"), fa("ابتدا لینک را وارد کنید."))
            return
        self.download_queue.append(url)
        self.write_log(f"به صف اضافه شد ({len(self.download_queue)}): {url}")
        self.url.set("")
        self._set_status(f"{len(self.download_queue)} لینک در صف قرار دارد")

    def show_queue(self):
        dialog = tk.Toplevel(self)
        dialog.title("صف دانلود")
        dialog.geometry("650x380")
        dialog.configure(bg=PANEL)
        self._label(dialog, "صف دانلود", 17, TEXT, True).pack(anchor="e", padx=22, pady=(18, 8))
        queue_box = tk.Listbox(dialog, bg="#0e1727", fg=TEXT, selectbackground="#234879", relief="flat", height=12)
        queue_box.pack(fill="both", expand=True, padx=22)
        for index, item in enumerate(self.download_queue, 1):
            queue_box.insert("end", f"{index}. {item}")
        actions = tk.Frame(dialog, bg=PANEL); actions.pack(fill="x", padx=22, pady=16)
        self._button(actions, "حذف انتخاب‌شده", lambda: self.remove_queue_item(queue_box)).pack(side="right")
        self._button(actions, "بستن", dialog.destroy).pack(side="left")

    def remove_queue_item(self, box):
        selected = box.curselection()
        if selected:
            self.download_queue.pop(selected[0])
            box.delete(selected[0])
            for index in range(selected[0], box.size()):
                box.delete(index); box.insert(index, f"{index + 1}. {self.download_queue[index]}")

    def write_log(self, text):
        self.log.configure(state="normal")
        self.log.insert("end", fa(text) + "\n", "rtl")
        self.log.see("end")
        self.log.configure(state="disabled")

    def inspect(self):
        if not self.url.get().strip():
            messagebox.showwarning(fa("لینک لازم است"), fa("لینک ویدئو یا پست را وارد کنید."))
            return
        self.write_log("در حال بررسی لینک...")
        self._set_status("در حال بررسی اطلاعات لینک")

    def start_download(self):
        if self.running:
            return
        if yt_dlp is None:
            messagebox.showerror(fa("وابستگی نصب نیست"), fa("کتابخانه yt-dlp نصب نشده است.\n\npython -m pip install -r requirements.txt"))
            return
        url = self.url.get().strip()
        if not url and self.download_queue:
            url = self.download_queue.pop(0)
        if not url:
            messagebox.showwarning(fa("لینک لازم است"), fa("لینک ویدئو یا پست را وارد کنید."))
            return
        self.running = True
        self.progress.set(0)
        threading.Thread(target=self._download, args=(url,), daemon=True).start()

    def _download(self, url):
        Path(self.destination.get()).mkdir(parents=True, exist_ok=True)
        quality = self.quality.get()
        fmt = "bestaudio/best" if quality == fa("فقط صدا (MP3)") else ("bestvideo[height<=1080]+bestaudio/best" if quality == fa("بهترین کیفیت") else f"bestvideo[height<={quality.replace('p', '')}]+bestaudio/best")
        opts = {"outtmpl": str(Path(self.destination.get()) / "%(title)s.%(ext)s"), "format": fmt, "noplaylist": True, "merge_output_format": "mp4", "quiet": True, "progress_hooks": [self._progress]}
        if self.active_profile and self.active_profile.get("scheme") in {"http", "https", "socks5", "socks5h"}:
            opts["proxy"] = self.active_profile["value"]
            self.events.put(("log", f"اتصال دانلود: {self.active_profile.get('name', 'Manual')}"))
        else:
            self.auto_proxy = self._detect_local_proxy()
            if self.auto_proxy:
                opts["proxy"] = self.auto_proxy[1]
                self.events.put(("log", f"اتصال دانلود: {self.auto_proxy[0]}"))

        if "youtube.com" in url or "youtu.be" in url:
            chrome_profile = Path.home() / ".config" / "google-chrome"
            if chrome_profile.exists():
                opts["cookiesfrombrowser"] = ("chrome", None, None, None)
            node_path = shutil.which("node")
            if node_path:
                opts["js_runtimes"] = {"node": {"path": node_path}}

        if quality == fa("فقط صدا (MP3)"):
            opts.update({"postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}]})
        try:
            self.events.put(("log", "دانلود شروع شد..."))
            with yt_dlp.YoutubeDL(opts) as downloader:
                downloader.download([url])
            self.events.put(("done", "دانلود با موفقیت انجام شد", url))
        except Exception as exc:
            self.events.put(("error", str(exc)))

    def _progress(self, data):
        if data.get("status") == "downloading":
            total = data.get("total_bytes") or data.get("total_bytes_estimate") or 0
            if total:
                downloaded = data.get("downloaded_bytes", 0)
                speed = data.get("speed")
                eta = data.get("eta")
                self.events.put(("progress", downloaded * 100 / total, data.get("_percent_str", ""), downloaded, total, speed, eta))

    def _drain_events(self):
        try:
            while True:
                event = self.events.get_nowait()
                if event[0] == "progress":
                    self.progress.set(event[1]); self._set_status(f"در حال دانلود {event[2]}")
                    self._set_stats(f"حجم: {human_size(event[3])} / {human_size(event[4])}   سرعت: {human_size(event[5])}/s   زمان باقی‌مانده: {human_time(event[6])}")
                elif event[0] == "log": self.write_log(event[1])
                elif event[0] == "done":
                    self.history.append(event[2]); self.progress.set(100); self._set_status(event[1]); self.write_log(event[1]); self.running = False
                    if self.download_queue:
                        self.start_download()
                    else:
                        messagebox.showinfo(fa("تمام شد"), fa(event[1]))
                elif event[0] == "error": self.running = False; self._set_status("دانلود ناموفق بود"); self.write_log("خطا: " + event[1]); messagebox.showerror(fa("خطا در دانلود"), event[1])
        except queue.Empty:
            pass
        self.after(100, self._drain_events)


if __name__ == "__main__":
    DownloadCenter().mainloop()
