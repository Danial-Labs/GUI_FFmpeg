"""
compressor.py
Video analysis and compression logic built on top of ffmpeg/ffprobe.
"""

import json
import subprocess
import re
import os
import platform

CREATE_NO_WINDOW = 0x08000000 if platform.system() == "Windows" else 0


def _popen_kwargs():
    kwargs = {}
    if platform.system() == "Windows":
        kwargs["creationflags"] = CREATE_NO_WINDOW
    return kwargs


def get_video_info(ffprobe_path: str, video_path: str) -> dict:
    """Reads duration, size, resolution, bitrate and codec info via ffprobe."""
    cmd = [
        ffprobe_path, "-v", "quiet", "-print_format", "json",
        "-show_format", "-show_streams", video_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, **_popen_kwargs())
    if result.returncode != 0:
        raise RuntimeError(f"Failed to read video info:\n{result.stderr}")

    data = json.loads(result.stdout)
    fmt = data.get("format", {})
    video_stream = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), {})
    audio_stream = next((s for s in data.get("streams", []) if s.get("codec_type") == "audio"), {})

    duration = float(fmt.get("duration", 0) or 0)
    size_bytes = int(fmt.get("size", 0) or os.path.getsize(video_path))

    return {
        "duration": duration,
        "size_bytes": size_bytes,
        "width": video_stream.get("width"),
        "height": video_stream.get("height"),
        "video_codec": video_stream.get("codec_name"),
        "audio_codec": audio_stream.get("codec_name"),
        "fps": _parse_frame_rate(video_stream.get("r_frame_rate")),
        "bit_rate": int(fmt.get("bit_rate", 0) or 0),
    }


def _parse_frame_rate(rate_str):
    if not rate_str:
        return None
    try:
        num, den = rate_str.split("/")
        den = float(den)
        return round(float(num) / den, 2) if den else None
    except Exception:
        return None


# ---------- ffmpeg command builders ----------

AUDIO_BITRATE_BPS = 128_000  # assumed output audio bitrate


def build_percent_mode_cmd(ffmpeg_path, input_path, output_path, info, percent, preset="medium"):
    """
    "Reduce size by percentage" mode: the video bitrate is calculated so the
    resulting file size is roughly the requested percentage smaller than the original.
    """
    duration = max(info["duration"], 0.1)
    original_bits = info["size_bytes"] * 8
    target_bits = original_bits * (1 - percent / 100)
    target_bitrate = int(target_bits / duration) - AUDIO_BITRATE_BPS
    target_bitrate = max(target_bitrate, 100_000)  # 100 kbps floor

    return [
        ffmpeg_path, "-y", "-i", input_path,
        "-c:v", "libx264", "-preset", preset,
        "-b:v", str(target_bitrate),
        "-maxrate", str(int(target_bitrate * 1.5)),
        "-bufsize", str(int(target_bitrate * 2)),
        "-c:a", "aac", "-b:a", "128k",
        "-movflags", "+faststart",
        "-progress", "pipe:1", "-nostats",
        output_path,
    ]


def build_quality_mode_cmd(ffmpeg_path, input_path, output_path, crf, codec="libx265", preset="medium"):
    """
    "Keep quality constant" mode: CRF-based encoding with a more efficient
    codec (H.265 by default) keeps visual quality close to the source while
    the file size naturally shrinks.
    """
    cmd = [
        ffmpeg_path, "-y", "-i", input_path,
        "-c:v", codec, "-crf", str(crf), "-preset", preset,
        "-c:a", "aac", "-b:a", "128k",
        "-movflags", "+faststart",
        "-progress", "pipe:1", "-nostats",
        output_path,
    ]
    if codec == "libx265":
        # Tag as hvc1 for better compatibility with players (e.g. QuickTime/Safari)
        idx = cmd.index(output_path)
        cmd[idx:idx] = ["-tag:v", "hvc1"]
    return cmd


TIME_RE = re.compile(r"out_time_ms=(\d+)")


def run_ffmpeg_with_progress(cmd, duration_sec, on_progress=None, on_log=None):
    """
    Runs ffmpeg and reports progress (0..1) by parsing the -progress output.
    on_progress(fraction)
    on_log(line)
    """
    process = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, bufsize=1, universal_newlines=True, **_popen_kwargs(),
    )

    for line in process.stdout:
        line = line.strip()
        if on_log and line:
            on_log(line)

        match = TIME_RE.search(line)
        if match and duration_sec > 0:
            out_time_sec = int(match.group(1)) / 1_000_000
            fraction = min(out_time_sec / duration_sec, 1.0)
            if on_progress:
                on_progress(fraction)

        if line.startswith("progress=") and "end" in line:
            if on_progress:
                on_progress(1.0)

    process.wait()
    if process.returncode != 0:
        raise RuntimeError("ffmpeg exited with an error. Check the log for details.")


def format_size(num_bytes: float) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if abs(num_bytes) < 1024:
            return f"{num_bytes:.1f} {unit}"
        num_bytes /= 1024
    return f"{num_bytes:.1f} TB"


def format_duration(seconds: float) -> str:
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"
