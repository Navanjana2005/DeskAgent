"""
Send a message through an INSTALLED messaging app (WhatsApp, Telegram,
Messenger, ...) with the full step sequence encoded in Python, not left to
the agent's own reasoning.

WHY ONE COMPOSED TOOL INSTEAD OF LOOSE PRIMITIVES:
"Open WhatsApp and send Amma 'Hi'" requires a specific ordered sequence
(open -> click search -> type contact -> wait for filter -> click result ->
click message box -> type message -> send). Leaving that sequencing to the
agent's step-by-step tool calls is unreliable. This tool guarantees the
sequence by doing it all in one function call: the agent only needs to
supply app_name, contact_name, and message.

ADDING A NEW APP:
Most desktop messaging apps share the same UI shape (a search field, a
filtered contact/chat list, a message box). To support a new app, add one
entry to APP_CONFIGS below -- no new function needed. Use AutomationSpy to
find the real Name values for that app's search box and message box.
"""

import functools
import time
from langchain_core.tools import tool

try:
    import uiautomation as auto
    HAS_UIAUTOMATION = True
except ImportError:
    HAS_UIAUTOMATION = False

try:
    from AppOpener import open as app_open
    HAS_APPOPENER = True
except ImportError:
    HAS_APPOPENER = False


def with_com_init(func):
    """Initializes COM on whichever thread this runs on -- required because
    uiautomation calls COM, and COM must be initialized per-thread. Fixes
    'CoInitialize has not been called' errors when tools run off the main
    thread (e.g. via a thread pool or asyncio.to_thread)."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if not HAS_UIAUTOMATION:
            return func(*args, **kwargs)
        with auto.UIAutomationInitializerInThread():
            return func(*args, **kwargs)
    return wrapper


WINDOW_TIMEOUT = 8
CONTROL_TIMEOUT = 3
FILTER_WAIT = 1.2
SEND_WAIT = 0.4

# One entry per supported app. search_name/message_name are the Name values
# AutomationSpy shows for that app's search box and message compose box.
# window_subname matches the app's window title (partial match, since some
# apps prefix it with an unread count like "(3) WhatsApp").
APP_CONFIGS = {
    "whatsapp": {
        "process_name": "WhatsApp",
        "window_subname": "WhatsApp",
        "search_name": "Search or start a new chat",
        "message_name": "Type a message",
        "list_name": "Chat list",
    },
    "telegram": {
        "process_name": "Telegram",
        "window_subname": "Telegram",
        "search_name": "Search",
        "message_name": "Message",
        "list_name": None,  # falls back to generic list detection
    },
    "messenger": {
        "process_name": "Messenger",
        "window_subname": "Messenger",
        "search_name": "Search Messenger",
        "message_name": "Aa",
        "list_name": None,
    },
}


def _set_clipboard_text(text: str):
    if hasattr(auto, "SetClipboardText"):
        auto.SetClipboardText(text)
    else:
        import subprocess
        subprocess.run("clip", input=text.encode("utf-16-le"), check=True)


def _paste_into(control):
    control.Click()
    time.sleep(0.2)
    control.SendKeys("{Ctrl}a", waitTime=0.05)
    control.SendKeys("{Delete}", waitTime=0.05)
    control.SendKeys("{Ctrl}v", waitTime=0.05)


def _get_app_window(subname):
    window = auto.WindowControl(searchDepth=1, SubName=subname)
    if window.Exists(WINDOW_TIMEOUT):
        return window
    return None


def _find_first_list_result(window, list_name):
    if list_name:
        results_container = window.Control(searchDepth=20, Name=list_name)
        if not results_container.Exists(CONTROL_TIMEOUT):
            results_container = window.ListControl(searchDepth=20)
    else:
        results_container = window.ListControl(searchDepth=20)

    if not results_container.Exists(CONTROL_TIMEOUT):
        return None

    children = results_container.GetChildren()
    return children[0] if children else None


def _find_message_box(window, message_name):
    box = window.EditControl(searchDepth=20, Name=message_name)
    if box.Exists(CONTROL_TIMEOUT):
        return box

    # Fallback: last Edit control in the tree tends to be the compose box.
    edits = []

    def _walk(ctrl, depth=0):
        if depth > 25:
            return
        if ctrl.ControlTypeName == "EditControl":
            edits.append(ctrl)
        for child in ctrl.GetChildren():
            _walk(child, depth + 1)

    _walk(window)
    return edits[-1] if len(edits) >= 2 else None


@tool
@with_com_init
def send_message_to_contact(
    app_name: str,
    contact_name: str,
    message: str,
    confirmed_by_user: bool = False,
) -> str:
    """Opens an installed messaging app, searches for a contact, selects
    their chat, and sends them a text message. Handles the full sequence
    internally: open app -> click search bar -> type contact name -> wait
    for the filtered list -> click the top result -> click the message box
    -> type the message -> send. No matter what, you must follow this sequence exactly, or the message will not be sent.

    Args:
        app_name: Which app to use. Supported: "whatsapp", "telegram", "messenger".
        contact_name: Name of the contact/chat to message, e.g. "Jhon".
        message: The text message to send.
        confirmed_by_user: Set True only after the user explicitly confirms
            sending this exact message to this exact contact.
    """
    if not confirmed_by_user:
        return (
            f"⛔ Not sent. Confirm sending this exact message to "
            f"'{contact_name}' via {app_name}, then retry with "
            "confirmed_by_user=True."
        )
    if not HAS_UIAUTOMATION:
        return "❌ uiautomation not installed. Run: pip install uiautomation"
    if not HAS_APPOPENER:
        return "❌ AppOpener not installed. Run: pip install AppOpener"

    key = app_name.strip().lower()
    config = APP_CONFIGS.get(key)
    if config is None:
        supported = ", ".join(APP_CONFIGS.keys())
        return f"❌ Unsupported app '{app_name}'. Supported apps: {supported}"

    contact_name = contact_name.strip()
    message = message.strip()
    if not contact_name:
        return "❌ No contact name provided."
    if not message:
        return "❌ No message text provided."

    try:
        # Step 1: open the app
        app_open(config["process_name"], match_closest=True, throw_error=True)
        time.sleep(2)

        window = _get_app_window(config["window_subname"])
        if window is None:
            return f"❌ {config['process_name']} window did not appear in time."
        window.SetTopmost(True)
        window.SetActive()

        # Step 2: click the search bar and type the contact name
        search_box = window.EditControl(searchDepth=20, Name=config["search_name"])
        if not search_box.Exists(CONTROL_TIMEOUT):
            return f"❌ Could not find the search bar in {config['process_name']}."
        _set_clipboard_text(contact_name)
        _paste_into(search_box)
        time.sleep(FILTER_WAIT)

        # Step 3: select the first matching result
        result_item = _find_first_list_result(window, config["list_name"])
        if result_item is None:
            return f"❌ No chat found matching '{contact_name}'."
        found_name = result_item.Name or contact_name
        result_item.Click()
        time.sleep(0.8)

        # Step 4: find the message box and type the message
        message_box = _find_message_box(window, config["message_name"])
        if message_box is None:
            return (
                f"❌ Selected the chat but could not find the message box "
                f"in {config['process_name']}. Verify 'message_name' in "
                f"APP_CONFIGS against AutomationSpy."
            )
        _set_clipboard_text(message)
        _paste_into(message_box)
        time.sleep(SEND_WAIT)

        # Step 5: send
        message_box.SendKeys("{Enter}", waitTime=0.05)

        return (
            f"✅ Message sent via {config['process_name']}!\n"
            f"Contact matched: {found_name}\n"
            f"Message: {message}"
        )

    except Exception as e:
        return f"❌ Error sending message via {app_name}: {e}"