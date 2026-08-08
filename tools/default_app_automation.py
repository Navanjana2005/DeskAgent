"""
Generic Windows UI-automation primitives for the agent.

Instead of writing one @tool per specific action (turn_on_wifi,
send_whatsapp_message, calculator_control, ...), give the agent a handful
of general primitives. The agent's own reasoning (in your LangGraph ReAct
loop) decides which control to inspect, click, or type into, based on what
inspect_screen() reports back -- the same way a human would look at the
screen, then act.

Typical agent loop for ANY task, e.g. "turn on Bluetooth":
  1. open_app("ms-settings:bluetooth")
  2. inspect_screen()                -> agent reads the returned tree,
                                         finds a control named "Bluetooth"
                                         with ControlType Button/Toggle
  3. toggle_set("Bluetooth", True)   -> or click("Bluetooth") if it's a
                                         plain button, not a toggle
  4. inspect_screen()                -> agent verifies the new state

No new Python needed for "turn on Airplane mode" -- same four tools, agent
just targets a different Name.
"""

import functools
import subprocess
import time
from langchain_core.tools import BaseTool, tool

try:
    import uiautomation as auto
    HAS_UIAUTOMATION = True
except ImportError:
    HAS_UIAUTOMATION = False


def with_com_init(func):
    """Ensures COM is initialized on whatever thread this tool call runs on.

    uiautomation talks to Windows via COM, which requires CoInitialize()
    per-thread. If the agent executes tools through a thread pool or
    asyncio.to_thread, each call may land on a different worker thread that
    never had COM initialized -- causing 'CoInitialize has not been called'
    errors. Wrapping each tool body in UIAutomationInitializerInThread()
    fixes this regardless of which thread the call happens to run on.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if not HAS_UIAUTOMATION:
            return func(*args, **kwargs)
        with auto.UIAutomationInitializerInThread():
            return func(*args, **kwargs)
    return wrapper

try:
    from AppOpener import open as app_open
    HAS_APPOPENER = True
except ImportError:
    HAS_APPOPENER = False


MAX_INSPECT_DEPTH = 10       # how deep to walk the control tree
MAX_INSPECT_ELEMENTS = 150  # cap so the output stays small enough for the LLM
CONTROL_TIMEOUT = 4


def _active_window():
    """Returns the current foreground window as a uiautomation control."""
    return auto.GetForegroundControl()


def _find_control(name: str, control_type: str = None):
    """Searches the active window (and its descendants) for a control whose
    Name contains `name` (case-insensitive), optionally filtered by
    ControlType (e.g. 'Button', 'Edit', 'CheckBox')."""
    window = _active_window()
    name_lower = name.lower()
    match = [None]

    def _walk(ctrl, depth=0):
        if match[0] is not None or depth > MAX_INSPECT_DEPTH:
            return
        try:
            ctrl_name = (ctrl.Name or "").lower()
            ctrl_type = ctrl.ControlTypeName.replace("Control", "")
        except Exception:
            return
        if name_lower in ctrl_name:
            if control_type is None or control_type.lower() == ctrl_type.lower():
                match[0] = ctrl
                return
        for child in ctrl.GetChildren():
            _walk(child, depth + 1)

    _walk(window)
    return match[0]


@tool
def default_open_app(app_or_uri: str) -> str:
    """Opens an application by name (e.g. 'Calculator', 'Notepad', 'Settings', 'File Explorer', 'Microsoft Store') or a
    Windows URI (e.g. 'ms-settings:bluetooth', 'ms-settings:network-wifi').

    Args:
        app_or_uri: App name to launch via AppOpener, or a 'ms-settings:...'
            / other shell URI to open directly.
    """
    if not HAS_APPOPENER and not app_or_uri.startswith(("ms-settings:", "http")):
        return "❌ AppOpener not installed. Run: pip install AppOpener"
    try:
        if app_or_uri.startswith(("ms-settings:", "http", "ms-")):
            subprocess.Popen(f'start {app_or_uri}', shell=True)
        else:
            app_open(app_or_uri, match_closest=True, throw_error=True)
        time.sleep(2)
        return f"✅ Opened '{app_or_uri}'."
    except Exception as e:
        return f"❌ Could not open '{app_or_uri}': {e}"


@tool
@with_com_init
def inspect_screen() -> str:
    """Reads the current foreground window's UI control tree and returns it
    as text, so the agent can decide what to click, type into, or toggle.
    Call this after opening or navigating to a screen, and again after any
    action to confirm the result.
    """
    if not HAS_UIAUTOMATION:
        return "❌ uiautomation not installed. Run: pip install uiautomation"
    try:
        window = _active_window()
        if window is None:
            return "❌ No foreground window detected."

        lines = [f"Window: {window.Name}"]
        count = [0]

        def _walk(ctrl, depth=0):
            if count[0] >= MAX_INSPECT_ELEMENTS or depth > MAX_INSPECT_DEPTH:
                return
            name = ctrl.Name
            ctrl_type = ctrl.ControlTypeName.replace("Control", "")
            if name:
                lines.append(f"{'  ' * depth}- [{ctrl_type}] \"{name}\"")
                count[0] += 1
            for child in ctrl.GetChildren():
                _walk(child, depth + 1)

        _walk(window)
        return "\n".join(lines)
    except Exception as e:
        return f"❌ Error inspecting screen: {e}"


@tool
@with_com_init
def click(name: str, control_type: str = None) -> str:
    """Clicks a UI control in the current foreground window, matched by a
    (partial, case-insensitive) Name. Use after inspect_screen() to confirm
    the control exists with that Name.

    Args:
        name: Visible Name of the control to click, e.g. "Send", "Wi-Fi".
        control_type: Optional filter, e.g. "Button", "CheckBox", "ListItem".
    """
    if not HAS_UIAUTOMATION:
        return "❌ uiautomation not installed. Run: pip install uiautomation"
    try:
        control = _find_control(name, control_type)
        if control is None or not control.Exists(CONTROL_TIMEOUT):
            return f"❌ No control found matching '{name}'."
        control.Click()
        return f"✅ Clicked '{name}'."
    except Exception as e:
        return f"❌ Error clicking '{name}': {e}"


@tool
@with_com_init
def type_text(name: str, text: str) -> str:
    """Types text into an editable control (Edit box) matched by Name, using
    clipboard paste so special characters and non-Latin text work correctly.

    Args:
        name: Visible Name of the text field, e.g. "Search or start a new chat".
        text: The text to type into it.
    """
    if not HAS_UIAUTOMATION:
        return "❌ uiautomation not installed. Run: pip install uiautomation"
    try:
        control = _find_control(name, control_type="Edit")
        if control is None or not control.Exists(CONTROL_TIMEOUT):
            return f"❌ No editable field found matching '{name}'."

        if hasattr(auto, "SetClipboardText"):
            auto.SetClipboardText(text)
        else:
            import subprocess as sp
            sp.run("clip", input=text.encode("utf-16-le"), check=True)

        control.Click()
        time.sleep(0.15)
        control.SendKeys("{Ctrl}a", waitTime=0.05)
        control.SendKeys("{Ctrl}v", waitTime=0.05)
        return f"✅ Typed text into '{name}'."
    except Exception as e:
        return f"❌ Error typing into '{name}': {e}"


@tool
@with_com_init
def toggle_set(name: str, turn_on: bool) -> str:
    """Sets a toggle/checkbox control to a specific on/off state, checking
    its CURRENT state first so it only clicks if a change is actually
    needed. Use this instead of click() for any toggle-style control.

    Args:
        name: Visible Name of the toggle, e.g. "Wi-Fi", "Bluetooth", "Airplane mode".
        turn_on: True to turn it on, False to turn it off.
    """
    if not HAS_UIAUTOMATION:
        return "❌ uiautomation not installed. Run: pip install uiautomation"
    try:
        control = _find_control(name)
        if control is None or not control.Exists(CONTROL_TIMEOUT):
            return f"❌ No toggle found matching '{name}'."

        toggle_pattern = control.GetTogglePattern()
        if toggle_pattern is None:
            # Not a real toggle control -- fall back to a plain click,
            # but warn the caller since we can't verify state.
            control.Click()
            return (
                f"⚠️ '{name}' isn't a standard toggle control (clicked once, "
                f"state unverified). Use inspect_screen() to confirm."
            )

        is_on = toggle_pattern.ToggleState == auto.ToggleState.On
        if is_on == turn_on:
            return f"✅ '{name}' is already {'on' if turn_on else 'off'}."

        control.Click()
        time.sleep(0.3)
        return f"✅ '{name}' switched to {'on' if turn_on else 'off'}."
    except Exception as e:
        return f"❌ Error setting toggle '{name}': {e}"


@tool
@with_com_init
def press_key(keys: str) -> str:
    """Sends a keyboard shortcut or key press to the current foreground
    window, e.g. 'Enter', '{Ctrl}c', '{Alt}{F4}'. Uses uiautomation's
    SendKeys syntax.

    Args:
        keys: Key sequence in uiautomation SendKeys format.
    """
    if not HAS_UIAUTOMATION:
        return "❌ uiautomation not installed. Run: pip install uiautomation"
    try:
        window = _active_window()
        window.SendKeys(keys, waitTime=0.05)
        return f"✅ Sent keys: {keys}"
    except Exception as e:
        return f"❌ Error sending keys '{keys}': {e}"