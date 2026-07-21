"""
ffmpeg_manager.py
Detects, downloads, and automatically installs ffmpeg / ffprobe.

If ffmpeg is already available (either on the system PATH or in this
app's local data folder), that copy is used and nothing is downloaded.
Otherwise, a static build matching the user's OS is downloaded,
extracted, and installed into the app's local data folder.
"""

import os
import shutil
import platform
import tarfile
import zipfile
import tempfile
import stat
import urllib.request
from pathlib import Path

APP_DIR_NAME = ".video_shrinker"


def get_app_data_dir() -> Path:
    """Application data folder inside the user's home directory."""
    d = Path.home() / APP_DIR_NAME
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_local_bin_dir() -> Path:
    d = get_app_data_dir() / "ffmpeg_bin"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _exe_name(base: str) -> str:
    return f"{base}.exe" if platform.system() == "Windows" else base


def _find_local_binaries():
    """Returns paths if ffmpeg/ffprobe were already installed locally by this app."""
    bin_dir = get_local_bin_dir()
    ffmpeg_path = bin_dir / _exe_name("ffmpeg")
    ffprobe_path = bin_dir / _exe_name("ffprobe")
    if ffmpeg_path.exists() and ffprobe_path.exists():
        return str(ffmpeg_path), str(ffprobe_path)
    return None, None


def _find_system_binaries():
    ffmpeg_path = shutil.which("ffmpeg")
    ffprobe_path = shutil.which("ffprobe")
    if ffmpeg_path and ffprobe_path:
        return ffmpeg_path, ffprobe_path
    return None, None


def find_ffmpeg():
    """
    Looks for ffmpeg and ffprobe, first in this app's local folder, then on PATH.
    Returns (ffmpeg_path, ffprobe_path) or (None, None) if not found.
    """
    ffmpeg_path, ffprobe_path = _find_local_binaries()
    if ffmpeg_path:
        return ffmpeg_path, ffprobe_path

    return _find_system_binaries()


def is_ffmpeg_available() -> bool:
    ffmpeg_path, ffprobe_path = find_ffmpeg()
    return bool(ffmpeg_path and ffprobe_path)


def _download_url(url: str, dest_path: Path, on_progress=None):
    """Downloads a file while reporting progress as a 0..1 fraction."""
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as response, open(dest_path, "wb") as out_file:
        total = response.length or int(response.headers.get("Content-Length", 0) or 0)
        downloaded = 0
        chunk_size = 1024 * 256
        while True:
            chunk = response.read(chunk_size)
            if not chunk:
                break
            out_file.write(chunk)
            downloaded += len(chunk)
            if on_progress and total:
                on_progress(min(downloaded / total, 1.0))


def _extract_archive(archive_path: Path, extract_to: Path):
    if str(archive_path).endswith(".zip"):
        with zipfile.ZipFile(archive_path, "r") as z:
            z.extractall(extract_to)
    elif str(archive_path).endswith((".tar.xz", ".tar.gz", ".tgz")):
        with tarfile.open(archive_path, "r:*") as t:
            t.extractall(extract_to)
    else:
        raise RuntimeError(f"Unknown archive format: {archive_path}")


def _collect_binaries_from(folder: Path, bin_dir: Path):
    """After extraction, locates the ffmpeg/ffprobe executables and copies them into bin_dir."""
    wanted = {_exe_name("ffmpeg"), _exe_name("ffprobe")}
    found = {}
    for root, _dirs, files in os.walk(folder):
        for f in files:
            if f in wanted and f not in found:
                found[f] = Path(root) / f
        if len(found) == len(wanted):
            break

    if len(found) < len(wanted):
        raise RuntimeError("Could not find the ffmpeg/ffprobe executables inside the archive.")

    for name, src in found.items():
        dst = bin_dir / name
        shutil.copy2(src, dst)
        if platform.system() != "Windows":
            st = os.stat(dst)
            os.chmod(dst, st.st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)


def _platform_targets():
    """
    Returns the download target(s) for the current OS.
    Output: list of dicts {"url": ..., "kind": "ffmpeg"/"ffprobe"/"both"}.
    Most platforms ship a single archive containing both binaries,
    except macOS where ffmpeg and ffprobe are separate downloads.
    """
    system = platform.system()
    machine = platform.machine().lower()

    if system == "Windows":
        return [{"url": "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip", "kind": "both"}]

    if system == "Linux":
        if "arm" in machine or "aarch64" in machine:
            url = "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-arm64-static.tar.xz"
        else:
            url = "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz"
        return [{"url": url, "kind": "both"}]

    if system == "Darwin":
        # macOS: ffmpeg and ffprobe are distributed as two separate archives
        return [
            {"url": "https://evermeet.cx/ffmpeg/getrelease/ffmpeg/zip", "kind": "ffmpeg"},
            {"url": "https://evermeet.cx/ffmpeg/getrelease/ffprobe/zip", "kind": "ffprobe"},
        ]

    raise RuntimeError(f"The '{system}' operating system is not currently supported.")


def download_and_install(status_callback=None, progress_callback=None):
    """
    Downloads and installs ffmpeg/ffprobe automatically for the current OS.
    status_callback(text): for showing status text
    progress_callback(fraction): for a progress bar (0..1)
    Returns (ffmpeg_path, ffprobe_path) on success.
    """
    def report_status(msg):
        if status_callback:
            status_callback(msg)

    def report_progress(frac):
        if progress_callback:
            progress_callback(frac)

    targets = _platform_targets()
    bin_dir = get_local_bin_dir()

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        n = len(targets)
        for i, target in enumerate(targets):
            url = target["url"]
            report_status(f"Downloading ({i + 1}/{n})...")

            def _on_dl_progress(frac, i=i, n=n):
                report_progress((i + frac) / n)

            archive_ext = ".zip" if url.endswith("zip") or "zip" in url else ".tar.xz"
            archive_path = tmp_path / f"part_{i}{archive_ext}"
            _download_url(url, archive_path, on_progress=_on_dl_progress)

            report_status("Extracting files...")
            extract_dir = tmp_path / f"extract_{i}"
            extract_dir.mkdir(exist_ok=True)
            _extract_archive(archive_path, extract_dir)

            if target["kind"] == "both":
                _collect_binaries_from(extract_dir, bin_dir)
            else:
                # Single binary (evermeet.cx) - usually sits at the archive root
                exe_name = _exe_name(target["kind"])
                candidates = list(extract_dir.rglob(target["kind"])) + list(extract_dir.rglob(exe_name))
                if not candidates:
                    raise RuntimeError(f"Could not find the {target['kind']} binary in the archive.")
                dst = bin_dir / exe_name
                shutil.copy2(candidates[0], dst)
                st = os.stat(dst)
                os.chmod(dst, st.st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

        report_progress(1.0)
        report_status("Installed successfully")

    ffmpeg_path, ffprobe_path = _find_local_binaries()
    if not ffmpeg_path:
        raise RuntimeError("ffmpeg could not be found after installation.")
    return ffmpeg_path, ffprobe_path
