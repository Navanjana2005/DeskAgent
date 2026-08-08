"""
tools/media_tools.py
Media, YouTube, screen recording, and audio tools (existing 9 migrated + 3 new).

BUG FIX:   play_media now properly imports sys
NEW tools: convert_audio, trim_media, merge_audio_files
"""

import os
import sys
import wave
import time
import threading
import webbrowser
import subprocess
import numpy as np
from typing import Optional
from langchain_core.tools import tool

try:
    import yt_dlp
    HAS_YTDLP = True
except ImportError:
    HAS_YTDLP = False

try:
    import sounddevice as sd
    HAS_SOUNDDEVICE = True
except ImportError:
    HAS_SOUNDDEVICE = False

try:
    import cv2
    import mss
    HAS_MSS = True
except ImportError:
    HAS_MSS = False

try:
    import winsound
    HAS_WINSOUND = True
except ImportError:
    HAS_WINSOUND = False

try:
    from plyer import notification
    HAS_PLYER = True
except ImportError:
    HAS_PLYER = False

try:
    from pydub import AudioSegment
    HAS_PYDUB = True
except ImportError:
    HAS_PYDUB = False


def _play_alert_sound():
    """Cross-platform alert beep."""
    try:
        if os.name == "nt" and HAS_WINSOUND:
            winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
        else:
            print("\a", end="", flush=True)
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────────────────
# EXISTING TOOLS (migrated)
# ─────────────────────────────────────────────────────────────────────────────

@tool
def play_media(file_path: str) -> str:
    """Plays a media file (audio or video) using VLC or the default system player.

    Args:
        file_path: Absolute or relative path to the media file.
    """
    try:
        if not os.path.exists(file_path):
            return f"❌ File not found: {file_path}"
        if os.name == "nt":
            vlc_path = r"C:\Program Files\VideoLAN\VLC\vlc.exe"
            if os.path.exists(vlc_path):
                subprocess.Popen([vlc_path, file_path])
            else:
                os.startfile(file_path)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", file_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            subprocess.Popen(["xdg-open", file_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return f"▶️  Playing: {os.path.basename(file_path)}"
    except Exception as e:
        return f"❌ Error playing media: {e}"


@tool
def search_youtube(query: str, max_results: int = 5) -> str:
    """Searches YouTube and returns video titles and URLs. No API key required.

    Args:
        query: Search keywords.
        max_results: Number of results to return (1–10, default 5).
    """
    if not HAS_YTDLP:
        return "❌ yt-dlp is not installed. Run: pip install yt-dlp"
    max_results = max(1, min(max_results, 10))
    try:
        ydl_opts = {"quiet": True, "extract_flat": True, "playlistend": max_results}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(f"ytsearch{max_results}:{query}", download=False)
            entries = result.get("entries", [])
        if not entries:
            return "No results found."
        lines = []
        for i, entry in enumerate(entries, 1):
            title = entry.get("title", "Unknown")
            vid = entry.get("id", "")
            dur = entry.get("duration", 0)
            dur_str = f"{dur // 60}:{dur % 60:02d}" if dur else "?"
            lines.append(f"{i}. {title} ({dur_str}) | https://youtube.com/watch?v={vid}")
        return "🎬 YouTube Results:\n" + "\n".join(lines)
    except Exception as e:
        return f"❌ Search failed: {e}"


@tool
def play_youtube_video(video_url: str) -> str:
    """Opens a YouTube video in the default web browser.

    Args:
        video_url: Full YouTube URL or video ID.
    """
    try:
        if "youtube.com" not in video_url and "youtu.be" not in video_url:
            video_url = f"https://youtube.com/watch?v={video_url}"
        webbrowser.open(video_url)
        return f"🌐 Opening YouTube: {video_url}"
    except Exception as e:
        return f"❌ Error: {e}"


@tool
def search_youtube_music(query: str, max_results: int = 5) -> str:
    """Searches YouTube Music and returns track titles and URLs.

    Args:
        query: Song/artist search keywords.
        max_results: Number of results (1–10, default 5).
    """
    if not HAS_YTDLP:
        return "❌ yt-dlp is not installed. Run: pip install yt-dlp"
    max_results = max(1, min(max_results, 10))
    try:
        ydl_opts = {"quiet": True, "extract_flat": True, "playlistend": max_results}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(f"ytsearch{max_results}:{query} audio", download=False)
            entries = result.get("entries", [])
        if not entries:
            return "No results found."
        lines = []
        for i, entry in enumerate(entries, 1):
            title = entry.get("title", "Unknown")
            vid = entry.get("id", "")
            lines.append(f"{i}. 🎵 {title} | https://music.youtube.com/watch?v={vid}")
        return "🎧 YouTube Music Results:\n" + "\n".join(lines)
    except Exception as e:
        return f"❌ Search failed: {e}"


@tool
def download_youtube_video(
    url: str,
    output_folder: str = "./downloads",
    audio_only: bool = False,
    video_quality: str = "best",
) -> str:
    """Downloads a YouTube video or audio-only (MP3).

    Args:
        url: YouTube video URL.
        output_folder: Folder to save the file (default './downloads').
        audio_only: If True, downloads MP3 audio only.
        video_quality: Video quality e.g. 'best', 'worst', '720p' (ignored if audio_only).
    """
    if not HAS_YTDLP:
        return "❌ yt-dlp is not installed. Run: pip install yt-dlp"
    try:
        os.makedirs(output_folder, exist_ok=True)
        ydl_opts = {
            "outtmpl": os.path.join(output_folder, "%(title)s.%(ext)s"),
            "quiet": True,
            "no_warnings": True,
        }
        if audio_only:
            ydl_opts["format"] = "bestaudio/best"
            ydl_opts["postprocessors"] = [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }]
        else:
            ydl_opts["format"] = video_quality
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get("title", "Unknown")
            filename = ydl.prepare_filename(info)
        return f"✅ Downloaded: {title}\n📁 Saved to: {filename}"
    except Exception as e:
        return f"❌ Download failed: {e}"


@tool
def record_audio_note(save_path: str, duration: int = 10) -> str:
    """Records audio from the microphone and saves it as a WAV file.

    Args:
        save_path: Path to save the .wav file (e.g., 'note.wav').
        duration: Recording length in seconds (default 10).
    """
    if not HAS_SOUNDDEVICE:
        return "❌ sounddevice not installed. Run: pip install sounddevice"
    try:
        fs, channels = 44100, 2
        print(f"🎙️  Recording for {duration} seconds...")
        recording = sd.rec(int(duration * fs), samplerate=fs, channels=channels, dtype=np.int16)
        sd.wait()
        with wave.open(save_path, "wb") as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(2)
            wf.setframerate(fs)
            wf.writeframes(recording.tobytes())
        size_kb = os.path.getsize(save_path) / 1024
        return f"🎙️  Audio recorded!\n📁 {save_path} ({size_kb:.1f} KB) | {duration}s"
    except Exception as e:
        return f"❌ Recording failed: {e}"


@tool
def get_media_info(file_path: str) -> str:
    """Returns basic info about a media file: size, type, and duration if detectable.

    Args:
        file_path: Path to the media file.
    """
    try:
        if not os.path.exists(file_path):
            return f"❌ File not found: {file_path}"
        size = os.path.getsize(file_path) / (1024 * 1024)
        ext = os.path.splitext(file_path)[1].upper()
        info = f"📄 {os.path.basename(file_path)}\n🗂️  Type: {ext}\n📦 Size: {size:.2f} MB"
        try:
            result = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", file_path],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                duration = float(result.stdout.strip())
                mins, secs = int(duration // 60), int(duration % 60)
                info += f"\n⏱️  Duration: {mins}:{secs:02d}"
        except Exception:
            pass
        return info
    except Exception as e:
        return f"❌ Error: {e}"


class _ScreenRecorder:
    """Internal screen recorder engine using mss + OpenCV."""

    def __init__(self, save_path: str):
        self.save_path = save_path
        self.recording = False
        self._thread: Optional[threading.Thread] = None

    def start(self):
        self.recording = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()

    def _capture_loop(self):
        with mss.mss() as sct:
            monitor = sct.monitors[1]
            width, height = monitor["width"], monitor["height"]
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            out = cv2.VideoWriter(self.save_path, fourcc, 20.0, (width, height))
            while self.recording:
                img = np.array(sct.grab(monitor))
                out.write(cv2.cvtColor(img, cv2.COLOR_BGRA2BGR))
                time.sleep(0.05)
            out.release()

    def stop(self):
        self.recording = False
        if self._thread:
            self._thread.join(timeout=10)


_active_screen_recorder: Optional[_ScreenRecorder] = None


@tool
def start_screen_recording(save_path: str = "screen_recording.mp4") -> str:
    """Starts recording the screen. Call stop_screen_recording() to save.

    Args:
        save_path: Output video file path (default: screen_recording.mp4).
    """
    global _active_screen_recorder
    if not HAS_MSS:
        return "❌ mss and opencv-python required. Run: pip install mss opencv-python"
    try:
        if _active_screen_recorder and _active_screen_recorder.recording:
            return "⚠️  Recording already running. Stop it first."
        _active_screen_recorder = _ScreenRecorder(save_path)
        _active_screen_recorder.start()
        return f"🎥 Screen recording STARTED\n📁 Saving to: {os.path.abspath(save_path)}"
    except Exception as e:
        return f"❌ Failed to start recording: {e}"


@tool
def stop_screen_recording() -> str:
    """Stops the active screen recording and finalizes the video file."""
    global _active_screen_recorder
    try:
        if _active_screen_recorder is None or not _active_screen_recorder.recording:
            return "⚠️  No active screen recording found."
        save_path = _active_screen_recorder.save_path
        _active_screen_recorder.stop()
        _active_screen_recorder = None
        size_mb = os.path.getsize(save_path) / (1024 * 1024) if os.path.exists(save_path) else 0
        return f"🛑 Screen recording STOPPED\n📁 Saved: {save_path} ({size_mb:.1f} MB)"
    except Exception as e:
        return f"❌ Error stopping recording: {e}"


@tool
def take_screenshot(save_path: str) -> str:
    """Takes a screenshot and saves it to the specified path.

    Args:
        save_path: Path where the screenshot will be saved (e.g., 'screen.png').
    """
    try:
        import pyautogui
        screenshot = pyautogui.screenshot()
        screenshot.save(save_path)
        return f"📸 Screenshot saved to {save_path}."
    except Exception as e:
        return f"❌ Error taking screenshot: {e}"


# ─────────────────────────────────────────────────────────────────────────────
# NEW TOOLS
# ─────────────────────────────────────────────────────────────────────────────

@tool
def convert_audio(input_path: str, output_path: str) -> str:
    """Converts an audio file to a different format (MP3, WAV, FLAC, OGG, AAC).

    Args:
        input_path: Path to the source audio file.
        output_path: Path for the output file with new extension (e.g., 'output.mp3').
    """
    if not HAS_PYDUB:
        return "❌ pydub not installed. Run: pip install pydub"
    try:
        audio = AudioSegment.from_file(input_path)
        fmt = os.path.splitext(output_path)[1].lstrip(".").lower()
        if fmt == "mp3":
            audio.export(output_path, format="mp3", bitrate="192k")
        else:
            audio.export(output_path, format=fmt)
        size_mb = os.path.getsize(output_path) / (1024 * 1024)
        return (
            f"✅ Converted audio\n"
            f"📥 Input:  {os.path.basename(input_path)}\n"
            f"📤 Output: {output_path} ({size_mb:.2f} MB)"
        )
    except Exception as e:
        return f"❌ Error converting audio: {e}"


@tool
def trim_media(input_path: str, output_path: str, start_sec: float, end_sec: float) -> str:
    """Trims an audio file to a specified time range.

    Args:
        input_path: Path to the source audio file.
        output_path: Path to save the trimmed file.
        start_sec: Start time in seconds (e.g., 30.5).
        end_sec: End time in seconds (e.g., 90.0).
    """
    if not HAS_PYDUB:
        return "❌ pydub not installed. Run: pip install pydub"
    try:
        audio = AudioSegment.from_file(input_path)
        start_ms = int(start_sec * 1000)
        end_ms = int(end_sec * 1000)
        if end_ms > len(audio):
            end_ms = len(audio)
        trimmed = audio[start_ms:end_ms]
        fmt = os.path.splitext(output_path)[1].lstrip(".").lower() or "mp3"
        trimmed.export(output_path, format=fmt)
        duration = (end_ms - start_ms) / 1000
        return (
            f"✅ Trimmed audio: {start_sec}s → {end_sec}s ({duration:.1f}s)\n"
            f"📁 Saved to: {output_path}"
        )
    except Exception as e:
        return f"❌ Error trimming audio: {e}"


@tool
def merge_audio_files(input_paths: str, output_path: str) -> str:
    """Concatenates multiple audio files into a single file.

    Args:
        input_paths: Comma-separated list of audio file paths to merge (in order).
        output_path: Path to save the merged audio file.
    """
    if not HAS_PYDUB:
        return "❌ pydub not installed. Run: pip install pydub"
    try:
        paths = [p.strip() for p in input_paths.split(",")]
        combined = AudioSegment.empty()
        for path in paths:
            if not os.path.exists(path):
                return f"❌ File not found: {path}"
            combined += AudioSegment.from_file(path)
        fmt = os.path.splitext(output_path)[1].lstrip(".").lower() or "mp3"
        combined.export(output_path, format=fmt)
        duration = len(combined) / 1000
        size_mb = os.path.getsize(output_path) / (1024 * 1024)
        return (
            f"✅ Merged {len(paths)} audio files\n"
            f"⏱️  Total duration: {duration:.1f}s\n"
            f"📁 Saved to: {output_path} ({size_mb:.2f} MB)"
        )
    except Exception as e:
        return f"❌ Error merging audio: {e}"
