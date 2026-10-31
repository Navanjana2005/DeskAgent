import os
import subprocess
import psutil
from langchain_core.tools import tool
import webbrowser
from AppOpener import open as launch_app, close as terminate_app
import datetime 
import time
import ctypes
import shutil
import requests
import pyautogui
import wave
import json
import threading
import numpy as np
from typing import Optional

try:
    from firecrawl import Firecrawl
except ImportError:
    Firecrawl = None


try:
    import yt_dlp
    HAS_YTDLP = True
except ImportError:
    HAS_YTDLP = False

try:
    import speedtest
    HAS_SPEEDTEST = True
except ImportError:
    HAS_SPEEDTEST = False

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
    from plyer import notification
    HAS_PLYER = True
except ImportError:
    HAS_PLYER = False

try:
    import winsound
    HAS_WINSOUND = True
except ImportError:
    HAS_WINSOUND = False

try:
    import pygame
    HAS_PYGAME = True
except ImportError:
    HAS_PYGAME = False

FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY")
HAS_FIRECRAWL = Firecrawl is not None and bool(FIRECRAWL_API_KEY)
firecrawl = Firecrawl(api_key=FIRECRAWL_API_KEY) if HAS_FIRECRAWL else None

MAX_CHARS_PER_PAGE = 3000


def _dangerous_tool_blocked(action: str) -> str | None:
    if os.getenv("ALLOW_DANGEROUS_TOOLS", "0") == "1":
        return None
    return (
        f"⛔ {action} is disabled. Set ALLOW_DANGEROUS_TOOLS=1 "
        "in your environment to enable it."
    )


@tool
def app_opener(app_name: str) -> str:
    """
    Opens the specified application by name (e.g. 'notepad', 'chrome', 'whatsapp').
    Uses fuzzy matching, so exact executable names aren't required.
    """
    try:
        launch_app(app_name, match_closest=True, output=False, throw_error=True)
        return f"{app_name} has been opened successfully."
    except Exception as e:
        return f"An error occurred while trying to open {app_name}: {e}"


@tool
def app_closer(app_name: str) -> str:
    """
    Closes the specified application by name.
    """
    try:
        terminate_app(app_name, match_closest=True, output=False, throw_error=True)
        return f"{app_name} has been closed successfully."
    except Exception as e:
        return f"An error occurred while trying to close {app_name}: {e}"

@tool
def get_system_stats() -> str:
    """Return current CPU usage, RAM usage, and battery percentage."""
    cpu = psutil.cpu_percent(interval=1)
    ram = psutil.virtual_memory().percent
    storage = psutil.disk_usage('/').percent
    network = psutil.net_io_counters()
    battery = psutil.sensors_battery()
    battery_str = f"{battery.percent}%" if battery else "N/A (desktop)"
    return f"CPU: {cpu}%, RAM: {ram}%, Storage: {storage}%, Network: {network.bytes_sent} sent, {network.bytes_recv} received, Battery: {battery_str}"


@tool
def open_file(file_path: str) -> str:
    """
    Opens the specified file using the default application.

    Args:
        file_path (str): The path to the file to open.
    """
    try:
        os.startfile(file_path)
        print(f"Opening {file_path} with the default application.")
        return f"Opening {file_path} with the default application."
    except Exception as e:
        print(f"An error occurred while trying to open the file: {e}")
        return f"An error occurred while trying to open the file: {e}"

@tool
def open_directory(directory_path: str) -> str:
    """
    Opens the specified directory in the default file explorer.

    Args:
        directory_path (str): The path to the directory to open.
    """
    try:
        os.startfile(directory_path)
        print(f"Opening {directory_path} in the default file explorer.")
        return f"Opening {directory_path} in the default file explorer."
    except Exception as e:
        print(f"An error occurred while trying to open the directory: {e}")
        return f"An error occurred while trying to open the directory: {e}"

@tool 
def delete_file(file_path: str) -> str:
    """
    Deletes the specified file.

    Args:
        file_path (str): The path to the file to delete.
    """
    blocked = _dangerous_tool_blocked("File deletion")
    if blocked:
        return blocked
    try:
        os.remove(file_path)
        print(f"Deleted {file_path}.")
        return f"Deleted {file_path}."
    except Exception as e:
        print(f"An error occurred while trying to delete the file: {e}")
        return f"An error occurred while trying to delete the file: {e}"

@tool
def copy_file(source_path: str, destination_path: str) -> str:
    """
    Copies a file from the source path to the destination path.

    Args:
        source_path (str): The path to the source file.
        destination_path (str): The path to the destination file.
    """
    try:
        with open(source_path, 'rb') as source_file:
            with open(destination_path, 'wb') as destination_file:
                destination_file.write(source_file.read())
        print(f"Copied {source_path} to {destination_path}.")
        return f"Copied {source_path} to {destination_path}."
    except Exception as e:
        print(f"An error occurred while trying to copy the file: {e}")
        return f"An error occurred while trying to copy the file: {e}"

def move_file(source_path: str, destination_path: str) -> str:
    """
    Moves a file from the source path to the destination path.
    Args:
        source_path (str): The path to the source file.
        destination_path (str): The path to the destination file or folder.
    """
    try:
        if not os.path.exists(source_path):
            return f"Move failed: source file does not exist at {source_path}"
        os.makedirs(os.path.dirname(destination_path), exist_ok=True)
        shutil.move(source_path, destination_path)
        return f"Moved {source_path} to {destination_path}."
    except Exception as e:
        return f"An error occurred while trying to move the file: {e}"

@tool
def rename_file(old_path: str, new_path: str) -> str:
    """
    Renames a file from the old path to the new path.

    Args:
        old_path (str): The current path of the file.
        new_path (str): The new path of the file.
    """
    try:
        os.rename(old_path, new_path)
        print(f"Renamed {old_path} to {new_path}.")
        return f"Renamed {old_path} to {new_path}."
    except Exception as e:
        print(f"An error occurred while trying to rename the file: {e}")
        return f"An error occurred while trying to rename the file: {e}"


@tool
def create_directory(directory_path: str) -> str:
    """
    Creates a new directory at the specified path.

    Args:
        directory_path (str): The path where the new directory will be created.
    """
    try:
        os.makedirs(directory_path, exist_ok=True)
        print(f"Created directory {directory_path}.")
        return f"Created directory {directory_path}."
    except Exception as e:
        print(f"An error occurred while trying to create the directory: {e}")
        return f"An error occurred while trying to create the directory: {e}"

@tool
def create_file(file_path: str, content: str = "") -> str:
    """Creates a new file with optional content. Returns the absolute path used."""
    try:
        abs_path = os.path.abspath(file_path)
        with open(abs_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Created file at absolute path: {abs_path}"
    except Exception as e:
        return f"An error occurred while trying to create the file: {e}"

@tool
def write_to_file(file_path: str, content: str, mode: str = "w") -> str:
    """
    Writes text content to a file. Creates the file if it doesn't exist.

    Args:
        file_path (str): The path to the file.
        content (str): The text to write.
        mode (str): "w" to overwrite, "a" to append. Defaults to "w".
    """
    try:
        with open(file_path, 'w' if mode == "w" else 'a', encoding='utf-8') as f:
            f.write(content)
        return f"Wrote {len(content)} characters to {file_path}."
    except Exception as e:
        return f"An error occurred while writing to the file: {e}"

@tool
def web_opener(url: str) -> str:
    """
    Opens the specified URL in the default web browser.

    Args:
        url (str): The URL of the webpage to open.
    """
    try:
        webbrowser.open(url)
        print(f"Opening {url} in the default web browser.")
        return f"Opening {url} in the default web browser."
    except Exception as e:
        print(f"An error occurred while trying to open the webpage: {e}")
        return f"An error occurred while trying to open the webpage: {e}"

# ---------------------------------------------------
# Search files by name
# ---------------------------------------------------

@tool
def search_files(root_path: str, query: str) -> str:
    """
    Searches for files inside a directory recursively using os.walk().

    Args:
        root_path (str): Starting directory path.
        query (str): Text to search in file names.

    Returns:
        Matching file paths.
    """

    try:
        results = []

        for root, dirs, files in os.walk(root_path):

            for file in files:

                if query.lower() in file.lower():

                    results.append(
                        os.path.join(root, file)
                    )


        if not results:
            return "No matching files found."

        return "\n".join(results[:50])


    except Exception as e:
        return f"Search error: {e}"

@tool
def read_file_content(file_path: str, max_lines: int = 100) -> str:
    """
    Reads the content of a file and returns it as a string.

    Args:
        file_path (str): The path to the file to read.
        max_lines (int): Maximum number of lines to read. Defaults to 100.

    Returns:
        The content of the file or an error message.
    """

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = []
            for i in range(max_lines):
                line = f.readline()
                if not line:
                    break
                lines.append(line.rstrip('\n'))
        return "\n".join(lines)
    except Exception as e:
        return f"Error reading file: {e}"

# ---------------------------------------------------
# Search files by extension
# ---------------------------------------------------

@tool
def find_files_by_extension(root_path: str, extension: str) -> str:
    """
    Finds files with a specific extension recursively.

    Example:
        extension=".py"
        extension=".pdf"
    """

    try:

        results = []

        for root, dirs, files in os.walk(root_path):

            for file in files:

                if file.lower().endswith(extension.lower()):

                    results.append(
                        os.path.join(root,file)
                    )


        if not results:
            return "No files found."


        return "\n".join(results[:100])


    except Exception as e:
        return f"Error: {e}"



# ---------------------------------------------------
# List folder structure
# ---------------------------------------------------

@tool
def list_directory_tree(folder_path: str, depth: int = 2) -> str:
    """
    Creates a directory tree view using os.walk().

    Args:
        folder_path: Root folder.
        depth: Maximum folder depth.
    """

    try:

        output=[]

        base_depth = folder_path.rstrip(os.sep).count(os.sep)


        for root, dirs, files in os.walk(folder_path):

            current_depth = (
                root.count(os.sep)-base_depth
            )


            if current_depth > depth:
                continue


            indent = "    " * current_depth


            output.append(
                f"{indent}[{os.path.basename(root)}]"
            )


            for file in files[:10]:

                output.append(
                    f"{indent} └── {file}"
                )


        return "\n".join(output)


    except Exception as e:
        return f"Error: {e}"



# ---------------------------------------------------
# Find large files
# ---------------------------------------------------

@tool
def find_large_files(root_path: str, size_mb: int = 100) -> str:
    """
    Finds files larger than given size.

    Args:
        root_path: Search location.
        size_mb: Minimum file size MB.
    """

    try:

        results=[]

        limit = size_mb * 1024 * 1024


        for root, dirs, files in os.walk(root_path):

            for file in files:

                path=os.path.join(root,file)

                try:

                    size=os.path.getsize(path)


                    if size > limit:

                        results.append(
                            f"{path} ({size/1024/1024:.2f} MB)"
                        )

                except:
                    pass



        if not results:
            return "No large files found."


        return "\n".join(results[:50])


    except Exception as e:
        return f"Error: {e}"



# ---------------------------------------------------
# Find recently modified files
# ---------------------------------------------------

@tool
def find_recent_files(root_path: str, days: int = 7) -> str:
    """
    Finds files modified within last N days.
    """

    try:

        results=[]

        now=time.time()

        limit = days*24*60*60


        for root, dirs, files in os.walk(root_path):

            for file in files:

                path=os.path.join(root,file)


                try:

                    modified=os.path.getmtime(path)


                    if now-modified < limit:

                        date=datetime.datetime.fromtimestamp(
                            modified
                        )


                        results.append(
                            f"{path} | {date}"
                        )

                except:
                    pass



        return "\n".join(results[:50])


    except Exception as e:
        return f"Error: {e}"



# ---------------------------------------------------
# Get file information
# ---------------------------------------------------

@tool
def get_file_info(file_path: str) -> str:
    """
    Returns file metadata.

    Includes:
    - size
    - created date
    - modified date
    """

    try:

        size=os.path.getsize(file_path)

        created=datetime.datetime.fromtimestamp(
            os.path.getctime(file_path)
        )

        modified=datetime.datetime.fromtimestamp(
            os.path.getmtime(file_path)
        )


        return f"""
File:
{file_path}

Size:
{size/1024:.2f} KB

Created:
{created}

Modified:
{modified}
"""


    except Exception as e:
        return f"Error: {e}"



# ---------------------------------------------------
# Folder statistics
# ---------------------------------------------------

@tool
def analyze_folder(folder_path: str) -> str:
    """
    Calculates folder statistics.

    Returns:
    - total files
    - total folders
    - total size
    """

    try:

        files_count=0
        folder_count=0
        total_size=0


        for root, dirs, files in os.walk(folder_path):

            folder_count += len(dirs)


            for file in files:

                files_count +=1

                try:

                    total_size += os.path.getsize(
                        os.path.join(root,file)
                    )

                except:
                    pass



        return f"""
                Folder:
                {folder_path}

                Files:
                {files_count}

                Folders:
                {folder_count}

                Size:
                {total_size/1024/1024:.2f} MB
                """


    except Exception as e:
        return f"Error: {e}"

@tool
def get_running_apps() -> str:
    """
    Returns currently running user applications.

    Shows:
    - Process ID
    - Application name
    - User
    """

    apps = []

    ignored = [
        "system",
        "svchost",
        "runtimebroker",
        "conhost",
        "dllhost",
        "searchhost"
    ]


    for proc in psutil.process_iter(
        ['pid','name','username']
    ):

        try:

            name = proc.info['name']


            if not name:
                continue


            name_lower = name.lower()


            # Ignore Windows services
            if any(
                x in name_lower 
                for x in ignored
            ):
                continue


            username = proc.info['username']

            apps.append(
                {
                    "pid": proc.info['pid'],
                    "name": name,
                    "username": username or "Unknown"
                }
            )


        except (
            psutil.NoSuchProcess,
            psutil.AccessDenied
        ):
            continue



    if not apps:
        return "No running applications found."


    output = "PID      NAME\n"
    output += "-"*40 + "\n"


    for app in apps[:50]:

        output += (
            f"{app['pid']:<8}"
            f"{app['name']:<30}\n"
        )


    return output

@tool
def lock_the_computer() -> str:
    """
    Locks the computer.
    """

    try:
        if os.name == 'nt':  # Windows
            ctypes.windll.user32.LockWorkStation()
        elif os.name == 'posix':  # macOS or Linux
            subprocess.run(['gnome-screensaver-command', '-l'], check=True)
        else:
            return "Locking not supported on this OS."
        return "Computer locked successfully."
    except Exception as e:
        return f"An error occurred while trying to lock the computer: {e}"

@tool
def shutdown_computer() -> str:
    """
    Shuts down the computer.
    """

    blocked = _dangerous_tool_blocked("Shutdown")
    if blocked:
        return blocked
    try:
        if os.name == 'nt':  # Windows
            subprocess.run(['shutdown', '/s', '/t', '0'], check=True)
        elif os.name == 'posix':  # macOS or Linux
            subprocess.run(['shutdown', '-h', 'now'], check=True)
        else:
            return "Shutdown not supported on this OS."
        return "Shutdown command executed successfully."
    except Exception as e:
        return f"An error occurred while trying to shut down the computer: {e}"

@tool
def restart_computer() -> str:
    """
    Restarts the computer.
    """

    blocked = _dangerous_tool_blocked("Restart")
    if blocked:
        return blocked
    try:
        if os.name == 'nt':  # Windows
            subprocess.run(['shutdown', '/r', '/t', '0'], check=True)
        elif os.name == 'posix':  # macOS or Linux
            subprocess.run(['shutdown', '-r', 'now'], check=True)
        else:
            return "Restart not supported on this OS."
        return "Restart command executed successfully."
    except Exception as e:
        return f"An error occurred while trying to restart the computer: {e}"

@tool
def sleep_computer() -> str:
    """
    Puts the computer to sleep.
    """

    blocked = _dangerous_tool_blocked("Sleep")
    if blocked:
        return blocked
    try:
        if os.name == 'nt':  # Windows
            subprocess.run(['rundll32.exe', 'powrprof.dll,SetSuspendState', '0,1,0'], check=True)
        elif os.name == 'posix':  # macOS or Linux
            subprocess.run(['systemctl', 'suspend'], check=True)
        else:
            return "Sleep not supported on this OS."
        return "Sleep command executed successfully."
    except Exception as e:
        return f"An error occurred while trying to put the computer to sleep: {e}"
@tool
def hibernate_computer() -> str:
    """
    Hibernates the computer.
    """

    blocked = _dangerous_tool_blocked("Hibernation")
    if blocked:
        return blocked
    try:
        if os.name == 'nt':  # Windows
            subprocess.run(['shutdown', '/h'], check=True)
        elif os.name == 'posix':  # macOS or Linux
            subprocess.run(['systemctl', 'hibernate'], check=True)
        else:
            return "Hibernate not supported on this OS."
        return "Hibernate command executed successfully."
    except Exception as e:
        return f"An error occurred while trying to hibernate the computer: {e}"

@tool
def set_volume(level: int) -> str:
    """
    Sets the system volume to the specified level (0-100).
    """

    try:
        if os.name == 'nt':  # Windows
            import ctypes
            devices = ctypes.windll.winmm.waveOutGetNumDevs()
            for i in range(devices):
                ctypes.windll.winmm.waveOutSetVolume(i, int(level * 65535 / 100))
        elif os.name == 'posix':  # macOS or Linux
            subprocess.run(['amixer', 'sset', 'Master', f'{level}%'], check=True)
        else:
            return "Setting volume not supported on this OS."
        return f"Volume set to {level}% successfully."
    except Exception as e:
        return f"An error occurred while trying to set the volume: {e}"
    
@tool
def set_brightness(level: int) -> str:
    """
    Sets the screen brightness to the specified level (0-100).
    """

    try:
        if os.name == 'nt':  # Windows
            import screen_brightness_control as sbc
            sbc.set_brightness(level)
        elif os.name == 'posix':  # macOS or Linux
            subprocess.run(['xbacklight', '-set', str(level)], check=True)
        else:
            return "Setting brightness not supported on this OS."
        return f"Brightness set to {level}% successfully."
    except Exception as e:
        return f"An error occurred while trying to set the brightness: {e}"

@tool
def deep_web_research(query: str, num_sources: int = 3) -> str:
    """
    Perform deep web research: searches the web for a query, then visits each
    result page and extracts its actual content (not just the snippet).
    Use this when the user needs a real answer synthesized from multiple sources,
    not just a list of links.

    Args:
        query (str): The search query.
        num_sources (int): Number of top results to search and scrape (default 3, max 5).
    """
    if not HAS_FIRECRAWL:
        return "❌ Firecrawl is unavailable. Install firecrawl-py and set FIRECRAWL_API_KEY."

    num_sources = min(num_sources, 5)

    try:
        search_results = firecrawl.search(query=query, limit=num_sources)
    except Exception as e:
        return f"Search failed: {e}"

    # search_results.web is the list of result objects (per the SDK)
    urls = [r.url for r in search_results.web if getattr(r, "url", None)]

    if not urls:
        return f"No search results found for query: {query}"

    report_sections = []

    for url in urls:
        try:
            page = firecrawl.scrape(url=url, formats=["markdown"])
            content = getattr(page, "markdown", None) or ""
            content = content.strip()

            if not content:
                report_sections.append(f"### Source: {url}\n(No extractable content)")
                continue

            trimmed = content[:MAX_CHARS_PER_PAGE]
            report_sections.append(f"### Source: {url}\n{trimmed}")

        except Exception as e:
            report_sections.append(f"### Source: {url}\n(Failed to scrape: {e})")

    combined = "\n\n".join(report_sections)
    return (
        f"Research results for '{query}' from {len(urls)} sources:\n\n{combined}\n\n"
        "Instruction: synthesize a clear, well-organized answer from the above sources. "
        "Note any disagreements between sources."
    )

@tool
def get_weather(city: str) -> str:
    """
    Fetches current weather data for the specified city using OpenWeatherMap API.

    Args:
        city (str): The name of the city to fetch weather for.
    """
    API_KEY = os.getenv("OPENWEATHER_API_KEY")
    if not API_KEY:
        return "❌ OPENWEATHER_API_KEY is not set in the environment."
    BASE_URL = "https://api.openweathermap.org/data/2.5/weather"

    params = {
        "q": city,
        "appid": API_KEY,
        "units": "metric"  # Use 'imperial' for Fahrenheit
    }
    try:
        response = requests.get(BASE_URL, params=params, timeout=10)
        response.raise_for_status()

        data = response.json()
        city_name    = data["name"]
        country      = data["sys"]["country"]
        temperature  = data["main"]["temp"]
        feels_like   = data["main"]["feels_like"]
        humidity     = data["main"]["humidity"]
        description  = data["weather"][0]["description"].capitalize()
        wind_speed   = data["wind"]["speed"]

        return f"📍 Weather in {city_name}, {country}\n" \
               f"🌡️  Temperature : {temperature}°C (Feels like {feels_like}°C)\n" \
               f"💧 Humidity    : {humidity}%\n" \
               f"🌬️  Wind Speed  : {wind_speed} m/s\n" \
               f"🌤️  Condition   : {description}"
        # return response.json()

    except requests.exceptions.HTTPError as http_err:
        if response.status_code == 404:
            print(f"❌ City '{city}' not found. Please check the spelling.")
            return f"❌ City '{city}' not found. Please check the spelling."
        elif response.status_code == 401:
            print("❌ Invalid API key. Please check your .env file.")
            return "❌ Invalid API key. Please check your .env file."
        else:
            print(f"❌ HTTP error occurred: {http_err}")
            return f"❌ HTTP error occurred: {http_err}"

    except requests.exceptions.ConnectionError:
        print("❌ Network error. Please check your internet connection.")
        return "❌ Network error. Please check your internet connection."

    except requests.exceptions.Timeout:
        print("❌ Request timed out. Try again later.")
        return "❌ Request timed out. Try again later."

@tool 
def take_screenshot(save_path: str) -> str:
    """
    Takes a screenshot of the entire screen and saves it to the specified path.

    Args:
        save_path (str): The path where the screenshot will be saved.
    """
    try:
        screenshot = pyautogui.screenshot()
        screenshot.save(save_path)
        return f"Screenshot saved to {save_path}."
    except Exception as e:
        return f"An error occurred while taking the screenshot: {e}"

@tool
def get_clipboard() -> str:
    """Returns the current clipboard text content."""
    import pyperclip
    try:
        return pyperclip.paste()
    except Exception as e:
        return f"Error reading clipboard: {e}"

@tool
def set_clipboard(text: str) -> str:
    """Copies text to the clipboard."""
    import pyperclip
    try:
        pyperclip.copy(text)
        return "Text copied to clipboard successfully."
    except Exception as e:
        return f"Error copying to clipboard: {e}"

@tool
def kill_process(pid: int) -> str:
    """Terminates a process by its PID."""
    blocked = _dangerous_tool_blocked("Process termination")
    if blocked:
        return blocked
    try:
        p = psutil.Process(pid)
        p.terminate()
        return f"Process {pid} ({p.name()}) terminated."
    except Exception as e:
        return f"Error terminating process: {e}"

@tool
def get_process_info(pid: int) -> str:
    """Returns detailed info about a specific process."""
    try:
        p = psutil.Process(pid)
        return f"PID: {pid}\nName: {p.name()}\nCPU%: {p.cpu_percent()}\nMemory: {p.memory_info().rss / 1024 / 1024:.2f} MB\nStatus: {p.status()}\nCreated: {datetime.datetime.fromtimestamp(p.create_time())}"
    except Exception as e:
        return f"Error: {e}"

@tool
def speak_text(text: str) -> str:
    """Converts text to speech and plays it through speakers."""
    try:
        import pyttsx3
        engine = pyttsx3.init()
        engine.say(text)
        engine.runAndWait()
        return f"Spoke: {text[:100]}..."
    except Exception as e:
        return f"Error: {e}"

@tool
def listen_and_transcribe(duration: int = 5) -> str:
    """Records audio from microphone and transcribes to text."""
    try:
        import speech_recognition as sr
        r = sr.Recognizer()
        with sr.Microphone() as source:
            audio = r.listen(source, timeout=duration)
        return r.recognize_google(audio)
    except Exception as e:
        return f"Error: {e}"

@tool
def send_notification(title: str, message: str) -> str:
    """Sends a desktop notification to the user."""
    try:
        from plyer import notification
        notification.notify(title=title, message=message, timeout=10)
        return "Notification sent."
    except Exception as e:
        return f"Error: {e}"

@tool
def get_clipboard_image(save_path: str) -> str:
    """Saves the current clipboard image to a file."""
    try:
        from PIL import ImageGrab
        img = ImageGrab.grabclipboard()
        if img is None:
            return "No image found in clipboard."
        img.save(save_path)
        return f"Clipboard image saved to {save_path}."
    except Exception as e:
        return f"Error: {e}"

@tool
def get_active_window_title() -> str:
    """Returns the title of the currently focused window."""
    try:
        import pygetwindow as gw
        return gw.getActiveWindow().title
    except Exception as e:
        return f"Error: {e}"

@tool
def list_all_windows() -> str:
    """Lists all open window titles."""
    try:
        import pygetwindow as gw
        windows = gw.getAllWindows()
        return "\n".join([f"{w.title} (PID: {w._hWnd})" for w in windows if w.title])
    except Exception as e:
        return f"Error: {e}"

def _play_alert_sound():
    """Cross-platform alert beep."""
    try:
        if os.name == "nt" and HAS_WINSOUND:
            winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
        elif HAS_PYGAME:
            pygame.mixer.init()
            # Generate a simple beep using pygame if no sound file
            print("\a", end="", flush=True)
        else:
            print("\a", end="", flush=True)
            if os.name == "posix":
                subprocess.Popen(["paplay", "/usr/share/sounds/freedesktop/stereo/complete.oga"],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# 1. MEDIA PLAYBACK
# ---------------------------------------------------------------------------

@tool
def play_media(file_path: str) -> str:
    """
    Play a media file (music, video, etc.) using the default system player (VLC media player).

    Args:
        file_path: Absolute or relative path to the media file.
    """
    try:
        if not os.path.exists(file_path):
            return f"❌ File not found: {file_path}"

        if os.name == "nt":
            vlc_path = r"C:\Program Files\VideoLAN\VLC\vlc.exe"
            subprocess.Popen([vlc_path, file_path])
        elif sys.platform == "darwin":
            subprocess.Popen(["open", file_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            subprocess.Popen(["xdg-open", file_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        return f"▶️  Playing: {os.path.basename(file_path)}"
    except Exception as e:
        return f"❌ Error playing media: {e}, please ensure you have a media player installed and the file path is correct."


# ---------------------------------------------------------------------------
# 2. YOUTUBE TOOLS
# ---------------------------------------------------------------------------

@tool
def search_youtube(query: str, max_results: int = 5) -> str:
    """
    Search YouTube videos and return titles + URLs.
    No API key required — uses yt-dlp under the hood.

    Args:
        query: Search keywords.
        max_results: Number of results (1-10).
    """
    if not HAS_YTDLP:
        return "❌ yt-dlp is not installed. Run: pip install yt-dlp"

    max_results = max(1, min(max_results, 10))
    try:
        ydl_opts = {
            "quiet": True,
            "extract_flat": True,
            "playlistend": max_results,
            "default_search": "ytsearch",
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            search_query = f"ytsearch{max_results}:{query}"
            result = ydl.extract_info(search_query, download=False)
            entries = result.get("entries", [])

            if not entries:
                return "No results found."

            lines = []
            for i, entry in enumerate(entries, 1):
                title = entry.get("title", "Unknown")
                vid = entry.get("id", "")
                duration = entry.get("duration", 0)
                dur_str = f"{duration//60}:{duration%60:02d}" if duration else "?"
                url = f"https://youtube.com/watch?v={vid}"
                lines.append(f"{i}. {title} ({dur_str}) | {url}")

            return "🎬 YouTube Search Results:\n" + "\n".join(lines)
    except Exception as e:
        return f"❌ Search failed: {e}"


@tool
def play_youtube_video(video_url: str) -> str:
    """
    Open a YouTube video URL in the default web browser.

    Args:
        video_url: Full YouTube URL or video ID.
    """
    try:
        if "youtube.com" not in video_url and "youtu.be" not in video_url:
            # Assume it's a video ID
            video_url = f"https://youtube.com/watch?v={video_url}"
        webbrowser.open(video_url)
        return f"🌐 Opening YouTube: {video_url}"
    except Exception as e:
        return f"❌ Error: {e}"


@tool
def search_youtube_music(query: str, max_results: int = 5) -> str:
    """
    Search YouTube Music and return track titles + URLs.

    Args:
        query: Song/artist search keywords.
        max_results: Number of results (1-10).
    """
    if not HAS_YTDLP:
        return "❌ yt-dlp is not installed. Run: pip install yt-dlp"

    max_results = max(1, min(max_results, 10))
    try:
        ydl_opts = {
            "quiet": True,
            "extract_flat": True,
            "playlistend": max_results,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Search and filter for music-oriented results
            search_query = f"ytsearch{max_results}:{query} audio"
            result = ydl.extract_info(search_query, download=False)
            entries = result.get("entries", [])

            if not entries:
                return "No results found."

            lines = []
            for i, entry in enumerate(entries, 1):
                title = entry.get("title", "Unknown")
                vid = entry.get("id", "")
                url = f"https://music.youtube.com/watch?v={vid}"
                lines.append(f"{i}. 🎵 {title} | {url}")

            return "🎧 YouTube Music Search Results:\n" + "\n".join(lines)
    except Exception as e:
        return f"❌ Search failed: {e}"


@tool
def download_youtube_video(url: str, output_folder: str = "./downloads", audio_only: bool = False, video_quality: str = "best") -> str:
    """
    Download a YouTube video or extract audio only.

    Args:
        url: YouTube video URL.
        output_folder: Where to save the file.
        audio_only: If True, downloads MP3 audio only.
        video_quality: Quality of the video to download.
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
            ext = "mp3" if audio_only else info.get("ext", "mp4")
            filename = ydl.prepare_filename(info)
            if audio_only:
                filename = filename.replace(info.get("ext", "webm"), "mp3")

            return f"✅ Downloaded: {title}\n📁 Saved to: {filename}"
    except Exception as e:
        return f"❌ Download failed: {e}"


# ---------------------------------------------------------------------------
# 3. FILE DOWNLOAD
# ---------------------------------------------------------------------------

@tool
def download_file(url: str, save_path: str) -> str:
    """
    Download any file from a URL with progress tracking.

    Args:
        url: Direct download link.
        save_path: Local path to save the file.
    """
    try:
        os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)

        with requests.get(url, stream=True, timeout=60) as r:
            r.raise_for_status()
            total = int(r.headers.get("content-length", 0))
            downloaded = 0

            with open(save_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)

        size_mb = downloaded / (1024 * 1024)
        return f"⬇️  Downloaded ({size_mb:.2f} MB)\n📁 {save_path}"
    except Exception as e:
        return f"❌ Download error: {e}"


# ---------------------------------------------------------------------------
# 4. SPEED TEST
# ---------------------------------------------------------------------------

@tool
def run_speed_test() -> str:
    """
    Run an internet speed test and return download/upload speeds + ping.
    Note: This may take 20-40 seconds to complete.
    """
    if not HAS_SPEEDTEST:
        return "❌ speedtest-cli not installed. Run: pip install speedtest-cli"

    try:
        st = speedtest.Speedtest()
        st.get_best_server()

        download_bps = st.download()
        upload_bps = st.upload()
        ping_ms = st.results.ping

        download_mbps = download_bps / 1_000_000
        upload_mbps = upload_bps / 1_000_000
        server = st.results.server["sponsor"] + " — " + st.results.server["name"]

        return (
            f"📡 Speed Test Results\n"
            f"{'─'*30}\n"
            f"⬇️  Download: {download_mbps:.2f} Mbps\n"
            f"⬆️  Upload:   {upload_mbps:.2f} Mbps\n"
            f"📶 Ping:     {ping_ms:.0f} ms\n"
            f"🖥️  Server:   {server}"
        )
    except Exception as e:
        return f"❌ Speed test failed: {e}"


# ---------------------------------------------------------------------------
# 5. AUDIO RECORDING
# ---------------------------------------------------------------------------

@tool
def record_audio_note(save_path: str, duration: int = 10) -> str:
    """
    Record audio from the microphone and save as a WAV file.

    Args:
        save_path: Path to save the .wav file (e.g., "note.wav").
        duration: Recording length in seconds (default 10).
    """
    if not HAS_SOUNDDEVICE:
        return "❌ sounddevice not installed. Run: pip install sounddevice"

    try:
        fs = 44100  # Sample rate
        channels = 2

        print(f"🎙️  Recording for {duration} seconds... Speak now!")
        recording = sd.rec(int(duration * fs), samplerate=fs, channels=channels, dtype=np.int16)
        sd.wait()  # Block until finished

        with wave.open(save_path, "wb") as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(2)  # 16-bit = 2 bytes
            wf.setframerate(fs)
            wf.writeframes(recording.tobytes())

        file_size = os.path.getsize(save_path) / 1024
        return f"🎙️  Audio recorded!\n📁 {save_path} ({file_size:.1f} KB) | {duration}s"
    except Exception as e:
        return f"❌ Recording failed: {e}"


# ---------------------------------------------------------------------------
# 6. SCREEN RECORDER (Start / Stop)
# ---------------------------------------------------------------------------

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
            monitor = sct.monitors[1]  # Primary monitor
            width = monitor["width"]
            height = monitor["height"]

            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            out = cv2.VideoWriter(self.save_path, fourcc, 20.0, (width, height))

            while self.recording:
                img = np.array(sct.grab(monitor))
                frame = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
                out.write(frame)
                time.sleep(0.05)  # ~20 FPS

            out.release()

    def stop(self):
        self.recording = False
        if self._thread:
            self._thread.join(timeout=10)


# Global recorder instance (so start/stop can reference the same object)
_active_screen_recorder: Optional[_ScreenRecorder] = None


@tool
def start_screen_recording(save_path: str = "screen_recording.mp4") -> str:
    """
    Start recording the screen. Must call stop_screen_recording() later to save.

    Args:
        save_path: Output video file path (default: screen_recording.mp4).
    """
    global _active_screen_recorder

    if not HAS_MSS:
        return "❌ mss and opencv-python required. Run: pip install mss opencv-python"

    try:
        if _active_screen_recorder is not None and _active_screen_recorder.recording:
            return "⚠️  Screen recording is already running. Stop it first."

        _active_screen_recorder = _ScreenRecorder(save_path)
        _active_screen_recorder.start()
        return f"🎥 Screen recording STARTED\n📁 Saving to: {os.path.abspath(save_path)}"
    except Exception as e:
        return f"❌ Failed to start recording: {e}"


@tool
def stop_screen_recording() -> str:
    """
    Stop the active screen recording and finalize the video file.
    """
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


# ---------------------------------------------------------------------------
# 7. TIMER
# ---------------------------------------------------------------------------

@tool
def set_timer(minutes: float, message: str = "Timer finished!") -> str:
    """
    Set a countdown timer. Shows a desktop notification + sound when done.

    Args:
        minutes: Countdown duration in minutes (supports decimals, e.g., 0.5 = 30s).
        message: Notification message when timer expires.
    """
    try:
        seconds = minutes * 60
        end_time = (datetime.datetime.now() + datetime.timedelta(seconds=seconds)).strftime("%H:%M:%S")

        def _timer_done():
            if HAS_PLYER:
                try:
                    notification.notify(
                        title="⏰ Timer Done",
                        message=message,
                        timeout=15,
                        app_name="AI Agent"
                    )
                except Exception:
                    pass
            _play_alert_sound()
            print(f"\n🔔 TIMER: {message}")

        t = threading.Timer(seconds, _timer_done)
        t.daemon = True
        t.start()

        return (
            f"⏱️  Timer set for {minutes} minute(s)\n"
            f"🔔 Will notify at {end_time}"
        )
    except Exception as e:
        return f"❌ Error setting timer: {e}"


# ---------------------------------------------------------------------------
# 8. ALARM
# ---------------------------------------------------------------------------

@tool
def set_alarm(time_str: str, message: str = "Wake up! Alarm ringing!") -> str:
    """
    Set an alarm for a specific time today (or tomorrow if time already passed).

    Args:
        time_str: Time in 24-hour format "HH:MM" (e.g., "07:30" or "18:45").
        message: Notification message when alarm rings.
    """
    try:
        now = datetime.datetime.now()
        alarm_time = datetime.datetime.strptime(time_str, "%H:%M").replace(
            year=now.year, month=now.month, day=now.day
        )

        # If time already passed today, set for tomorrow
        if alarm_time <= now:
            alarm_time += datetime.timedelta(days=1)

        seconds_until = (alarm_time - now).total_seconds()
        mins_until = int(seconds_until // 60)

        def _alarm_done():
            if HAS_PLYER:
                try:
                    notification.notify(
                        title="🚨 Alarm",
                        message=message,
                        timeout=30,
                        app_name="AI Agent"
                    )
                except Exception:
                    pass
            _play_alert_sound()
            print(f"\n🚨 ALARM: {message}")

        t = threading.Timer(seconds_until, _alarm_done)
        t.daemon = True
        t.start()

        return (
            f"🚨 Alarm set for {time_str}\n"
            f"⏳ Rings in {mins_until} minute(s)"
        )
    except ValueError:
        return "❌ Invalid time format. Use 24-hour format: HH:MM (e.g., 07:30 or 18:45)"
    except Exception as e:
        return f"❌ Error setting alarm: {e}"

@tool
def cancel_all_timers_and_alarms() -> str:
    """
    Cancel all active timers and alarms.
    """
    try:
        for thread in threading.enumerate():
            if isinstance(thread, threading.Timer):
                thread.cancel()
        return "✅ All timers and alarms have been canceled."
    except Exception as e:
        return f"❌ Error canceling timers/alarms: {e}"

# ---------------------------------------------------------------------------
# 9. BONUS: Quick media info
# ---------------------------------------------------------------------------

@tool
def get_media_info(file_path: str) -> str:
    """
    Get basic info about a media file (size, duration if detectable).

    Args:
        file_path: Path to the media file.
    """
    try:
        if not os.path.exists(file_path):
            return f"❌ File not found: {file_path}"

        size = os.path.getsize(file_path) / (1024 * 1024)
        ext = os.path.splitext(file_path)[1].upper()

        info = f"📄 {os.path.basename(file_path)}\n🗂️  Type: {ext}\n📦 Size: {size:.2f} MB"

        # Try to get duration with ffprobe if available
        try:
            result = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", file_path],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                duration = float(result.stdout.strip())
                mins = int(duration // 60)
                secs = int(duration % 60)
                info += f"\n⏱️  Duration: {mins}:{secs:02d}"
        except Exception:
            pass

        return info
    except Exception as e:
        return f"❌ Error: {e}"

@tool

def run_commnds_in_terminal(command: str) -> str:
    """
    Executes a command in the system terminal and returns the output.

    Args:
        command: The command to execute.
    """
    blocked = _dangerous_tool_blocked("Terminal command execution")
    if blocked:
        return blocked
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            return f"✅ Command executed successfully:\n{result.stdout.strip()}"
        else:
            return f"❌ Command failed with error:\n{result.stderr.strip()}"
    except Exception as e:
        return f"❌ Error executing command: {e}"