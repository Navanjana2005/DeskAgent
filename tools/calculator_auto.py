import os
import re
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


# Maps expression characters to the Name of the corresponding Calculator button.
# These Names match the standard Windows 11 Calculator (Standard mode).
BUTTON_MAP = {
    "0": "Zero", "1": "One", "2": "Two", "3": "Three", "4": "Four",
    "5": "Five", "6": "Six", "7": "Seven", "8": "Eight", "9": "Nine",
    "+": "Plus", "-": "Minus", "*": "Multiply by", "/": "Divide by",
    ".": "Decimal separator", "%": "Percent",
}

# Only these characters are allowed in an expression. Anything else is rejected
# before we touch the UI, so we never leave Calculator mid-sequence on bad input.
VALID_EXPRESSION_RE = re.compile(r"^[0-9+\-*/.% ]+$")

CLICK_DELAY = 0.15  # seconds between button clicks, avoids dropped inputs
WINDOW_TIMEOUT = 8  # seconds to wait for the Calculator window to appear
RESULT_WAIT = 0.3   # seconds to wait after '=' before reading the result


def _get_calculator_window():
    """Tries the known ClassName/SubName combos for Calculator across Windows
    versions and returns the first live window control found, or None."""
    candidates = [
        dict(searchDepth=1, ClassName="ApplicationFrameWindow", SubName="Calculator"),
        dict(searchDepth=1, ClassName="Windows.UI.Core.CoreWindow", SubName="Calculator"),
        dict(searchDepth=1, SubName="Calculator"),
    ]
    for kwargs in candidates:
        window = auto.WindowControl(**kwargs)
        if window.Exists(WINDOW_TIMEOUT / len(candidates)):
            return window
    return None


def _clean_result(raw: str) -> str:
    """Calculator's result control sometimes returns text like
    'Display is 10' or 'Display is 7 + 3= 10'. Extract the trailing value."""
    if "Display is" in raw:
        raw = raw.split("Display is", 1)[-1]
    if "=" in raw:
        raw = raw.rsplit("=", 1)[-1]
    return raw.strip()


@tool
def calculator_control(expression: str) -> str:
    """Opens Windows Calculator and evaluates a math expression by clicking
    the on-screen buttons (via UI Automation), then reads back the result.

    Args:
        expression: A math expression using digits, +, -, *, /, ., % and
            spaces only, e.g. "7+3*2" or "45.5 - 10%". Parentheses are not
            supported in Standard mode.
    """
    if not HAS_UIAUTOMATION:
        return "❌ uiautomation not installed. Run: pip install uiautomation"
    if not HAS_APPOPENER:
        return "❌ AppOpener not installed. Run: pip install AppOpener"

    expression = expression.strip()
    if not expression:
        return "❌ Empty expression."
    if not VALID_EXPRESSION_RE.match(expression):
        return (
            "❌ Invalid characters in expression. Only digits, "
            "+ - * / . % and spaces are allowed."
        )

    try:
        app_open("Calculator", match_closest=True, throw_error=True)
        time.sleep(2)

        calc_window = _get_calculator_window()
        if calc_window is None:
            return "❌ Calculator window did not appear in time."

        calc_window.SetTopmost(True)
        calc_window.SetActive()

        # Reset to a clean state before entering the new expression.
        clear_button = calc_window.ButtonControl(Name="Clear")
        if clear_button.Exists(2):
            clear_button.Click()
            time.sleep(CLICK_DELAY)

        clicked = []
        for char in expression:
            if char == " ":
                continue
            button_name = BUTTON_MAP.get(char)
            if button_name is None:
                return f"❌ Unsupported character: '{char}'"

            button = calc_window.ButtonControl(Name=button_name)
            if not button.Exists(2):
                return f"❌ Could not find button for '{char}' ({button_name})"

            button.Click()
            clicked.append(char)
            time.sleep(CLICK_DELAY)

        equals_button = calc_window.ButtonControl(Name="Equals")
        if not equals_button.Exists(2):
            return "❌ Could not find the Equals button."
        equals_button.Click()
        time.sleep(RESULT_WAIT)

        result_control = calc_window.TextControl(AutomationId="CalculatorResults")
        if not result_control.Exists(2):
            return "❌ Could not read the result display."

        result = _clean_result(result_control.Name)

        return (
            f"✅ Calculation complete!\n"
            f"Expression: {expression}\n"
            f"Result:     {result}"
        )

    except Exception as e:
        return f"❌ Error running calculator automation: {e}"