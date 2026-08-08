import subprocess

vlc_path = r"C:\Program Files\VideoLAN\VLC\vlc.exe"
video_path = r"C:\Users\malmi\Videos\Screen Recordings\Screen Recording 2026-02-16 141647.mp4"

subprocess.Popen([vlc_path, video_path])