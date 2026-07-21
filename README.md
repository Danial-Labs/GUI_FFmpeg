# GUI_FFmpeg

<div align="center">

# 🎬 GUI_FFmpeg

**A beautiful, beginner-friendly desktop app for compressing videos — powered by ffmpeg.**

No command line. No manual ffmpeg install. Just pick a video, choose how much smaller you want it, and go.

[![Python](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)](#)
[![License](https://img.shields.io/badge/license-MIT-green)](#license)
[![Made by](https://img.shields.io/badge/made%20by-%40DanialLabs-7C6FF0)](https://t.me/DanialLabs)

</div>

---

## ✨ Features

| | |
|---|---|
| 🧩 **Zero-setup ffmpeg** | On first launch, GUI_FFmpeg checks for ffmpeg and, if it's missing, downloads and installs it automatically — one click, no terminal needed. |
| 🎯 **Two compression modes** | **Reduce by percentage** (tell it how much smaller you want the file) or **Keep quality** (CRF-based H.265/H.264 encoding that shrinks size while preserving detail). |
| 📊 **Live feedback** | See resolution, duration, codec and size before you start, then watch a live progress bar and full ffmpeg log while it runs. |
| 🎨 **Modern UI** | Built with CustomTkinter — clean cards, light/dark themes, and a scrollable layout that adapts to any window size. |
| 📦 **Ships as a single .exe** | Comes with a ready-made PyInstaller setup, so you can build a standalone executable and distribute it via GitHub Releases — no Python required on the user's machine. |

---

## 🚀 Getting started

### Option A — Run from source

```bash
git clone https://github.com/USERNAME/GUI_FFmpeg.git
cd GUI_FFmpeg
pip install -r requirements.txt
python main.py
```

That's it — ffmpeg is handled automatically the first time you run the app.

### Option B — Download a prebuilt executable

Check the [Releases](../../releases) page for a ready-to-run `.exe` (Windows) or binary (macOS/Linux) — no installation required.

---

## 🧭 How to use it

1. **Launch the app.** If ffmpeg isn't already on your system, click **"Download & install ffmpeg"** and wait a moment.
2. **Browse** for the video you want to shrink.
3. Pick a mode:
   - **Reduce by percentage** — drag the slider to choose how much smaller the output should be (e.g. 50%).
   - **Keep quality** — pick a codec (H.265 for smaller files, H.264 for wider compatibility) and a quality level.
4. *(Optional)* Choose a custom output location.
5. Hit **Start compressing** and watch the progress bar. When it's done, you can jump straight to the output folder.

---

## ⚙️ Under the hood

- **ffmpeg sources** (static builds, no admin rights required):
  - Windows → [gyan.dev](https://www.gyan.dev/ffmpeg/builds/)
  - Linux → [johnvansickle.com](https://johnvansickle.com/ffmpeg/)
  - macOS → [evermeet.cx](https://evermeet.cx/ffmpeg/)
- Installed binaries live in `~/.video_shrinker/` and are reused on every launch.
- If your network can't reach those hosts, install ffmpeg manually and put it on your system `PATH` — GUI_FFmpeg will detect it automatically, no download needed.

---

## 🙋 Troubleshooting

- **"ffmpeg not found" after install** — check your internet connection and firewall; the app needs to reach the download hosts listed above.
- **Antivirus flags the .exe** — this is a common false positive with PyInstaller-built apps, especially unsigned ones. Building it yourself from source (rather than downloading a stranger's binary) avoids most trust concerns.
- **Output looks too compressed** — try "Keep quality" mode instead of a high percentage reduction, or lower the compression level.

---

## 🤝 Contributing

Issues and pull requests are welcome. If you run into a bug or have an idea for a feature, feel free to open an issue.

## 📄 License

MIT — do whatever you'd like with this, credit is appreciated but not required.

## 💬 Author

Made by **[@DanialLabs](https://t.me/DanialLabs)**
