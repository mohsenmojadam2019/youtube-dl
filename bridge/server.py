#!/usr/bin/env python3
"""Loopback-only companion for Download Center Chrome extension."""
import json
import os
import re
import secrets
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

BASE = Path(__file__).resolve().parents[1]
SETTINGS = Path.home() / ".config/download-center"
PORT = 18765
JOBS = {}
LOCK = threading.RLock()
SLOTS = threading.BoundedSemaphore(2)
ORIGIN = re.compile(r"chrome-extension://[a-p]{32}$")
BIN = os.getenv("YTDLP_BIN", "yt-dlp")

def setup():
    SETTINGS.mkdir(parents=True, exist_ok=True)
    secret = SETTINGS / "token"
    if not secret.exists():
        secret.write_text(secrets.token_urlsafe(32))
        secret.chmod(0o600)
    token = secret.read_text().strip()
    (BASE / "extension/config.js").write_text("const BRIDGE_TOKEN = " + json.dumps(token) + ";\n")
    return token

TOKEN = ""
DEST = Path.home() / "Downloads/DownloadCenter"

def check_url(value):
    if not isinstance(value, str) or len(value) > 4096:
        raise ValueError("لینک معتبر وارد کنید")
    part = urlsplit(value)
    if part.scheme not in ("http", "https") or not part.hostname:
        raise ValueError("لینک باید با http یا https شروع شود")
    if part.hostname.lower() in ("localhost", "127.0.0.1", "::1"):
        raise ValueError("آدرس محلی مجاز نیست")
    return value

def inspect(value):
    url = check_url(value)
    p = subprocess.run([BIN, "-J", "--no-playlist", "--skip-download", "--no-warnings", "--", url],
                       capture_output=True, text=True, timeout=55)
    if p.returncode:
        raise ValueError((p.stderr or "لینک پشتیبانی نمی‌شود")[-500:])
    d = json.loads(p.stdout)
    sizes = sorted({f["height"] for f in d.get("formats", [])
                    if isinstance(f.get("height"), int) and f.get("vcodec") != "none"}, reverse=True)
    return {"title": d.get("title", ""), "site": d.get("extractor_key", ""),
            "duration": d.get("duration"), "heights": sizes[:12]}

def status(jid, **update):
    with LOCK:
        JOBS[jid].update(update)

def worker(jid, url, quality, mode):
    with SLOTS:
        with LOCK:
            if JOBS[jid]["state"] == "cancelled":
                return
        status(jid, state="running")
        cmd = [BIN, "--no-playlist", "--newline", "--no-warnings",
               "--paths", str(DEST), "-o", "%(title).150B [%(id)s].%(ext)s",
               "--progress-template", "download:%(progress._percent_str)s",
               "--no-overwrites"]
        if mode == "mp3":
            cmd += ["-f", "bestaudio/best", "-x", "--audio-format", "mp3"]
        else:
            q = "bv*+ba/b" if quality == "best" else (
                "bv*[height<=" + quality + "]+ba/b[height<=" + quality + "]/bv*+ba/b")
            cmd += ["-f", q, "--merge-output-format", "mp4"]
        cmd += ["--", url]
        proc = None
        tail = []
        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    text=True, bufsize=1)
            status(jid, proc=proc)
            for line in proc.stdout:
                tail.append(line.strip())
                tail = tail[-8:]
                match = re.search(r"(\d+(?:\.\d+)?)\s*%", line)
                if match:
                    status(jid, progress=min(100, float(match.group(1))))
            code = proc.wait()
            if JOBS[jid]["state"] == "cancelled":
                return
            if code:
                status(jid, state="error", error="\n".join(tail)[-700:])
            else:
                status(jid, state="done", progress=100)
        except Exception as exc:
            status(jid, state="error", error=str(exc))
        finally:
            status(jid, proc=None)

def queue(data):
    url = check_url(data.get("url"))
    mode = data.get("mode", "video")
    quality = str(data.get("quality", "best"))
    if mode not in ("video", "mp3") or quality not in ("best", "1080", "720", "480", "360"):
        raise ValueError("فرمت یا کیفیت نامعتبر")
    with LOCK:
        if sum(j["state"] in ("running", "queued") for j in JOBS.values()) >= 8:
            raise ValueError("صف دانلود پر است")
        jid = secrets.token_hex(8)
        JOBS[jid] = {"id": jid, "url": url, "mode": mode, "quality": quality,
                     "state": "queued", "progress": 0, "error": "",
                     "created": time.time(), "proc": None}
        threading.Thread(target=worker, args=(jid, url, quality, mode), daemon=True).start()
    return {"id": jid}

class Handler(BaseHTTPRequestHandler):
    def trusted(self):
        origin = self.headers.get("Origin", "")
        ok_origin = not origin or bool(ORIGIN.fullmatch(origin))
        ok_token = secrets.compare_digest(self.headers.get("X-Download-Token", ""), TOKEN)
        if not (ok_origin and ok_token):
            print("BRIDGE_DENY", "origin=", repr(origin), "origin_ok=", ok_origin, "token_ok=", ok_token, flush=True)
        return ok_origin and ok_token

    def reply(self, code, data):
        raw = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(code)
        origin = self.headers.get("Origin", "")
        if ORIGIN.fullmatch(origin):
            self.send_header("Access-Control-Allow-Origin", origin)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def do_OPTIONS(self):
        origin = self.headers.get("Origin", "")
        if not ORIGIN.fullmatch(origin):
            return self.reply(403, {"error": "Forbidden"})
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", origin)
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Download-Token")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.end_headers()

    def do_GET(self):
        if not self.trusted():
            return self.reply(403, {"error": "Forbidden"})
        if self.path == "/api/health":
            return self.reply(200, {"ok": True, "folder": str(DEST)})
        if self.path == "/api/jobs":
            with LOCK:
                jobs = [{k: v for k, v in j.items() if k != "proc"}
                        for j in sorted(JOBS.values(), key=lambda x: x["created"], reverse=True)]
            return self.reply(200, {"jobs": jobs[:20]})
        return self.reply(404, {"error": "Not found"})

    def do_POST(self):
        if not self.trusted():
            return self.reply(403, {"error": "Forbidden"})
        try:
            n = int(self.headers.get("Content-Length", "0"))
            if not 0 < n <= 8192:
                raise ValueError("اندازه درخواست نامعتبر")
            data = json.loads(self.rfile.read(n))
            if self.path == "/api/inspect":
                return self.reply(200, inspect(data.get("url")))
            if self.path == "/api/download":
                return self.reply(200, queue(data))
            if self.path == "/api/cancel":
                with LOCK:
                    j = JOBS.get(data.get("id"))
                    if not j:
                        raise ValueError("دانلود پیدا نشد")
                    if j["state"] in ("queued", "running"):
                        j["state"] = "cancelled"
                        if j["proc"]:
                            j["proc"].terminate()
                return self.reply(200, {"ok": True})
            return self.reply(404, {"error": "Not found"})
        except (ValueError, json.JSONDecodeError) as exc:
            return self.reply(400, {"error": str(exc)})
        except subprocess.TimeoutExpired:
            return self.reply(504, {"error": "زمان بررسی لینک تمام شد"})
        except Exception as exc:
            return self.reply(500, {"error": str(exc)})

if __name__ == "__main__":
    TOKEN = setup()
    DEST.mkdir(parents=True, exist_ok=True)
    print("Download Center listening on 127.0.0.1:" + str(PORT), flush=True)
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
