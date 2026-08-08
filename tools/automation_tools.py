"""
tools/automation_tools.py
Keyboard, mouse, window automation, clipboard, voice, and notification tools
(existing 7 migrated + 6 new keyboard/mouse/window tools).

NEW tools: type_text, press_hotkey, click_at_position, scroll_page,
           move_window, minimize_all_windows
"""

import os
import subprocess
import datetime
import threading
from langchain_core.tools import tool

try:
    import pyautogui
    pyautogui.FAILSAFE = True  # Move mouse to top-left to abort
    HAS_PYAUTOGUI = True
except ImportError:
    HAS_PYAUTOGUI = False

try:
    import pygetwindow as gw
    HAS_PYGETWINDOW = True
except ImportError:
    HAS_PYGETWINDOW = False

try:
    import pyperclip
    HAS_PYPERCLIP = True
except ImportError:
    HAS_PYPERCLIP = False

try:
    from plyer import notification as plyer_notif
    HAS_PLYER = True
except ImportError:
    HAS_PLYER = False

try:
    import pyttsx3
    HAS_TTS = True
except ImportError:
    HAS_TTS = False

try:
    import speech_recognition as sr
    HAS_SR = True
except ImportError:
    HAS_SR = False

try:
    import winsound
    HAS_WINSOUND = True
except ImportError:
    HAS_WINSOUND = False


def _play_alert_sound():
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
def get_clipboard() -> str:
    """Returns the current clipboard text content."""
    if not HAS_PYPERCLIP:
        return "❌ pyperclip not installed."
    try:
        return pyperclip.paste()
    except Exception as e:
        return f"Error reading clipboard: {e}"


@tool
def set_clipboard(text: str) -> str:
    """Copies the given text to the clipboard.

    Args:
        text: The text to copy to the clipboard.
    """
    if not HAS_PYPERCLIP:
        return "❌ pyperclip not installed."
    try:
        pyperclip.copy(text)
        return "✅ Text copied to clipboard."
    except Exception as e:
        return f"Error: {e}"


@tool
def get_clipboard_image(save_path: str) -> str:
    """Saves the current clipboard image to a file.

    Args:
        save_path: Path to save the image (e.g., 'clipboard_image.png').
    """
    try:
        from PIL import ImageGrab
        img = ImageGrab.grabclipboard()
        if img is None:
            return "No image found in clipboard."
        img.save(save_path)
        return f"📸 Clipboard image saved to {save_path}."
    except Exception as e:
        return f"Error: {e}"


@tool
def get_active_window_title() -> str:
    """Returns the title of the currently focused window."""
    if not HAS_PYGETWINDOW:
        return "❌ pygetwindow not installed."
    try:
        win = gw.getActiveWindow()
        return win.title if win else "No active window."
    except Exception as e:
        return f"Error: {e}"


@tool
def list_all_windows() -> str:
    """Lists all open window titles."""
    if not HAS_PYGETWINDOW:
        return "❌ pygetwindow not installed."
    try:
        windows = gw.getAllWindows()
        titles = [f"{w.title}" for w in windows if w.title]
        return "\n".join(titles) if titles else "No open windows found."
    except Exception as e:
        return f"Error: {e}"


@tool
def speak_text(text: str) -> str:
    """Converts text to speech and plays it through speakers.

    Args:
        text: The text to speak aloud.
    """
    if not HAS_TTS:
        return "❌ pyttsx3 not installed. Run: pip install pyttsx3"
    try:
        engine = pyttsx3.init()
        voices = engine.getProperty('voices')
        engine.setProperty('voice', voices[1].id)
        engine.say(text)
        engine.runAndWait()
        return f"🗣️  Spoke: {text[:100]}"
    except Exception as e:
        return f"Error: {e}"


@tool
def listen_and_transcribe(duration: int = 5) -> str:
    """Records from the microphone and transcribes audio to text.

    Args:
        duration: Listen timeout in seconds (default 5).
    """
    if not HAS_SR:
        return "❌ SpeechRecognition not installed. Run: pip install SpeechRecognition"
    try:
        recognizer = sr.Recognizer()
        with sr.Microphone() as source:
            audio = recognizer.listen(source, timeout=duration)
        return recognizer.recognize_google(audio)
    except sr.WaitTimeoutError:
        return "⚠️  No speech detected within the timeout."
    except Exception as e:
        return f"Error: {e}"


@tool
def send_notification(title: str, message: str) -> str:
    """Sends a desktop notification to the user.

    Args:
        title: Notification title.
        message: Notification body text.
    """
    if not HAS_PLYER:
        return "❌ plyer not installed. Run: pip install plyer"
    try:
        plyer_notif.notify(title=title, message=message, timeout=10, app_name="AI Agent")
        return "✅ Notification sent."
    except Exception as e:
        return f"Error: {e}"


@tool
def set_timer(minutes: float, message: str = "Timer finished!") -> str:
    """Sets a countdown timer. Plays a sound and shows a notification when done.

    Args:
        minutes: Duration in minutes (supports decimals, e.g. 0.5 = 30s).
        message: Message to display when the timer expires.
    """
    try:
        seconds = minutes * 60
        end_time = (datetime.datetime.now() + datetime.timedelta(seconds=seconds)).strftime("%H:%M:%S")

        def _done():
            if HAS_PLYER:
                try:
                    plyer_notif.notify(title="⏰ Timer Done", message=message, timeout=15)
                except Exception:
                    pass
            _play_alert_sound()
            print(f"\n🔔 TIMER: {message}")

        t = threading.Timer(seconds, _done)
        t.daemon = True
        t.start()
        return f"⏱️  Timer set for {minutes} minute(s)\n🔔 Will notify at {end_time}"
    except Exception as e:
        return f"❌ Error: {e}"


@tool
def set_alarm(time_str: str, message: str = "Wake up! Alarm ringing!") -> str:
    """Sets an alarm for a specific time today (tomorrow if already passed).

    Args:
        time_str: Time in 24-hour format HH:MM (e.g., '07:30' or '18:45').
        message: Message to display when the alarm rings.
    """
    try:
        now = datetime.datetime.now()
        alarm_time = datetime.datetime.strptime(time_str, "%H:%M").replace(
            year=now.year, month=now.month, day=now.day
        )
        if alarm_time <= now:
            alarm_time += datetime.timedelta(days=1)
        seconds_until = (alarm_time - now).total_seconds()
        mins_until = int(seconds_until // 60)

        def _ring():
            if HAS_PLYER:
                try:
                    plyer_notif.notify(title="🚨 Alarm", message=message, timeout=30)
                except Exception:
                    pass
            _play_alert_sound()
            print(f"\n🚨 ALARM: {message}")

        t = threading.Timer(seconds_until, _ring)
        t.daemon = True
        t.start()
        return f"🚨 Alarm set for {time_str}\n⏳ Rings in {mins_until} minute(s)"
    except ValueError:
        return "❌ Invalid time format. Use HH:MM (e.g., 07:30)"
    except Exception as e:
        return f"❌ Error: {e}"


@tool
def cancel_all_timers_and_alarms() -> str:
    """Cancels all active timers and alarms."""
    try:
        count = 0
        for thread in threading.enumerate():
            if isinstance(thread, threading.Timer):
                thread.cancel()
                count += 1
        return f"✅ Cancelled {count} timer(s)/alarm(s)."
    except Exception as e:
        return f"❌ Error: {e}"


# ─────────────────────────────────────────────────────────────────────────────
# NEW TOOLS — Keyboard & Mouse Automation
# ─────────────────────────────────────────────────────────────────────────────

@tool
def type_text(text: str, interval: float = 0.03) -> str:
    """Simulates keyboard typing of the given text.

    Args:
        text: The text to type.
        interval: Delay between keystrokes in seconds (default 0.03).
    """
    if not HAS_PYAUTOGUI:
        return "❌ pyautogui not installed."
    try:
        pyautogui.typewrite(text, interval=interval)
        return f"⌨️  Typed: {text[:80]}{'...' if len(text) > 80 else ''}"
    except Exception as e:
        return f"❌ Error typing text: {e}"


@tool
def press_hotkey(keys: str) -> str:
    """Presses a keyboard shortcut or hotkey combination.

    Args:
        keys: Plus-sign separated key names (e.g., 'ctrl+c', 'alt+tab', 'win+d', 'ctrl+shift+esc').
              Supported keys: ctrl, alt, shift, win, tab, enter, esc, space, f1-f12, and letter/number keys.
    """
    if not HAS_PYAUTOGUI:
        return "❌ pyautogui not installed."
    try:
        key_list = [k.strip() for k in keys.lower().split("+")]
        pyautogui.hotkey(*key_list)
        return f"⌨️  Pressed hotkey: {keys}"
    except Exception as e:
        return f"❌ Error pressing hotkey: {e}"


@tool
def click_at_position(x: int, y: int, button: str = "left", clicks: int = 1) -> str:
    """Clicks the mouse at the specified screen coordinates.

    Args:
        x: Horizontal screen coordinate in pixels.
        y: Vertical screen coordinate in pixels.
        button: Mouse button to click: 'left', 'right', or 'middle' (default 'left').
        clicks: Number of clicks (1 = single, 2 = double-click, default 1).
    """
    if not HAS_PYAUTOGUI:
        return "❌ pyautogui not installed."
    try:
        pyautogui.click(x, y, button=button, clicks=clicks)
        action = "Double-clicked" if clicks == 2 else "Clicked"
        return f"🖱️  {action} {button} button at ({x}, {y})."
    except Exception as e:
        return f"❌ Error clicking: {e}"


@tool
def scroll_page(direction: str, amount: int = 3) -> str:
    """Scrolls the page up or down.

    Args:
        direction: 'up' or 'down'.
        amount: Number of scroll clicks (default 3).
    """
    if not HAS_PYAUTOGUI:
        return "❌ pyautogui not installed."
    try:
        clicks = amount if direction.lower() == "up" else -amount
        pyautogui.scroll(clicks)
        return f"🖱️  Scrolled {direction} by {amount} clicks."
    except Exception as e:
        return f"❌ Error scrolling: {e}"


@tool
def move_window(title: str, x: int = 100, y: int = 100, width: int = 800, height: int = 600) -> str:
    """Moves and resizes a window by its title.

    Args:
        title: Part of the window title to match (case-insensitive).
        x: New left position in pixels.
        y: New top position in pixels.
        width: New window width in pixels.
        height: New window height in pixels.
    """
    if not HAS_PYGETWINDOW:
        return "❌ pygetwindow not installed."
    try:
        matches = [w for w in gw.getAllWindows() if title.lower() in w.title.lower()]
        if not matches:
            return f"❌ No window found matching '{title}'."
        win = matches[0]
        win.moveTo(x, y)
        win.resizeTo(width, height)
        return f"✅ Moved '{win.title}' to ({x}, {y}), size {width}×{height}."
    except Exception as e:
        return f"❌ Error: {e}"


@tool
def minimize_all_windows() -> str:
    """Minimizes all open windows to show the desktop (Win+D shortcut)."""
    if not HAS_PYAUTOGUI:
        return "❌ pyautogui not installed."
    try:
        pyautogui.hotkey("win", "d")
        return "✅ All windows minimized (Show Desktop)."
    except Exception as e:
        return f"❌ Error: {e}"
