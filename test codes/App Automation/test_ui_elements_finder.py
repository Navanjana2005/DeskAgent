# import subprocess
# import time
# import uiautomation as auto

# # 1. Launch Windows 11 Settings App using its URI
# subprocess.Popen("start ms-settings:", shell=True)
# time.sleep(2)  # Wait for Settings to load

# # 2. Locate the main Settings Window
# settings_win = auto.WindowControl(
#     searchDepth=2, ClassName="ApplicationFrameWindow", SubName="Settings"
# )

# # Fallback for newer WinUI 3 Settings window class names if needed
# if not settings_win.Exists(maxSearchSeconds=3):
#     settings_win = auto.WindowControl(searchDepth=2, Name="Settings")

# settings_win.SetActive()
# print(f"Found Window: {settings_win.Name} ({settings_win.ClassName})")

# # 3. Walk through the first few levels of children and print their identifiers
# for control, depth in auto.WalkControl(settings_win, maxDepth=4):
#     # Indent based on tree depth for readability
#     indent = "  " * depth
#     print(
#         f"{indent}[{control.ControlTypeName}] "
#         f"Name: '{control.Name}' | "
#         f"AutomationId: '{control.AutomationId}' | "
#         f"ClassName: '{control.ClassName}'"
#     )

import uiautomation as auto, subprocess

# Launch Settings to Network page via URI
subprocess.Popen('start ms-settings:network', shell=True)
settings = auto.WindowControl(ClassName='ApplicationFrameWindow', Name='Settings', foundIndex=1)
settings.SetActive()  # ensure in foreground
# Click on the "Wi-Fi" toggle by name (ControlType=Button/Toggle)
wifiToggle = settings.ButtonControl(Name='Wi-Fi')
if wifiToggle.Exists(5):  # wait up to 5s for control
    wifiToggle.Click()
else:
    print("Wi-Fi toggle not found (no adapter or access disabled)")
