import os
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path

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
        self.events = queue.Queue()
        self.running = False
        self.destination = tk.StringVar(value=str(Path.home() / "Downloads"))
        self.url = tk.StringVar()
        self.quality = tk.StringVar(value="بهترین کیفیت")
        self.cookies = tk.StringVar()
        self.status = tk.StringVar(value="آماده دریافت لینک شما")
        self.stats = tk.StringVar(value="حجم: —   سرعت: —   زمان باقی‌مانده: —")
        self.progress = tk.DoubleVar(value=0)
        self._setup_style()
        self._build_ui()
        self.after(100, self._drain_events)

    def _setup_style(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TProgressbar", troughcolor="#22334d", background=ACCENT, borderwidth=0, thickness=12)
        style.configure("Treeview", background=PANEL, fieldbackground=PANEL, foreground=TEXT, rowheight=34, borderwidth=0)
        style.configure("Treeview.Heading", background=PANEL_2, foreground=MUTED, relief="flat")
        style.map("Treeview", background=[("selected", "#234879")])

    def _label(self, parent, text, size=11, color=TEXT, bold=False):
        return tk.Label(parent, text=text, bg=parent.cget("bg"), fg=color,
                        font=("Segoe UI", size, "bold" if bold else "normal"))

    def _button(self, parent, text, command, primary=False):
        return tk.Button(parent, text=text, command=command, bg=ACCENT if primary else PANEL_2,
                         fg="white", activebackground="#6da2ff", activeforeground="white",
                         relief="flat", borderwidth=0, padx=18, pady=10,
                         font=("Segoe UI", 10, "bold"), cursor="hand2")

    def _build_ui(self):
        header = tk.Frame(self, bg=BG)
        header.pack(fill="x", padx=34, pady=(28, 12))
        tk.Label(header, text="⬇", bg=ACCENT, fg="white", width=3, height=1,
                 font=("Segoe UI", 22, "bold")).pack(side="right", padx=(0, 12))
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
                         relief="flat", justify="right", font=("Segoe UI", 12))
        entry.pack(side="right", fill="x", expand=True, ipady=12, padx=(0, 8))
        entry.focus_set()
        self._button(row, "چسباندن", self.paste_url).pack(side="right")

        options = tk.Frame(main, bg=BG)
        options.pack(fill="x", pady=16)
        quality = tk.Frame(options, bg=PANEL, padx=18, pady=16)
        quality.pack(side="right", fill="both", expand=True, padx=(8, 0))
        self._label(quality, "کیفیت دانلود", 10, MUTED, True).pack(anchor="e")
        ttk.Combobox(quality, textvariable=self.quality, values=["بهترین کیفیت", "1080p", "720p", "480p", "فقط صدا (MP3)"], state="readonly", justify="right").pack(fill="x", pady=(8, 0), ipady=5)
        folder = tk.Frame(options, bg=PANEL, padx=18, pady=16)
        folder.pack(side="right", fill="both", expand=True, padx=(0, 8))
        self._label(folder, "مسیر ذخیره‌سازی", 10, MUTED, True).pack(anchor="e")
        frow = tk.Frame(folder, bg=PANEL)
        frow.pack(fill="x", pady=(8, 0))
        self._button(frow, "انتخاب", self.choose_folder).pack(side="left")
        tk.Entry(frow, textvariable=self.destination, bg="#1d2c43", fg=TEXT, relief="flat", justify="right").pack(side="right", fill="x", expand=True, ipady=8, padx=(0, 8))

        bottom = tk.Frame(main, bg=BG)
        bottom.pack(fill="both", expand=True)
        left = tk.Frame(bottom, bg=PANEL, padx=18, pady=18)
        left.pack(side="left", fill="both", expand=True, padx=(8, 0))
        self._label(left, "صف دانلود", 15, TEXT, True).pack(anchor="e")
        self.progress_bar = ttk.Progressbar(left, variable=self.progress, maximum=100)
        self.progress_bar.pack(fill="x", pady=(18, 8))
        self._label(left, "آماده دریافت لینک شما", 10, MUTED).pack(anchor="e")
        self.status_label = self._label(left, self.status.get(), 11, TEXT)
        self.status_label.pack(anchor="e", pady=(4, 18))
        self.stats_label = self._label(left, self.stats.get(), 10, MUTED)
        self.stats_label.pack(anchor="e", pady=(0, 14))
        self._button(left, "شروع دانلود", self.start_download, primary=True).pack(fill="x")
        self._button(left, "پاک‌کردن صف", self.clear_log).pack(fill="x", pady=(8, 0))

        right = tk.Frame(bottom, bg=PANEL, padx=18, pady=18)
        right.pack(side="right", fill="both", expand=True, padx=(0, 8))
        self._label(right, "گزارش فعالیت", 15, TEXT, True).pack(anchor="e")
        self.log = tk.Text(right, bg="#0e1727", fg=MUTED, relief="flat", height=10, wrap="word", state="disabled", font=("Consolas", 9))
        self.log.pack(fill="both", expand=True, pady=(12, 0))
        self.write_log("برنامه آماده است. یک لینک وارد کنید.")

    def paste_url(self):
        try:
            self.url.set(self.clipboard_get())
        except tk.TclError:
            self.status.set("متنی در کلیپ‌بورد نیست")

    def choose_folder(self):
        folder = filedialog.askdirectory(initialdir=self.destination.get())
        if folder:
            self.destination.set(folder)

    def clear_log(self):
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")
        self.progress.set(0)
        self.stats.set("حجم: —   سرعت: —   زمان باقی‌مانده: —")

    def write_log(self, text):
        self.log.configure(state="normal")
        self.log.insert("end", text + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def inspect(self):
        if not self.url.get().strip():
            messagebox.showwarning("لینک لازم است", "لینک ویدئو یا پست را وارد کنید.")
            return
        self.write_log("در حال بررسی لینک...")
        self.status.set("در حال بررسی اطلاعات لینک")

    def start_download(self):
        if self.running:
            return
        if yt_dlp is None:
            messagebox.showerror("وابستگی نصب نیست", "کتابخانه yt-dlp نصب نشده است.\n\npython -m pip install -r requirements.txt")
            return
        url = self.url.get().strip()
        if not url:
            messagebox.showwarning("لینک لازم است", "لینک ویدئو یا پست را وارد کنید.")
            return
        self.running = True
        self.progress.set(0)
        threading.Thread(target=self._download, args=(url,), daemon=True).start()

    def _download(self, url):
        Path(self.destination.get()).mkdir(parents=True, exist_ok=True)
        quality = self.quality.get()
        fmt = "bestaudio/best" if quality == "فقط صدا (MP3)" else ("bestvideo[height<=1080]+bestaudio/best" if quality == "بهترین کیفیت" else f"bestvideo[height<={quality.replace('p', '')}]+bestaudio/best")
        opts = {"outtmpl": str(Path(self.destination.get()) / "%(title)s.%(ext)s"), "format": fmt, "noplaylist": True, "merge_output_format": "mp4", "quiet": True, "progress_hooks": [self._progress]}
        if quality == "فقط صدا (MP3)":
            opts.update({"postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}]})
        try:
            self.events.put(("log", "دانلود شروع شد..."))
            with yt_dlp.YoutubeDL(opts) as downloader:
                downloader.download([url])
            self.events.put(("done", "دانلود با موفقیت انجام شد"))
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
                    self.progress.set(event[1]); self.status.set(f"در حال دانلود {event[2]}")
                    self.stats.set(f"حجم: {human_size(event[3])} / {human_size(event[4])}   سرعت: {human_size(event[5])}/s   زمان باقی‌مانده: {human_time(event[6])}")
                elif event[0] == "log": self.write_log(event[1])
                elif event[0] == "done": self.running = False; self.progress.set(100); self.status.set(event[1]); self.write_log(event[1]); messagebox.showinfo("تمام شد", event[1])
                elif event[0] == "error": self.running = False; self.status.set("دانلود ناموفق بود"); self.write_log("خطا: " + event[1]); messagebox.showerror("خطا در دانلود", event[1])
        except queue.Empty:
            pass
        self.after(100, self._drain_events)


if __name__ == "__main__":
    DownloadCenter().mainloop()
