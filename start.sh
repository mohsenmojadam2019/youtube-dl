#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
command -v yt-dlp >/dev/null || { echo "yt-dlp is missing."; exit 1; }
command -v ffmpeg >/dev/null || echo "Warning: ffmpeg missing; MP3/merged MP4 may fail."
mkdir -p "$HOME/.cache"
if ! ss -ltn '( sport = :18765 )' | grep -q '127.0.0.1:18765'; then
  nohup python3 "$ROOT/bridge/server.py" >> "$HOME/.cache/download-center.log" 2>&1 </dev/null &
  sleep 1
fi
if [ ! -f "$ROOT/extension/config.js" ]; then
  echo "Companion failed. Check ~/.cache/download-center.log."
  exit 1
fi
echo "Download Center ready at http://127.0.0.1:18765"
echo "Chrome extension folder: $ROOT/extension"
echo "Downloads: $HOME/Downloads/DownloadCenter"
