from langchain_core.tools import tool
import subprocess
import time
import uiautomation as auto

@tool
def turn_on_wifi() -> str:
    """
    Launches the Windows 11 Settings app and turns on Wi-Fi.
    """
    # Launch Settings to Network page via URI
    subprocess.Popen('start ms-settings:network', shell=True)
    time.sleep(2)  # Wait for Settings to load

    settings = auto.WindowControl(ClassName='ApplicationFrameWindow', Name='Settings', foundIndex=1)
    settings.SetActive()  # ensure in foreground

    # Click on the "Wi-Fi" toggle by name (ControlType=Button/Toggle)
    wifiToggle = settings.ButtonControl(Name='Wi-Fi')
    if wifiToggle.Exists(5):  # wait up to 5s for control
        wifiToggle.Click()
        return "Wi-Fi toggle clicked."
    else:
        return "Wi-Fi toggle not found (no adapter or access disabled)."

@tool 
def turn_off_wifi() -> str:
    """
    Launches the Windows 11 Settings app and turns off Wi-Fi.
    """
    # Launch Settings to Network page via URI
    subprocess.Popen('start ms-settings:network', shell=True)
    time.sleep(2)  # Wait for Settings to load

    settings = auto.WindowControl(ClassName='ApplicationFrameWindow', Name='Settings', foundIndex=1)
    settings.SetActive()  # ensure in foreground

    # Click on the "Wi-Fi" toggle by name (ControlType=Button/Toggle)
    wifiToggle = settings.ButtonControl(Name='Wi-Fi')
    if wifiToggle.Exists(5):  # wait up to 5s for control
        wifiToggle.Click()
        return "Wi-Fi toggle clicked."
    else:
        return "Wi-Fi toggle not found (no adapter or access disabled)."

@tool
def turn_on_bluetooth() -> str:
    """
    Launches the Windows 11 Settings app and turns on Bluetooth.
    """
    # Launch Settings to Bluetooth page via URI
    subprocess.Popen('start ms-settings:bluetooth', shell=True)
    time.sleep(2)  # Wait for Settings to load

    settings = auto.WindowControl(ClassName='ApplicationFrameWindow', Name='Settings', foundIndex=1)
    settings.SetActive()  # ensure in foreground

    # Click on the "Bluetooth" toggle by name (ControlType=Button/Toggle)
    bluetoothToggle = settings.ButtonControl(Name='Bluetooth')
    if bluetoothToggle.Exists(5):  # wait up to 5s for control
        bluetoothToggle.Click()
        return "Bluetooth toggle clicked."
    else:
        return "Bluetooth toggle not found (no adapter or access disabled)."