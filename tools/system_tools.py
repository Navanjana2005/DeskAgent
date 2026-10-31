"""
tools/system_tools.py
System control tools (existing 11 migrated + 8 new).

NEW tools: get_disk_partitions, get_hardware_info, get_wifi_networks, connect_wifi,
           get_startup_programs, toggle_dark_mode, empty_recycle_bin, set_wallpaper
"""

import os
import sys
import ctypes
import platform
import socket
import subprocess
import html
import tempfile
import psutil
import datetime
from langchain_core.tools import tool
from tools.safety import dangerous_tools_enabled

try:
    from AppOpener import open as launch_app, close as terminate_app
    HAS_APPOPENER = True
except ImportError:
    HAS_APPOPENER = False

try:
    import winreg
    HAS_WINREG = True
except ImportError:
    HAS_WINREG = False


# ─────────────────────────────────────────────────────────────────────────────
# EXISTING TOOLS (migrated)
# ─────────────────────────────────────────────────────────────────────────────

@tool
def app_opener(app_name: str) -> str:
    """Opens the specified application by name (e.g. 'notepad', 'chrome', 'spotify').
    Uses fuzzy matching so exact executable names aren't required.
    """
    try:
        launch_app(app_name, match_closest=True, output=False, throw_error=True)
        return f"{app_name} has been opened successfully."
    except Exception as e:
        return f"An error occurred while trying to open {app_name}: {e}"


@tool
def app_closer(app_name: str) -> str:
    """Closes the specified application by name."""
    try:
        terminate_app(app_name, match_closest=True, output=False, throw_error=True)
        return f"{app_name} has been closed successfully."
    except Exception as e:
        return f"An error occurred while trying to close {app_name}: {e}"


@tool
def get_system_stats() -> str:
    """Returns current CPU usage, RAM usage, disk usage, network I/O, and battery."""
    cpu = psutil.cpu_percent(interval=1)
    ram = psutil.virtual_memory().percent
    storage = psutil.disk_usage("/").percent
    network = psutil.net_io_counters()
    battery = psutil.sensors_battery()
    battery_str = f"{battery.percent}%" if battery else "N/A (desktop)"
    return (
        f"CPU: {cpu}%\n"
        f"RAM: {ram}%\n"
        f"Storage: {storage}%\n"
        f"Network sent: {network.bytes_sent / 1024 / 1024:.2f} MB | "
        f"received: {network.bytes_recv / 1024 / 1024:.2f} MB\n"
        f"Battery: {battery_str}"
    )


@tool
def get_running_apps() -> str:
    """Returns currently running user applications (PID + name)."""
    ignored = {"system", "svchost", "runtimebroker", "conhost", "dllhost", "searchhost"}
    apps = []
    for proc in psutil.process_iter(["pid", "name", "username"]):
        try:
            name = proc.info["name"] or ""
            if any(x in name.lower() for x in ignored):
                continue
            apps.append({"pid": proc.info["pid"], "name": name})
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    if not apps:
        return "No running applications found."
    output = f"{'PID':<8} {'NAME':<30}\n" + "-" * 40 + "\n"
    for app in apps[:50]:
        output += f"{app['pid']:<8} {app['name']:<30}\n"
    return output


@tool
def kill_process(pid: int) -> str:
    """Terminates a process by its PID.

    Args:
        pid: The process ID to terminate.
    """
    if not dangerous_tools_enabled():
        return (
            "⛔ Process termination is disabled. Set ALLOW_DANGEROUS_TOOLS=1 "
            "in your environment to enable it."
        )
    try:
        p = psutil.Process(pid)
        name = p.name()
        p.terminate()
        return f"Process {pid} ({name}) terminated."
    except Exception as e:
        return f"Error terminating process: {e}"


@tool
def get_process_info(pid: int) -> str:
    """Returns detailed info about a specific process.

    Args:
        pid: The process ID to inspect.
    """
    try:
        p = psutil.Process(pid)
        return (
            f"PID: {pid}\n"
            f"Name: {p.name()}\n"
            f"CPU%: {p.cpu_percent()}\n"
            f"Memory: {p.memory_info().rss / 1024 / 1024:.2f} MB\n"
            f"Status: {p.status()}\n"
            f"Created: {datetime.datetime.fromtimestamp(p.create_time())}"
        )
    except Exception as e:
        return f"Error: {e}"


@tool
def lock_the_computer() -> str:
    """Locks the computer screen immediately."""
    try:
        if os.name == "nt":
            ctypes.windll.user32.LockWorkStation()
        else:
            subprocess.run(["gnome-screensaver-command", "-l"], check=True)
        return "Computer locked successfully."
    except Exception as e:
        return f"An error occurred while trying to lock the computer: {e}"


@tool
def shutdown_computer() -> str:
    """Shuts down the computer immediately."""
    if not dangerous_tools_enabled():
        return (
            "⛔ Shutdown is disabled. Set ALLOW_DANGEROUS_TOOLS=1 "
            "in your environment to enable it."
        )
    try:
        if os.name == "nt":
            subprocess.run(["shutdown", "/s", "/t", "0"], check=True)
        else:
            subprocess.run(["shutdown", "-h", "now"], check=True)
        return "Shutdown command executed."
    except Exception as e:
        return f"An error occurred: {e}"


@tool
def restart_computer() -> str:
    """Restarts the computer immediately."""
    if not dangerous_tools_enabled():
        return (
            "⛔ Restart is disabled. Set ALLOW_DANGEROUS_TOOLS=1 "
            "in your environment to enable it."
        )
    try:
        if os.name == "nt":
            subprocess.run(["shutdown", "/r", "/t", "0"], check=True)
        else:
            subprocess.run(["shutdown", "-r", "now"], check=True)
        return "Restart command executed."
    except Exception as e:
        return f"An error occurred: {e}"


@tool
def sleep_computer() -> str:
    """Puts the computer to sleep."""
    if not dangerous_tools_enabled():
        return (
            "⛔ Sleep is disabled. Set ALLOW_DANGEROUS_TOOLS=1 "
            "in your environment to enable it."
        )
    try:
        if os.name == "nt":
            subprocess.run(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"], check=True)
        else:
            subprocess.run(["systemctl", "suspend"], check=True)
        return "Sleep command executed."
    except Exception as e:
        return f"An error occurred: {e}"


@tool
def hibernate_computer() -> str:
    """Hibernates the computer."""
    if not dangerous_tools_enabled():
        return (
            "⛔ Hibernation is disabled. Set ALLOW_DANGEROUS_TOOLS=1 "
            "in your environment to enable it."
        )
    try:
        if os.name == "nt":
            subprocess.run(["shutdown", "/h"], check=True)
        else:
            subprocess.run(["systemctl", "hibernate"], check=True)
        return "Hibernate command executed."
    except Exception as e:
        return f"An error occurred: {e}"


@tool
def set_volume(level: int) -> str:
    """Sets the system volume to the specified level (0–100).

    Args:
        level: Volume percentage (0 to 100).
    """
    try:
        level = max(0, min(100, level))
        if os.name == "nt":
            devices = ctypes.windll.winmm.waveOutGetNumDevs()
            vol = int(level * 65535 / 100)
            for i in range(devices):
                ctypes.windll.winmm.waveOutSetVolume(i, vol | (vol << 16))
        else:
            subprocess.run(["amixer", "sset", "Master", f"{level}%"], check=True)
        return f"Volume set to {level}%."
    except Exception as e:
        return f"An error occurred while setting volume: {e}"


@tool
def set_brightness(level: int) -> str:
    """Sets the screen brightness to the specified level (0–100).

    Args:
        level: Brightness percentage (0 to 100).
    """
    try:
        if os.name == "nt":
            import screen_brightness_control as sbc
            sbc.set_brightness(level)
        else:
            subprocess.run(["xbacklight", "-set", str(level)], check=True)
        return f"Brightness set to {level}%."
    except Exception as e:
        return f"An error occurred while setting brightness: {e}"


# ─────────────────────────────────────────────────────────────────────────────
# NEW TOOLS
# ─────────────────────────────────────────────────────────────────────────────

@tool
def get_disk_partitions() -> str:
    """Lists all disk partitions with filesystem type, total size, used, free, and usage %."""
    try:
        lines = [f"{'Device':<20} {'Mount':<15} {'FS':<8} {'Total':>10} {'Used':>10} {'Free':>10} {'Use%':>6}"]
        lines.append("-" * 82)
        for part in psutil.disk_partitions(all=False):
            try:
                usage = psutil.disk_usage(part.mountpoint)
                lines.append(
                    f"{part.device:<20} {part.mountpoint:<15} {part.fstype:<8} "
                    f"{usage.total / 1e9:>9.1f}G {usage.used / 1e9:>9.1f}G "
                    f"{usage.free / 1e9:>9.1f}G {usage.percent:>5.1f}%"
                )
            except PermissionError:
                lines.append(f"{part.device:<20} {part.mountpoint:<15} {'N/A (access denied)'}")
        return "\n".join(lines)
    except Exception as e:
        return f"❌ Error: {e}"


@tool
def get_hardware_info() -> str:
    """Returns detailed hardware information: CPU model, cores, RAM, architecture, and OS."""
    try:
        cpu_freq = psutil.cpu_freq()
        freq_str = f"{cpu_freq.current:.0f} MHz" if cpu_freq else "N/A"
        ram = psutil.virtual_memory()
        swap = psutil.swap_memory()

        info = (
            f"🖥️  System Hardware Report\n"
            f"{'─' * 40}\n"
            f"OS:           {platform.system()} {platform.release()} ({platform.version()})\n"
            f"Architecture: {platform.machine()}\n"
            f"Processor:    {platform.processor() or 'N/A'}\n"
            f"CPU Cores:    {psutil.cpu_count(logical=False)} physical / {psutil.cpu_count()} logical\n"
            f"CPU Freq:     {freq_str}\n"
            f"CPU Usage:    {psutil.cpu_percent(interval=0.5)}%\n"
            f"RAM Total:    {ram.total / 1e9:.2f} GB\n"
            f"RAM Used:     {ram.used / 1e9:.2f} GB ({ram.percent}%)\n"
            f"RAM Free:     {ram.available / 1e9:.2f} GB\n"
            f"Swap Total:   {swap.total / 1e9:.2f} GB\n"
            f"Swap Used:    {swap.used / 1e9:.2f} GB ({swap.percent}%)\n"
            f"Hostname:     {socket.gethostname()}\n"
            f"Python:       {platform.python_version()}"
        )
        return info
    except Exception as e:
        return f"❌ Error: {e}"


@tool
def get_wifi_networks() -> str:
    """Lists available Wi-Fi networks (Windows only, uses netsh)."""
    try:
        if os.name != "nt":
            return "❌ This tool only works on Windows."
        result = subprocess.run(
            ["netsh", "wlan", "show", "networks", "mode=Bssid"],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode != 0:
            return f"❌ Failed: {result.stderr.strip()}"
        # Parse SSID lines
        lines = result.stdout.splitlines()
        networks = []
        current = {}
        for line in lines:
            line = line.strip()
            if line.startswith("SSID") and "BSSID" not in line:
                if current:
                    networks.append(current)
                current = {"ssid": line.split(":", 1)[-1].strip()}
            elif "Signal" in line:
                current["signal"] = line.split(":", 1)[-1].strip()
            elif "Authentication" in line:
                current["auth"] = line.split(":", 1)[-1].strip()
        if current:
            networks.append(current)
        if not networks:
            return "No Wi-Fi networks found."
        output = f"📶 Found {len(networks)} network(s):\n\n"
        for i, n in enumerate(networks, 1):
            output += (
                f"{i:2}. SSID: {n.get('ssid', 'N/A')}\n"
                f"     Signal: {n.get('signal', 'N/A')} | "
                f"Auth: {n.get('auth', 'N/A')}\n"
            )
        return output
    except Exception as e:
        return f"❌ Error: {e}"


@tool
def connect_wifi(ssid: str, password: str = "") -> str:
    """Connects to a Wi-Fi network by SSID (Windows only).

    Args:
        ssid: The Wi-Fi network name (SSID) to connect to.
        password: The Wi-Fi password (leave empty for open networks).
    """
    try:
        if os.name != "nt":
            return "❌ This tool only works on Windows."

        if not dangerous_tools_enabled():
            return (
                "⛔ Changing Wi-Fi networks is disabled. Set "
                "ALLOW_DANGEROUS_TOOLS=1 in your environment to enable it."
            )

        auth = "WPA2PSK" if password else "open"
        encrypt = "AES" if password else "none"
        key_block = (
            f"<keyMaterial>{html.escape(password)}</keyMaterial>"
            if password else ""
        )
        escaped_ssid = html.escape(ssid)
        profile_xml = f"""<?xml version="1.0"?>
<WLANProfile xmlns="http://www.microsoft.com/networking/WLAN/profile/v1">
    <name>{escaped_ssid}</name>
    <SSIDConfig><SSID><name>{escaped_ssid}</name></SSID></SSIDConfig>
    <connectionType>ESS</connectionType>
    <connectionMode>auto</connectionMode>
    <MSM>
        <security>
            <authEncryption>
                <authentication>{auth}</authentication>
                <encryption>{encrypt}</encryption>
                <useOneX>false</useOneX>
            </authEncryption>
            {"<sharedKey><keyType>passPhrase</keyType><protected>false</protected>" + key_block + "</sharedKey>" if password else ""}
        </security>
    </MSM>
</WLANProfile>"""

        with tempfile.TemporaryDirectory() as temp_dir:
            profile_path = os.path.join(temp_dir, "wifi_profile.xml")
            with open(profile_path, "w", encoding="utf-8") as profile_file:
                profile_file.write(profile_xml)

            add_result = subprocess.run(
                ["netsh", "wlan", "add", "profile", f"filename={profile_path}"],
                capture_output=True,
                text=True,
                timeout=15,
            )
            if add_result.returncode != 0:
                return f"❌ Failed to add Wi-Fi profile: {add_result.stderr.strip()}"

            result = subprocess.run(
                ["netsh", "wlan", "connect", f"name={ssid}"],
                capture_output=True,
                text=True,
                timeout=15,
            )

        if result.returncode == 0:
            return f"✅ Connected to Wi-Fi: {ssid}"
        return f"❌ Failed to connect: {(result.stderr or result.stdout).strip()}"
    except Exception as e:
        return f"❌ Error: {e}"


@tool
def get_startup_programs() -> str:
    """Lists programs configured to run at Windows startup (from registry)."""
    try:
        if not HAS_WINREG:
            return "❌ winreg not available (Windows only)."
        keys = [
            (winreg.HKEY_CURRENT_USER,
             r"Software\Microsoft\Windows\CurrentVersion\Run"),
            (winreg.HKEY_LOCAL_MACHINE,
             r"Software\Microsoft\Windows\CurrentVersion\Run"),
        ]
        entries = []
        for hive, path in keys:
            try:
                reg = winreg.OpenKey(hive, path)
                i = 0
                while True:
                    try:
                        name, value, _ = winreg.EnumValue(reg, i)
                        entries.append(f"  {name}: {value}")
                        i += 1
                    except OSError:
                        break
                winreg.CloseKey(reg)
            except Exception:
                pass
        if not entries:
            return "No startup programs found."
        return f"🚀 Startup Programs ({len(entries)}):\n" + "\n".join(entries)
    except Exception as e:
        return f"❌ Error: {e}"


@tool
def toggle_dark_mode() -> str:
    """Toggles between Windows light and dark mode."""
    try:
        if not HAS_WINREG:
            return "❌ winreg not available (Windows only)."
        reg_path = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
        reg = winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path, 0, winreg.KEY_ALL_ACCESS)
        current, _ = winreg.QueryValueEx(reg, "AppsUseLightTheme")
        new_val = 0 if current == 1 else 1
        winreg.SetValueEx(reg, "AppsUseLightTheme", 0, winreg.REG_DWORD, new_val)
        winreg.SetValueEx(reg, "SystemUsesLightTheme", 0, winreg.REG_DWORD, new_val)
        winreg.CloseKey(reg)
        mode = "Light" if new_val == 1 else "Dark"
        return f"✅ Switched to {mode} mode."
    except Exception as e:
        return f"❌ Error toggling dark mode: {e}"


@tool
def empty_recycle_bin() -> str:
    """Empties the Windows Recycle Bin."""
    if not dangerous_tools_enabled():
        return (
            "⛔ Emptying the Recycle Bin is disabled. Set ALLOW_DANGEROUS_TOOLS=1 "
            "in your environment to enable it."
        )
    try:
        if os.name != "nt":
            return "❌ This tool only works on Windows."
        # SHEmptyRecycleBin: flags 7 = SHERB_NOCONFIRMATION|SHERB_NOPROGRESSUI|SHERB_NOSOUND
        result = ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, 0x0007)
        if result == 0 or result == -2147418113:  # S_OK or already empty
            return "✅ Recycle Bin emptied successfully."
        return f"⚠️ SHEmptyRecycleBin returned code: {result}"
    except Exception as e:
        return f"❌ Error: {e}"


@tool
def set_wallpaper(image_path: str) -> str:
    """Sets the desktop wallpaper to the specified image.

    Args:
        image_path: Absolute path to the image file (JPG, PNG, BMP).
    """
    try:
        if not os.path.exists(image_path):
            return f"❌ Image file not found: {image_path}"
        abs_path = os.path.abspath(image_path)
        if os.name == "nt":
            # SPI_SETDESKWALLPAPER = 0x0014
            result = ctypes.windll.user32.SystemParametersInfoW(0x0014, 0, abs_path, 3)
            if result:
                return f"✅ Wallpaper set to: {abs_path}"
            return "❌ Failed to set wallpaper."
        elif sys.platform == "darwin":
            subprocess.run(
                ["osascript", "-e",
                 f'tell application "Finder" to set desktop picture to POSIX file "{abs_path}"'],
                check=True
            )
            return f"✅ Wallpaper set to: {abs_path}"
        else:
            subprocess.run(
                ["gsettings", "set", "org.gnome.desktop.background", "picture-uri", f"file://{abs_path}"],
                check=True
            )
            return f"✅ Wallpaper set to: {abs_path}"
    except Exception as e:
        return f"❌ Error setting wallpaper: {e}"
