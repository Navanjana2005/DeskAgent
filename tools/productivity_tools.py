"""
tools/productivity_tools.py
Productivity tools: notes, todos, datetime, unit converter, timezone,
pomodoro timer, and daily summary.

All tools use local JSON storage — no API keys required.
Storage files: storage/notes.json, storage/todos.json, storage/preferences.json
"""

import os
import json
import uuid
import math
import datetime
import difflib
import threading
from typing import Optional
from langchain_core.tools import tool

try:
    from plyer import notification as plyer_notif
    HAS_PLYER = True
except ImportError:
    HAS_PLYER = False

try:
    import pytz
    HAS_PYTZ = True
except ImportError:
    HAS_PYTZ = False

try:
    import winsound
    HAS_WINSOUND = True
except ImportError:
    HAS_WINSOUND = False

# ─────────────────────────────────────────────────────────────────────────────
# STORAGE PATHS
# ─────────────────────────────────────────────────────────────────────────────

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_STORAGE_DIR = os.path.join(_BASE_DIR, "storage")
_NOTES_FILE = os.path.join(_STORAGE_DIR, "notes.json")
_TODOS_FILE = os.path.join(_STORAGE_DIR, "todos.json")
_PREFS_FILE = os.path.join(_STORAGE_DIR, "preferences.json")


def _load_json(path: str) -> dict | list:
    os.makedirs(_STORAGE_DIR, exist_ok=True)
    if not os.path.exists(path):
        default = {} if path != _TODOS_FILE else []
        _save_json(path, default)
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_json(path: str, data) -> None:
    os.makedirs(_STORAGE_DIR, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _play_alert():
    try:
        if os.name == "nt" and HAS_WINSOUND:
            winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
        else:
            print("\a", end="", flush=True)
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────────────────
# NOTES TOOLS
# ─────────────────────────────────────────────────────────────────────────────

@tool
def save_note(title: str, content: str) -> str:
    """Saves a persistent note with a title and content to local storage.

    Args:
        title: Note title (used as the lookup key).
        content: The text content of the note.
    """
    try:
        notes = _load_json(_NOTES_FILE)
        notes[title] = {
            "content": content,
            "created": datetime.datetime.now().isoformat(),
            "updated": datetime.datetime.now().isoformat(),
        }
        _save_json(_NOTES_FILE, notes)
        return f"✅ Note '{title}' saved."
    except Exception as e:
        return f"❌ Error saving note: {e}"


@tool
def recall_note(keyword: str) -> str:
    """Searches saved notes by title or content using fuzzy matching.

    Args:
        keyword: Word or phrase to search for in note titles and content.
    """
    try:
        notes = _load_json(_NOTES_FILE)
        if not notes:
            return "No notes saved yet."

        keyword_lower = keyword.lower()
        results = []
        for title, data in notes.items():
            if keyword_lower in title.lower() or keyword_lower in data["content"].lower():
                results.append((title, data))

        if not results:
            # Fuzzy fallback on titles
            close = difflib.get_close_matches(keyword, notes.keys(), n=3, cutoff=0.4)
            results = [(t, notes[t]) for t in close]

        if not results:
            return f"No notes found matching '{keyword}'."

        output = []
        for title, data in results[:5]:
            snippet = data["content"][:200]
            output.append(
                f"📝 {title}\n"
                f"   Updated: {data.get('updated', 'N/A')}\n"
                f"   {snippet}{'...' if len(data['content']) > 200 else ''}"
            )
        return "\n\n".join(output)
    except Exception as e:
        return f"❌ Error: {e}"


@tool
def list_notes() -> str:
    """Lists all saved notes with their titles and last updated timestamps."""
    try:
        notes = _load_json(_NOTES_FILE)
        if not notes:
            return "No notes saved yet."
        lines = [f"📒 Saved Notes ({len(notes)}):\n"]
        for i, (title, data) in enumerate(notes.items(), 1):
            lines.append(f"  {i}. {title}  |  Updated: {data.get('updated', 'N/A')[:10]}")
        return "\n".join(lines)
    except Exception as e:
        return f"❌ Error: {e}"


@tool
def delete_note(title: str) -> str:
    """Deletes a saved note by its exact title.

    Args:
        title: The title of the note to delete.
    """
    try:
        notes = _load_json(_NOTES_FILE)
        if title not in notes:
            # Try case-insensitive
            match = next((k for k in notes if k.lower() == title.lower()), None)
            if not match:
                return f"❌ Note '{title}' not found."
            title = match
        del notes[title]
        _save_json(_NOTES_FILE, notes)
        return f"✅ Note '{title}' deleted."
    except Exception as e:
        return f"❌ Error: {e}"


# ─────────────────────────────────────────────────────────────────────────────
# PREFERENCES TOOLS
# ─────────────────────────────────────────────────────────────────────────────

@tool
def save_preference(key: str, value: str) -> str:
    """Saves a user preference as a key-value pair to persistent storage.

    Args:
        key: Preference name (e.g., 'name', 'default_browser', 'downloads_folder').
        value: The preference value.
    """
    try:
        prefs = _load_json(_PREFS_FILE)
        prefs[key] = value
        _save_json(_PREFS_FILE, prefs)
        return f"✅ Saved preference: {key} = {value}"
    except Exception as e:
        return f"❌ Error: {e}"


@tool
def get_preference(key: str) -> str:
    """Retrieves a saved user preference by key.

    Args:
        key: The preference name to look up.
    """
    try:
        prefs = _load_json(_PREFS_FILE)
        if key in prefs:
            return f"{key} = {prefs[key]}"
        # List all if key not found
        if not prefs:
            return "No preferences saved yet."
        keys = list(prefs.keys())
        return f"❌ Preference '{key}' not found.\nAvailable preferences: {', '.join(keys)}"
    except Exception as e:
        return f"❌ Error: {e}"


# ─────────────────────────────────────────────────────────────────────────────
# TO-DO TOOLS
# ─────────────────────────────────────────────────────────────────────────────

@tool
def add_todo(task: str, priority: str = "medium", due_date: str = "") -> str:
    """Adds a task to the to-do list with optional priority and due date.

    Args:
        task: Task description.
        priority: 'low', 'medium', or 'high' (default 'medium').
        due_date: Optional due date in YYYY-MM-DD format (e.g., '2025-08-01').
    """
    try:
        todos = _load_json(_TODOS_FILE)
        if not isinstance(todos, list):
            todos = []
        new_task = {
            "id": str(uuid.uuid4())[:8],
            "task": task,
            "priority": priority.lower(),
            "due_date": due_date,
            "status": "pending",
            "created": datetime.datetime.now().isoformat(),
        }
        todos.append(new_task)
        _save_json(_TODOS_FILE, todos)
        priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(priority.lower(), "⚪")
        return f"✅ Task added [{new_task['id']}] {priority_emoji} {task}"
    except Exception as e:
        return f"❌ Error: {e}"


@tool
def list_todos(filter_status: str = "all", filter_priority: str = "") -> str:
    """Lists to-do tasks with optional filtering.

    Args:
        filter_status: 'all', 'pending', or 'done' (default 'all').
        filter_priority: Filter by 'high', 'medium', or 'low' (leave empty for all).
    """
    try:
        todos = _load_json(_TODOS_FILE)
        if not isinstance(todos, list):
            todos = []
        if not todos:
            return "📋 No tasks yet. Use add_todo to add some!"

        filtered = todos
        if filter_status != "all":
            filtered = [t for t in filtered if t.get("status") == filter_status]
        if filter_priority:
            filtered = [t for t in filtered if t.get("priority") == filter_priority.lower()]

        if not filtered:
            return f"No tasks found with filter: status={filter_status}, priority={filter_priority}"

        p_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}
        s_emoji = {"pending": "⬜", "done": "✅"}

        lines = [f"📋 Tasks ({len(filtered)}):\n"]
        for t in filtered:
            s = s_emoji.get(t.get("status", "pending"), "⬜")
            p = p_emoji.get(t.get("priority", "medium"), "⚪")
            due = f" | Due: {t['due_date']}" if t.get("due_date") else ""
            lines.append(f"  {s} [{t['id']}] {p} {t['task']}{due}")
        return "\n".join(lines)
    except Exception as e:
        return f"❌ Error: {e}"


@tool
def complete_todo(task_id: str) -> str:
    """Marks a to-do task as completed.

    Args:
        task_id: The short ID of the task (shown in list_todos output).
    """
    try:
        todos = _load_json(_TODOS_FILE)
        if not isinstance(todos, list):
            return "❌ No tasks found."
        for t in todos:
            if t["id"] == task_id:
                t["status"] = "done"
                t["completed"] = datetime.datetime.now().isoformat()
                _save_json(_TODOS_FILE, todos)
                return f"✅ Task [{task_id}] marked as done: {t['task']}"
        return f"❌ Task ID '{task_id}' not found."
    except Exception as e:
        return f"❌ Error: {e}"


@tool
def delete_todo(task_id: str) -> str:
    """Removes a task from the to-do list.

    Args:
        task_id: The short ID of the task to delete.
    """
    try:
        todos = _load_json(_TODOS_FILE)
        if not isinstance(todos, list):
            return "❌ No tasks found."
        original_len = len(todos)
        todos = [t for t in todos if t["id"] != task_id]
        if len(todos) == original_len:
            return f"❌ Task ID '{task_id}' not found."
        _save_json(_TODOS_FILE, todos)
        return f"✅ Task [{task_id}] deleted."
    except Exception as e:
        return f"❌ Error: {e}"


# ─────────────────────────────────────────────────────────────────────────────
# DATE & TIME TOOLS
# ─────────────────────────────────────────────────────────────────────────────

@tool
def get_current_datetime() -> str:
    """Returns the current date, time, day of the week, and week number."""
    now = datetime.datetime.now()
    return (
        f"🕐 Current Date & Time\n"
        f"{'─' * 30}\n"
        f"Date:     {now.strftime('%Y-%m-%d')}\n"
        f"Time:     {now.strftime('%H:%M:%S')}\n"
        f"Day:      {now.strftime('%A')}\n"
        f"Week:     Week {now.strftime('%W')} of {now.year}\n"
        f"ISO:      {now.isoformat()}"
    )


@tool
def time_zone_converter(time_str: str, from_tz: str, to_tz: str) -> str:
    """Converts a time from one timezone to another.

    Args:
        time_str: Time to convert in HH:MM format (e.g., '14:30').
        from_tz: Source timezone name (e.g., 'US/Eastern', 'Asia/Colombo', 'UTC').
        to_tz: Target timezone name (e.g., 'Europe/London', 'Asia/Tokyo').
    """
    if not HAS_PYTZ:
        return "❌ pytz not installed. Run: pip install pytz"
    try:
        source_tz = pytz.timezone(from_tz)
        target_tz = pytz.timezone(to_tz)
        now = datetime.datetime.now()
        hour, minute = map(int, time_str.split(":"))
        dt = datetime.datetime(now.year, now.month, now.day, hour, minute)
        dt_source = source_tz.localize(dt)
        dt_target = dt_source.astimezone(target_tz)
        return (
            f"🌍 Timezone Conversion\n"
            f"{'─' * 30}\n"
            f"Input:  {time_str} {from_tz}\n"
            f"Output: {dt_target.strftime('%H:%M')} {to_tz}\n"
            f"Date:   {dt_target.strftime('%Y-%m-%d')} (may differ if crossing midnight)"
        )
    except Exception as e:
        return f"❌ Error: {e}\nTip: Use timezone names like 'Asia/Colombo', 'US/Eastern', 'Europe/London', 'UTC'"


# ─────────────────────────────────────────────────────────────────────────────
# UNIT CONVERTER
# ─────────────────────────────────────────────────────────────────────────────

_UNIT_TABLE = {
    # Length
    "km": ("length", 1000), "m": ("length", 1), "cm": ("length", 0.01),
    "mm": ("length", 0.001), "mi": ("length", 1609.34), "yd": ("length", 0.9144),
    "ft": ("length", 0.3048), "in": ("length", 0.0254),
    # Weight
    "kg": ("weight", 1), "g": ("weight", 0.001), "mg": ("weight", 1e-6),
    "lb": ("weight", 0.453592), "oz": ("weight", 0.0283495), "t": ("weight", 1000),
    # Data
    "b": ("data", 1), "kb": ("data", 1024), "mb": ("data", 1024**2),
    "gb": ("data", 1024**3), "tb": ("data", 1024**4),
    # Speed
    "mps": ("speed", 1), "kph": ("speed", 1/3.6), "mph": ("speed", 0.44704),
    "knot": ("speed", 0.514444),
    # Area
    "sqm": ("area", 1), "sqkm": ("area", 1e6), "sqft": ("area", 0.092903),
    "sqmi": ("area", 2.59e6), "ha": ("area", 10000), "acre": ("area", 4046.86),
}


@tool
def unit_converter(value: float, from_unit: str, to_unit: str) -> str:
    """Converts between units of length, weight, data size, speed, or area.

    Args:
        value: The numeric value to convert.
        from_unit: Source unit (e.g., 'km', 'kg', 'mb', 'mph', 'ft').
        to_unit: Target unit (e.g., 'mi', 'lb', 'gb', 'kph', 'm').

    Temperature: Use from_unit='C', 'F', or 'K' for temperature conversion.

    Supported units:
      Length: km, m, cm, mm, mi, yd, ft, in
      Weight: kg, g, mg, lb, oz, t
      Data:   b, kb, mb, gb, tb
      Speed:  mps, kph, mph, knot
      Area:   sqm, sqkm, sqft, sqmi, ha, acre
    """
    try:
        fu = from_unit.lower()
        tu = to_unit.lower()

        # Temperature special case
        temp_units = {"c", "f", "k"}
        if fu in temp_units or tu in temp_units:
            if fu == "c" and tu == "f":
                result = value * 9 / 5 + 32
            elif fu == "f" and tu == "c":
                result = (value - 32) * 5 / 9
            elif fu == "c" and tu == "k":
                result = value + 273.15
            elif fu == "k" and tu == "c":
                result = value - 273.15
            elif fu == "f" and tu == "k":
                result = (value - 32) * 5 / 9 + 273.15
            elif fu == "k" and tu == "f":
                result = (value - 273.15) * 9 / 5 + 32
            else:
                return f"❌ Unknown temperature units: {from_unit} → {to_unit}"
            return f"🌡️  {value} {from_unit.upper()} = {result:.4f} {to_unit.upper()}"

        if fu not in _UNIT_TABLE:
            return f"❌ Unknown unit '{from_unit}'. Supported: {', '.join(_UNIT_TABLE.keys())}"
        if tu not in _UNIT_TABLE:
            return f"❌ Unknown unit '{to_unit}'. Supported: {', '.join(_UNIT_TABLE.keys())}"

        cat_f, factor_f = _UNIT_TABLE[fu]
        cat_t, factor_t = _UNIT_TABLE[tu]

        if cat_f != cat_t:
            return f"❌ Cannot convert between {cat_f} and {cat_t}. They are different unit types."

        result = value * factor_f / factor_t
        return f"📐 {value} {from_unit} = {result:,.6g} {to_unit}"
    except Exception as e:
        return f"❌ Error: {e}"


# ─────────────────────────────────────────────────────────────────────────────
# POMODORO TIMER
# ─────────────────────────────────────────────────────────────────────────────

@tool
def countdown_pomodoro(work_minutes: int = 25, break_minutes: int = 5) -> str:
    """Starts a Pomodoro timer cycle: work period followed by a break.

    Args:
        work_minutes: Work session duration in minutes (default 25).
        break_minutes: Break duration in minutes (default 5).
    """
    try:
        work_sec = work_minutes * 60
        break_sec = break_minutes * 60

        def _pomodoro():
            # Work phase
            print(f"\n🍅 POMODORO: Work session started ({work_minutes} min)")
            if HAS_PLYER:
                try:
                    plyer_notif.notify(
                        title="🍅 Pomodoro — Work!",
                        message=f"Focus for {work_minutes} minutes. No distractions!",
                        timeout=10
                    )
                except Exception:
                    pass
            threading.Event().wait(timeout=work_sec)

            # Break phase
            _play_alert()
            print(f"\n☕ POMODORO: Break time! ({break_minutes} min)")
            if HAS_PLYER:
                try:
                    plyer_notif.notify(
                        title="☕ Pomodoro — Break!",
                        message=f"Great work! Take a {break_minutes}-minute break.",
                        timeout=10
                    )
                except Exception:
                    pass
            threading.Event().wait(timeout=break_sec)

            _play_alert()
            print("\n✅ POMODORO: Cycle complete! Ready for next round.")
            if HAS_PLYER:
                try:
                    plyer_notif.notify(
                        title="✅ Pomodoro Done!",
                        message="Break is over. Ready for the next session?",
                        timeout=10
                    )
                except Exception:
                    pass

        t = threading.Thread(target=_pomodoro, daemon=True)
        t.start()

        work_end = (datetime.datetime.now() + datetime.timedelta(seconds=work_sec)).strftime("%H:%M")
        break_end = (datetime.datetime.now() + datetime.timedelta(seconds=work_sec + break_sec)).strftime("%H:%M")
        return (
            f"🍅 Pomodoro Timer Started!\n"
            f"{'─' * 30}\n"
            f"🧠 Work phase:  {work_minutes} min → ends at {work_end}\n"
            f"☕ Break phase: {break_minutes} min → ends at {break_end}\n"
            f"You'll get desktop notifications at each phase change."
        )
    except Exception as e:
        return f"❌ Error: {e}"


# ─────────────────────────────────────────────────────────────────────────────
# DAILY SUMMARY
# ─────────────────────────────────────────────────────────────────────────────

@tool
def daily_summary() -> str:
    """Generates a daily summary: current date/time, pending tasks, and saved notes count."""
    try:
        now = datetime.datetime.now()

        # Date/time
        section_dt = (
            f"🗓️  {now.strftime('%A, %B %d %Y')} — {now.strftime('%H:%M')}\n"
            f"   Week {now.strftime('%W')} of {now.year}"
        )

        # Todos
        todos = _load_json(_TODOS_FILE)
        if not isinstance(todos, list):
            todos = []
        pending = [t for t in todos if t.get("status") == "pending"]
        overdue = [
            t for t in pending
            if t.get("due_date") and t["due_date"] < now.strftime("%Y-%m-%d")
        ]
        today_due = [
            t for t in pending
            if t.get("due_date") == now.strftime("%Y-%m-%d")
        ]

        p_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}
        todo_lines = [f"\n📋 Tasks: {len(pending)} pending, {len(todos) - len(pending)} done"]
        if overdue:
            todo_lines.append(f"   ⚠️  {len(overdue)} OVERDUE:")
            for t in overdue[:5]:
                todo_lines.append(f"      {p_emoji.get(t['priority'], '⚪')} {t['task']} (was due {t['due_date']})")
        if today_due:
            todo_lines.append(f"   📅 Due TODAY ({len(today_due)}):")
            for t in today_due[:5]:
                todo_lines.append(f"      {p_emoji.get(t['priority'], '⚪')} {t['task']}")
        if not overdue and not today_due and pending:
            todo_lines.append(f"   No tasks due today. Next up:")
            upcoming = sorted([t for t in pending if t.get("due_date")], key=lambda x: x["due_date"])
            for t in upcoming[:3]:
                todo_lines.append(f"      {p_emoji.get(t['priority'], '⚪')} {t['task']} (due {t['due_date']})")

        # Notes
        notes = _load_json(_NOTES_FILE)
        notes_line = f"\n📒 Notes: {len(notes)} saved"

        return "\n".join([
            "━" * 40,
            "🌅 DAILY SUMMARY",
            "━" * 40,
            section_dt,
            *todo_lines,
            notes_line,
            "━" * 40,
        ])
    except Exception as e:
        return f"❌ Error generating summary: {e}"
