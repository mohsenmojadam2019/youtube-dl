# Chrome extension — Download Center

The Chrome extension integrates with a local, loopback-only Python companion and yt-dlp.

## Install

1. Install yt-dlp and ffmpeg and confirm both commands are available.
2. From this repository, run: bash start.sh
3. Open chrome://extensions in Chrome; enable Developer mode.
4. Choose Load unpacked and select the extension folder.
5. Click the Download Center icon. Paste a media URL and choose quality or MP3.
6. Downloads are saved in ~/Downloads/DownloadCenter.

The companion listens on 127.0.0.1:18765, validates Origin, and requires a
random token stored outside the Git repository. The extension/config.js file
is generated locally and must never be committed.

## Limitations

- Use only for media that you have permission to download.
- Supported sites depend on current yt-dlp extractors and site permissions.
- DRM-protected content, private media, and login bypass are not supported.
- Chrome's scan feature can detect HTML video/audio and direct media links;
  blob-backed streams cannot always be inspected.
- Audio extraction and merged video formats require ffmpeg.
- Installing locally as an unpacked extension is supported; Web Store rules vary.
