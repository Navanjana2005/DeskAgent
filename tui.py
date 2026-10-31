
from __future__ import annotations

import os
import queue
import re
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import trim_messages

try:
    from rich import box
    from rich.console import Console, Group
    from rich.live import Live
    from rich.markdown import Markdown
    from rich.panel import Panel
    from rich.prompt import Prompt
    from rich.rule import Rule
    from rich.spinner import Spinner
    from rich.table import Table
    from rich.text import Text

    HAS_RICH = True
except ImportError:
    HAS_RICH = False


# ──────────────────────────────────────────────────────────────────────────
# Settings
# ──────────────────────────────────────────────────────────────────────────
def _positive_int_setting(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        parsed = int(value)
    except ValueError as error:
        raise RuntimeError(f"{name} must be a positive integer.") from error
    if parsed <= 0:
        raise RuntimeError(f"{name} must be a positive integer.")
    return parsed


HISTORY_TOKEN_BUDGET = _positive_int_setting(
    "DESKAGENT_HISTORY_TOKEN_BUDGET", 4000
)
HISTORY_MAX_TURNS = _positive_int_setting("DESKAGENT_HISTORY_MAX_TURNS", 4)


# ──────────────────────────────────────────────────────────────────────────
# Theme
# ──────────────────────────────────────────────────────────────────────────
ACCENT = "#8b5cf6"    # violet
ACCENT2 = "#22d3ee"   # cyan
OK = "#34d399"        # emerald
WARN = "#fbbf24"      # amber
ERR = "#fb7185"       # rose
TEXT = "#e5e7eb"
MUTED = "grey58"
GREY = "grey35"
INK = "#0b0b12"       # dark text for coloured pills

LOGO = (
    "╺┳┓┏━╸┏━┓╻┏ ┏━┓┏━╸┏━╸┏┓╻╺┳╸",
    " ┃┃┣╸ ┗━┓┣┻┓┣━┫┃╺┓┣╸ ┃┗┫ ┃ ",
    "╺┻┛┗━╸┗━┛╹ ╹╹ ╹┗━┛┗━╸╹ ╹ ╹ ",
)
PHASES = ("Received", "Thinking", "Tools", "Done")
SPARKS = "▁▂▃▄▅▆▇█"

_EVENT_STYLE = {
    "task_started": ("▸", ACCENT),
    "llm_started": ("◇", ACCENT2),
    "llm_completed": ("◆", ACCENT2),
    "llm_failed": ("✘", ERR),
    "tool_started": ("▶", WARN),
    "tool_completed": ("✔", OK),
    "tool_failed": ("✘", ERR),
    "task_completed": ("★", OK),
    "task_failed": ("✘", ERR),
    "cancellation_unsupported": ("!", WARN),
}

_CATEGORY_ICONS = (
    ("file", "▤"),
    ("web", "◍"),
    ("browser", "◍"),
    ("network", "⇄"),
    ("clip", "❐"),
    ("audio", "♪"),
    ("voice", "♪"),
    ("note", "✎"),
    ("system", "◈"),
)

EXAMPLE_PROMPTS = (
    "What is using the most memory on my machine right now?",
    "Summarize the PDF on my desktop in five bullet points",
    "Generate a strong password and save a note about it",
    "Organize my Downloads folder by file type",
)


# ──────────────────────────────────────────────────────────────────────────
# Sanitisation (unchanged behaviour)
# ──────────────────────────────────────────────────────────────────────────
_SECRET_KEY = re.compile(
    r"(?i)(api[_\s-]?key|access[_\s-]?token|refresh[_\s-]?token|token|password|passwd|secret|authorization|credential|private[_\s-]?key)"
)
_CREDENTIAL = re.compile(
    r"(?i)\b(?:nvapi-[a-z0-9_-]{12,}|fc-[a-f0-9-]{20,}|"
    r"sk-[a-z0-9_-]{16,})\b"
)
_SENSITIVE_OUTPUT_TOOLS = {
    "decrypt_file",
    "generate_password",
    "get_clipboard",
    "get_clipboard_image",
    "get_network_info",
    "get_preference",
    "get_process_info",
    "get_public_ip",
    "get_startup_programs",
    "listen_and_transcribe",
    "read_docx",
    "read_excel",
    "read_file_content",
    "read_pdf",
    "recall_note",
    "list_notes",
}


# ──────────────────────────────────────────────────────────────────────────
# Data model
# ──────────────────────────────────────────────────────────────────────────
@dataclass
class ToolExecution:
    number: int
    name: str
    category: str
    description: str
    arguments: str
    status: str = "RUNNING"
    duration: float | None = None
    result: str = ""
    started_at: float = field(default_factory=time.monotonic)


@dataclass
class ActivityEvent:
    kind: str
    message: str
    created_at: datetime = field(default_factory=datetime.now)
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskDisplay:
    prompt: str
    started_at: float = field(default_factory=time.monotonic)
    finished_at: float | None = None
    status: str = "RECEIVING TASK"
    explanation: str = "Task received by DeskAgent."
    phase: int = 0
    activities: list[ActivityEvent] = field(default_factory=list)
    tools: list[ToolExecution] = field(default_factory=list)
    result: str = ""
    failed: bool = False

    @property
    def elapsed(self) -> float:
        end = self.finished_at if self.finished_at is not None else time.monotonic()
        return end - self.started_at

    @property
    def done(self) -> bool:
        return self.finished_at is not None


@dataclass
class SessionStats:
    started_at: float = field(default_factory=time.monotonic)
    tasks: int = 0
    failed: int = 0
    tool_calls: int = 0
    busy_time: float = 0.0


class _PlainConsole:
    def print(self, *values: Any) -> None:
        print(" ".join(str(value) for value in values))


def _safe_text(value: Any, limit: int = 1200) -> str:
    text = str(value)
    text = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", text)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    text = _CREDENTIAL.sub("[REDACTED CREDENTIAL]", text)
    text = re.sub(
        r"(?im)(\b(?:api[_\s-]?key|access[_\s-]?token|refresh[_\s-]?token|"
        r"password|passwd|secret|authorization|credential|private[_\s-]?key)\b\s*[:=]\s*)[^\r\n,}]+",
        r"\1[REDACTED]",
        text,
    )
    if len(text) > limit:
        text = text[:limit].rstrip() + " … [truncated]"
    return text


def _safe_arguments(inputs: Any, input_text: str) -> str:
    if isinstance(inputs, dict):
        pieces = []
        for key, value in inputs.items():
            if _SECRET_KEY.search(str(key)):
                safe_value = "[REDACTED]"
            else:
                safe_value = _safe_text(value, limit=240)
            pieces.append(f"{_safe_text(key, limit=100)} = {safe_value}")
        return _safe_text("\n".join(pieces), limit=1200) if pieces else "(no arguments)"
    return _safe_text(input_text, limit=800) or "(no arguments)"


def _result_summary(name: str, output: Any, limit: int = 300) -> str:
    if name in _SENSITIVE_OUTPUT_TOOLS:
        return "[Sensitive tool output hidden in the activity monitor.]"
    if isinstance(output, str):
        text = output
    else:
        text = repr(output)
    text = _safe_text(text, limit=limit)
    return text.strip() or "(empty result)"


# ──────────────────────────────────────────────────────────────────────────
# Conversation history (unchanged behaviour)
# ──────────────────────────────────────────────────────────────────────────
def compact_conversation_history(
    messages: list[Any],
    max_tokens: int = HISTORY_TOKEN_BUDGET,
    max_turns: int = HISTORY_MAX_TURNS,
) -> list[Any]:
    """Keep recent user/final-assistant turns, omitting replayed tool traffic."""
    if max_tokens <= 0 or max_turns <= 0:
        raise ValueError("History token and turn limits must be positive.")

    completed_turns: list[list[Any]] = []
    user_message: Any | None = None
    final_answer: Any | None = None

    for message in messages:
        message_type = getattr(message, "type", None)
        if message_type == "human":
            if user_message is not None and final_answer is not None:
                completed_turns.append([user_message, final_answer])
            user_message = message
            final_answer = None
        elif (
            user_message is not None
            and message_type == "ai"
            and not getattr(message, "tool_calls", None)
            and not getattr(message, "invalid_tool_calls", None)
        ):
            final_answer = message

    if user_message is not None and final_answer is not None:
        completed_turns.append([user_message, final_answer])

    recent_turns = completed_turns[-max_turns:]
    recent_messages = [message for turn in recent_turns for message in turn]
    if not recent_messages:
        return []
    return trim_messages(
        recent_messages,
        max_tokens=max_tokens,
        token_counter="approximate",
        strategy="last",
        allow_partial=False,
        start_on="human",
    )


# ──────────────────────────────────────────────────────────────────────────
# LangChain callbacks → UI events (unchanged behaviour)
# ──────────────────────────────────────────────────────────────────────────
class AgentEventHandler(BaseCallbackHandler):
    """Converts observable LangChain callbacks into safe UI events."""

    def __init__(
        self,
        events: queue.Queue[ActivityEvent],
        tool_metadata: dict[str, dict[str, str]],
        first_tool_number: int,
    ) -> None:
        self.events = events
        self.tool_metadata = tool_metadata
        self.next_tool_number = first_tool_number
        self._running: dict[UUID, ToolExecution] = {}
        self._lock = threading.Lock()

    def _emit(self, kind: str, message: str, **data: Any) -> None:
        self.events.put(ActivityEvent(kind=kind, message=message, data=data))

    def on_llm_start(self, serialized: dict[str, Any], prompts: list[str], **kwargs: Any) -> None:
        self._emit("llm_started", "Request sent to the configured model.")

    def on_llm_end(self, response: Any, **kwargs: Any) -> None:
        self._emit("llm_completed", "Model response received.")

    def on_llm_error(self, error: BaseException, **kwargs: Any) -> None:
        self._emit("llm_failed", f"Model request failed: {_safe_text(error, 240)}")

    def on_tool_start(
        self,
        serialized: dict[str, Any],
        input_str: str,
        *,
        run_id: UUID,
        inputs: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        name = str(serialized.get("name") or "unknown tool")
        metadata = self.tool_metadata.get(name, {})
        with self._lock:
            execution = ToolExecution(
                number=self.next_tool_number,
                name=name,
                category=metadata.get("category", "tool"),
                description=_safe_text(metadata.get("description", "Registered DeskAgent tool."), 180),
                arguments=_safe_arguments(inputs, input_str),
            )
            self.next_tool_number += 1
            self._running[run_id] = execution
        self._emit("tool_started", f"Executing {name}.", execution=execution)

    def on_tool_end(self, output: Any, *, run_id: UUID, **kwargs: Any) -> None:
        self._finish_tool(run_id, output=output)

    def on_tool_error(self, error: BaseException, *, run_id: UUID, **kwargs: Any) -> None:
        self._finish_tool(run_id, error=error)

    def _finish_tool(
        self,
        run_id: UUID,
        output: Any = None,
        error: BaseException | None = None,
    ) -> None:
        with self._lock:
            execution = self._running.pop(run_id, None)
        if execution is None:
            return

        execution.duration = time.monotonic() - execution.started_at
        if error is not None:
            execution.status = "FAILED"
            execution.result = _safe_text(error, 300)
            kind = "tool_failed"
            message = f"{execution.name} failed."
        else:
            execution.status = "COMPLETED"
            execution.result = _result_summary(execution.name, output)
            kind = "tool_completed"
            message = f"{execution.name} completed."
        self._emit(kind, message, execution=execution)


# ──────────────────────────────────────────────────────────────────────────
# Small rendering helpers
# ──────────────────────────────────────────────────────────────────────────
def _time_label(created_at: datetime) -> str:
    return created_at.strftime("%H:%M:%S")


def _format_span(seconds: float) -> str:
    seconds = int(seconds)
    hours, rest = divmod(seconds, 3600)
    minutes, secs = divmod(rest, 60)
    if hours:
        return f"{hours}h {minutes:02d}m"
    if minutes:
        return f"{minutes}m {secs:02d}s"
    return f"{secs}s"


def _category_icon(category: str) -> str:
    lowered = category.lower()
    for needle, icon in _CATEGORY_ICONS:
        if needle in lowered:
            return icon
    return "◆"


def _sparkline(values: list[float]) -> str:
    if not values:
        return ""
    peak = max(values) or 1.0
    top = len(SPARKS) - 1
    return "".join(SPARKS[min(top, int(v / peak * top))] for v in values)


def _bar(value: float, peak: float, width: int = 8) -> str:
    peak = peak or 1.0
    filled = max(1, round(width * min(value / peak, 1.0))) if value > 0 else 0
    return "█" * filled + "░" * (width - filled)


def _gradient(text: str, start=(139, 92, 246), end=(34, 211, 238), bold=True) -> "Text":
    out = Text()
    span = max(len(text) - 1, 1)
    for index, char in enumerate(text):
        t = index / span
        r, g, b = (int(s + (e - s) * t) for s, e in zip(start, end))
        out.append(char, style=f"{'bold ' if bold else ''}rgb({r},{g},{b})")
    return out


def _pill(label: str, color: str) -> "Text":
    return Text(f" {label} ", style=f"bold {INK} on {color}")


def _task_state(task: TaskDisplay | None) -> tuple[str, str]:
    if task is None:
        return "idle", MUTED
    if task.failed:
        return "failed", ERR
    if task.done:
        return "done", OK
    return "active", ACCENT2


def _track_tool(tool_history: list[ToolExecution], event: ActivityEvent) -> None:
    if not event.kind.startswith("tool_"):
        return
    execution = event.data["execution"]
    if all(item is not execution for item in tool_history):
        tool_history.append(execution)


# ──────────────────────────────────────────────────────────────────────────
# Rich components
# ──────────────────────────────────────────────────────────────────────────
def _banner(provider: str, model: str, tool_count: int) -> Any:
    logo = Group(*[_gradient(row) for row in LOGO])
    chips = Text.assemble(
        _pill(provider.upper(), ACCENT),
        " ",
        _pill(model, ACCENT2),
        " ",
        _pill(f"{tool_count} tools", OK),
    )
    body = Group(
        logo,
        Text("Intelligent Desktop Automation Agent", style=f"italic {MUTED}"),
        Text(""),
        chips,
    )
    return Panel(body, box=box.ROUNDED, border_style=ACCENT, padding=(1, 3))


def _welcome_panels() -> Any:
    tips = Table.grid(padding=(0, 1))
    tips.add_column(width=2)
    tips.add_column()
    for prompt in EXAMPLE_PROMPTS:
        tips.add_row(Text("›", style=ACCENT2), Text(prompt, style=TEXT))
    tips_panel = Panel(
        tips,
        title=Text("Try asking", style=f"bold {ACCENT2}"),
        title_align="left",
        border_style=GREY,
        box=box.ROUNDED,
        padding=(0, 1),
    )

    commands = Table.grid(padding=(0, 1))
    commands.add_column(style=f"bold {ACCENT}")
    commands.add_column(style=MUTED)
    for cmd, label in (
        ("/history", "recent tool runs"),
        ("/detail N", "inspect a tool run"),
        ("/stats", "session statistics"),
        ("/clear", "clear the screen"),
        ("/help", "show commands"),
        ("/quit", "exit"),
    ):
        commands.add_row(cmd, label)
    commands_panel = Panel(
        commands,
        title=Text("Commands", style=f"bold {ACCENT}"),
        title_align="left",
        border_style=GREY,
        box=box.ROUNDED,
        padding=(0, 1),
    )

    grid = Table.grid(expand=True, padding=(0, 1))
    grid.add_column(ratio=3)
    grid.add_column(ratio=2)
    grid.add_row(tips_panel, commands_panel)
    return grid


def _header_line(provider: str, model: str, tool_count: int) -> Any:
    title = Text.assemble(
        _gradient("◆ DESKAGENT"),
        ("   ", ""),
        (f"{provider.upper()} · {model} · {tool_count} tools", MUTED),
    )
    return Rule(title=title, align="left", style=GREY)


def _pipeline(task: TaskDisplay) -> Any:
    line = Text()
    for index, label in enumerate(PHASES):
        if task.failed and index == task.phase:
            icon, color = "✘", ERR
        elif index < task.phase or (task.done and not task.failed):
            icon, color = "●", OK
        elif index == task.phase:
            icon, color = "◉", ACCENT2
        else:
            icon, color = "○", GREY
        current = index == task.phase and not task.done
        line.append(f"{icon} {label}", style=f"bold {color}" if current else color)
        if index < len(PHASES) - 1:
            connector = OK if index < task.phase else GREY
            line.append("  ━━  ", style=connector)
    return line


def _task_panel(task: TaskDisplay | None, running: bool) -> Any:
    if task is None:
        return Panel(
            Group(
                Text("Ready for your next task.", style=f"bold {TEXT}"),
                Text("Describe what you want done in plain language.", style=MUTED),
            ),
            border_style=GREY,
            box=box.ROUNDED,
            padding=(0, 1),
        )

    _, color = _task_state(task)
    head = Table.grid(expand=True, padding=(0, 1))
    head.add_column(width=2)
    head.add_column()
    head.add_column(justify="right")
    if running:
        lead: Any = Spinner("dots", style=color)
    else:
        lead = Text("✘" if task.failed else "✔", style=f"bold {color}")
    head.add_row(lead, _pill(task.status, color), Text(f"{task.elapsed:5.1f}s", style=MUTED))

    body = Group(
        head,
        Text.assemble(
            ("❯ ", f"bold {ACCENT}"),
            (_safe_text(task.prompt, 400), f"bold {TEXT}"),
            overflow="fold",
        ),
        Text(_safe_text(task.explanation, 300), style=MUTED, overflow="fold"),
        Text(""),
        _pipeline(task),
    )
    return Panel(
        body,
        title=Text("Current task", style=f"bold {color}"),
        title_align="left",
        border_style=color,
        box=box.ROUNDED,
        padding=(0, 1),
    )


def _tool_status_cell(execution: ToolExecution) -> Any:
    if execution.status == "RUNNING":
        return Spinner("dots", text=Text(" running", style=WARN), style=WARN)
    if execution.status == "FAILED":
        return Text("✘ failed", style=f"bold {ERR}")
    return Text("✔ done", style=OK)


def _tools_panel(tools: list[ToolExecution], rows: int) -> Any:
    shown = tools[-rows:]
    table = Table(
        box=None,
        expand=True,
        show_header=True,
        header_style=f"dim {MUTED}",
        padding=(0, 1),
    )
    table.add_column("#", width=3, style=MUTED)
    table.add_column("Tool", ratio=1, no_wrap=True, overflow="ellipsis")
    table.add_column("Status", width=10, no_wrap=True)
    table.add_column("Latency", width=17, no_wrap=True)

    def span(item: ToolExecution) -> float:
        return item.duration if item.duration is not None else time.monotonic() - item.started_at

    peak = max((span(item) for item in shown), default=0.0)
    for item in shown:
        elapsed = span(item)
        bar_color = ERR if item.status == "FAILED" else (WARN if item.status == "RUNNING" else ACCENT2)
        table.add_row(
            f"{item.number:02d}",
            Text.assemble((f"{_category_icon(item.category)} ", ACCENT), (item.name, f"bold {TEXT}")),
            _tool_status_cell(item),
            Text.assemble((_bar(elapsed, peak), bar_color), (f" {elapsed:5.2f}s", MUTED)),
        )
    if not shown:
        table.add_row("·", Text("No tool calls yet", style=MUTED), "", "")

    durations = [item.duration for item in tools if item.duration is not None]
    subtitle = None
    if len(durations) >= 2:
        subtitle = Text.assemble(("latency ", MUTED), (_sparkline(durations[-20:]), ACCENT2))
    return Panel(
        table,
        title=Text.assemble(("Tool execution", f"bold {OK}"), (f"  {len(tools)} this task", MUTED)),
        title_align="left",
        subtitle=subtitle,
        subtitle_align="right",
        border_style=OK,
        box=box.ROUNDED,
        padding=(0, 0),
    )


def _timeline_panel(events: list[ActivityEvent], rows: int) -> Any:
    grid = Table.grid(expand=True, padding=(0, 1))
    grid.add_column(width=8)
    grid.add_column(width=1)
    grid.add_column(ratio=1, no_wrap=True, overflow="ellipsis")
    for event in events[-rows:]:
        icon, color = _EVENT_STYLE.get(event.kind, ("·", MUTED))
        failed = event.kind in {"task_failed", "tool_failed", "llm_failed"}
        grid.add_row(
            Text(_time_label(event.created_at), style=GREY),
            Text(icon, style=f"bold {color}"),
            Text(_safe_text(event.message, 140), style=ERR if failed else MUTED),
        )
    if not events:
        grid.add_row("", "", Text("Activity will appear here.", style=MUTED))
    return Panel(
        grid,
        title=Text("Timeline", style=f"bold {ACCENT}"),
        title_align="left",
        border_style=ACCENT,
        box=box.ROUNDED,
        padding=(0, 1),
    )


def _footer() -> Any:
    chips = Text(no_wrap=True, overflow="ellipsis")
    for cmd, label in (
        ("/history", "history"),
        ("/detail N", "inspect"),
        ("/stats", "stats"),
        ("/clear", "clear"),
        ("/help", "help"),
        ("/quit", "exit"),
    ):
        chips.append(f" {cmd} ", style=f"bold {TEXT} on grey23")
        chips.append(f" {label}  ", style=MUTED)
    return chips


def _render_dashboard(
    task: TaskDisplay | None,
    *,
    tool_count: int,
    model: str,
    provider: str,
    width: int,
    height: int,
    running: bool,
) -> Any:
    rows = 5 if height >= 32 else 3
    tools = task.tools if task else []
    events = task.activities if task else []
    tools_panel = _tools_panel(tools, rows)
    timeline_panel = _timeline_panel(events, rows + 1)

    parts: list[Any] = [
        _header_line(provider, model, tool_count),
        _task_panel(task, running),
    ]
    if width >= 100:
        grid = Table.grid(expand=True, padding=(0, 1))
        grid.add_column(ratio=3)
        grid.add_column(ratio=2)
        grid.add_row(tools_panel, timeline_panel)
        parts.append(grid)
    else:
        parts.extend([tools_panel, timeline_panel])
    parts.append(_footer())
    return Group(*parts)


def _result_panel(task: TaskDisplay) -> Any:
    _, color = _task_state(task)
    if task.failed:
        body: Any = Text(task.result or "The task failed.", style=ERR, overflow="fold")
        label = "Failed"
    else:
        body = Markdown(task.result) if task.result.strip() else Text("(empty result)", style=MUTED)
        label = "Result"
    return Panel(
        body,
        title=Text.assemble((f"{'✘' if task.failed else '◆'} ", f"bold {color}"), (label, "bold")),
        title_align="left",
        subtitle=Text(f"{task.elapsed:.1f}s · {len(task.tools)} tool call(s)", style=MUTED),
        subtitle_align="right",
        border_style=color,
        box=box.ROUNDED,
        padding=(1, 2),
    )


def _task_summary_line(task: TaskDisplay, session: SessionStats) -> Any:
    _, color = _task_state(task)
    return Text.assemble(
        ("  ✘ " if task.failed else "  ✔ ", f"bold {color}"),
        ("Task failed" if task.failed else "Task completed", f"bold {color}"),
        (f"  ·  {task.elapsed:.2f}s  ·  {len(task.tools)} tool call(s)", MUTED),
        (f"  ·  session: {session.tasks} task(s), {session.tool_calls} tool call(s)", GREY),
    )


def _plain_event(event: ActivityEvent) -> str:
    return f"[{_time_label(event.created_at)}] {event.message}"


def _render_history(console: Any, history: list[ToolExecution]) -> None:
    if HAS_RICH:
        table = Table(
            title=Text("Recent tool executions", style=f"bold {ACCENT}"),
            box=box.SIMPLE_HEAD,
            header_style=f"bold {MUTED}",
            border_style=GREY,
        )
        table.add_column("#", style=MUTED)
        table.add_column("Tool")
        table.add_column("Category", style=MUTED)
        table.add_column("Status")
        table.add_column("Latency", justify="right")
        shown = history[-15:]
        peak = max((item.duration or 0.0 for item in shown), default=0.0)
        for item in shown:
            color = {"RUNNING": WARN, "FAILED": ERR}.get(item.status, OK)
            duration = item.duration
            latency = (
                Text.assemble((_bar(duration, peak), ACCENT2), (f" {duration:.2f}s", MUTED))
                if duration is not None
                else Text("—", style=MUTED)
            )
            table.add_row(
                f"{item.number:02d}",
                Text(f"{_category_icon(item.category)} {item.name}", style=TEXT),
                item.category,
                Text(item.status.lower(), style=color),
                latency,
            )
        if not shown:
            table.add_row("·", Text("No tool calls have been recorded.", style=MUTED), "", "", "")
        console.print(table)
    elif history:
        for item in history[-15:]:
            duration = f"{item.duration:.2f}s" if item.duration is not None else "—"
            console.print(f"{item.number:02d} {item.name} [{item.status}] {duration}")
    else:
        console.print("No tool calls have been recorded.")


def _render_detail(console: Any, execution: ToolExecution | None) -> None:
    if execution is None:
        console.print(
            Text("No tool execution with that number.", style=WARN) if HAS_RICH
            else "No tool execution with that number."
        )
        return
    duration = f"{execution.duration:.2f}s" if execution.duration is not None else "still running"
    if HAS_RICH:
        color = {"RUNNING": WARN, "FAILED": ERR}.get(execution.status, OK)
        grid = Table.grid(padding=(0, 2))
        grid.add_column(style=MUTED, justify="right", no_wrap=True)
        grid.add_column(overflow="fold")
        grid.add_row("Category", Text(execution.category, style=TEXT))
        grid.add_row("Status", _pill(execution.status, color))
        grid.add_row("Duration", Text(duration, style=TEXT))
        grid.add_row("Description", Text(_safe_text(execution.description, 400), style=TEXT))
        grid.add_row("Arguments", Text(_safe_text(execution.arguments, 1500), style=ACCENT2))
        grid.add_row("Result", Text(_safe_text(execution.result or "(still running)", 3000), style=TEXT))
        console.print(
            Panel(
                grid,
                title=Text.assemble(
                    (f"{_category_icon(execution.category)} Tool {execution.number}: ", MUTED),
                    (execution.name, f"bold {TEXT}"),
                ),
                title_align="left",
                border_style=color,
                box=box.ROUNDED,
                padding=(1, 2),
            )
        )
    else:
        content = (
            f"Category: {execution.category}\n"
            f"Status: {execution.status}\n"
            f"Description: {execution.description}\n"
            f"Arguments:\n{execution.arguments}\n"
            f"Result:\n{execution.result or '(still running)'}\n"
            f"Duration: {duration}"
        )
        console.print(_safe_text(content, 6000))


def _render_stats(console: Any, session: SessionStats) -> None:
    uptime = time.monotonic() - session.started_at
    if HAS_RICH:
        grid = Table.grid(padding=(0, 3))
        grid.add_column(style=MUTED)
        grid.add_column(style=f"bold {TEXT}", justify="right")
        grid.add_row("Session uptime", _format_span(uptime))
        grid.add_row("Tasks run", str(session.tasks))
        grid.add_row("Tasks failed", Text(str(session.failed), style=ERR if session.failed else TEXT))
        grid.add_row("Tool calls", str(session.tool_calls))
        grid.add_row("Time working", _format_span(session.busy_time))
        console.print(
            Panel(
                grid,
                title=Text("Session stats", style=f"bold {ACCENT}"),
                title_align="left",
                border_style=ACCENT,
                box=box.ROUNDED,
                padding=(1, 2),
                expand=False,
            )
        )
    else:
        console.print(
            f"Uptime {_format_span(uptime)} | tasks {session.tasks} | failed {session.failed} | "
            f"tool calls {session.tool_calls}"
        )


def _render_help(console: Any) -> None:
    if not HAS_RICH:
        console.print(
            "Commands: /history, /detail N, /stats, /clear, /help, /quit. "
            "Enter a natural-language request to run DeskAgent."
        )
        return
    table = Table(box=box.SIMPLE_HEAD, header_style=f"bold {MUTED}", border_style=GREY)
    table.add_column("Command", style=f"bold {ACCENT}")
    table.add_column("What it does")
    table.add_row("<any text>", "Run a natural-language task")
    table.add_row("/history", "Show recent tool executions")
    table.add_row("/detail N", "Inspect tool execution number N")
    table.add_row("/stats", "Show session statistics")
    table.add_row("/clear", "Clear the display (history and files untouched)")
    table.add_row("/help", "Show this help")
    table.add_row("/quit", "Exit (also: exit, quit, bye)")
    console.print(table)


# ──────────────────────────────────────────────────────────────────────────
# Response parsing + worker
# ──────────────────────────────────────────────────────────────────────────
def _response_text(messages: Any) -> str:
    if isinstance(messages, dict):
        messages = messages.get("messages", [])
    if not messages:
        return "(The agent returned no messages.)"
    content = getattr(messages[-1], "content", "")
    if isinstance(content, str):
        return content or "(The agent returned an empty response.)"
    if isinstance(content, list):
        text_parts = [
            str(part.get("text", ""))
            for part in content
            if isinstance(part, dict) and part.get("type") == "text"
        ]
        return "\n".join(text_parts) or "(The agent returned a non-text response.)"
    return str(content)


def _run_task(
    agent: Any,
    current_messages: list[Any],
    handler: AgentEventHandler,
    events: queue.Queue[ActivityEvent],
) -> None:
    try:
        response = agent.invoke(
            {"messages": current_messages},
            config={"callbacks": [handler]},
        )
        events.put(ActivityEvent("task_completed", "Task completed.", data={"response": response}))
    except Exception as error:
        events.put(
            ActivityEvent(
                "task_failed",
                f"Task failed: {_safe_text(error, 400)}",
                data={"error": error},
            )
        )


def _apply_event(task: TaskDisplay, event: ActivityEvent) -> None:
    task.activities.append(event)
    if event.kind == "task_started":
        task.phase = 0
    elif event.kind == "llm_started":
        task.phase = 1
        task.status = "THINKING"
        task.explanation = event.message
    elif event.kind == "llm_completed":
        task.status = "MODEL RESPONDED"
        task.explanation = event.message
    elif event.kind == "llm_failed":
        task.status = "FAILED"
        task.failed = True
        task.explanation = event.message
    elif event.kind == "tool_started":
        execution = event.data["execution"]
        task.tools.append(execution)
        task.phase = 2
        task.status = "EXECUTING TOOL"
        task.explanation = f"{execution.name}: {execution.description}"
    elif event.kind == "tool_completed":
        task.status = "TOOL COMPLETED"
        task.explanation = event.message
    elif event.kind == "tool_failed":
        task.status = "TOOL FAILED"
        task.explanation = event.message
    elif event.kind == "task_completed":
        task.phase = len(PHASES) - 1
        task.status = "COMPLETED"
        task.explanation = "Agent returned a final response."
        task.result = _safe_text(_response_text(event.data["response"]), 6000)
        task.finished_at = time.monotonic()
    elif event.kind == "task_failed":
        task.status = "FAILED"
        task.failed = True
        task.explanation = "Agent invocation failed."
        task.result = _safe_text(event.message, 2000)
        task.finished_at = time.monotonic()


def _history_from_event(event: ActivityEvent, messages: list[Any]) -> list[Any] | None:
    response = event.data.get("response")
    if response is None:
        return None
    return compact_conversation_history(response.get("messages", messages))


def _cancel_unsupported(task: TaskDisplay) -> ActivityEvent:
    task.status = "RUNNING (CANNOT CANCEL)"
    task.explanation = (
        "This agent invocation cannot be cancelled safely; waiting for it to finish."
    )
    interrupt = ActivityEvent(
        "cancellation_unsupported",
        "Ctrl+C cannot cancel the current agent invocation.",
    )
    task.activities.append(interrupt)
    return interrupt


# ──────────────────────────────────────────────────────────────────────────
# Main loop
# ──────────────────────────────────────────────────────────────────────────
def _print_welcome(console: Any, provider: str, model: str, tool_count: int) -> None:
    if HAS_RICH:
        console.print(_banner(provider, model, tool_count))
        console.print(_welcome_panels())
        console.print(
            Text(
                "  Model connectivity is checked on the first request. "
                "Sensitive tool output is withheld from the activity monitor.",
                style=f"dim {MUTED}",
            )
        )
    else:
        console.print("DESKAGENT — Intelligent Desktop Automation Agent")
        console.print(
            f"System: READY  |  {provider} model: {model}  |  "
            f"Tools: {tool_count} registered"
        )


def run_terminal_chat(
    agent: Any,
    registered_tools: list[Any],
    tool_metadata: dict[str, dict[str, str]],
    model: str,
    provider: str = "LLM",
) -> None:
    """Runs the terminal interaction layer around the existing agent."""
    console = Console(highlight=False) if HAS_RICH else _PlainConsole()
    history: list[Any] = []
    tool_history: list[ToolExecution] = []
    session = SessionStats()
    tool_count = len(registered_tools)

    _print_welcome(console, provider, model, tool_count)

    prompt_label = (
        Text.assemble(("\n╭─ ", GREY), ("task", f"bold {ACCENT}"), ("\n╰─❯ ", GREY))
        if HAS_RICH
        else None
    )

    while True:
        try:
            if HAS_RICH:
                user_input = Prompt.ask(prompt_label).strip()
            else:
                user_input = input("\nTask> ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print(Text("\nGoodbye. ✦", style=f"bold {ACCENT}") if HAS_RICH else "\nGoodbye.")
            return

        if not user_input:
            continue
        command = user_input.lower()
        if command in {"exit", "quit", "bye", "/quit"}:
            if HAS_RICH:
                console.print(
                    Text.assemble(
                        ("Goodbye. ✦", f"bold {ACCENT}"),
                        (f"  session {_format_span(time.monotonic() - session.started_at)}"
                         f" · {session.tasks} task(s)", MUTED),
                    )
                )
            else:
                console.print("Goodbye.")
            return
        if command == "/help":
            _render_help(console)
            continue
        if command == "/history":
            _render_history(console, tool_history)
            continue
        if command == "/stats":
            _render_stats(console, session)
            continue
        if command == "/clear":
            if HAS_RICH:
                console.clear()
                console.print(_banner(provider, model, tool_count))
            else:
                console.print("\n" * 30)
            console.print(
                Text("Display cleared. Conversation history and user files were not changed.", style=MUTED)
                if HAS_RICH
                else "Display cleared. Conversation history and user files were not changed."
            )
            continue
        if command.startswith("/detail"):
            parts = command.split(maxsplit=1)
            try:
                number = int(parts[1])
            except (IndexError, ValueError):
                console.print("Usage: /detail N")
                continue
            _render_detail(
                console,
                next((item for item in tool_history if item.number == number), None),
            )
            continue
        if command.startswith("/"):
            console.print(
                Text("Unknown command. Use /help to see available commands.", style=WARN)
                if HAS_RICH
                else "Unknown command. Use /help to see available commands."
            )
            continue

        # ── run a task ────────────────────────────────────────────────
        task = TaskDisplay(prompt=user_input)
        _apply_event(task, ActivityEvent("task_started", "Task received."))
        events: queue.Queue[ActivityEvent] = queue.Queue()
        first_number = tool_history[-1].number + 1 if tool_history else 1
        handler = AgentEventHandler(events, tool_metadata, first_number)
        messages = compact_conversation_history(history) + [
            {"role": "user", "content": user_input}
        ]
        worker = threading.Thread(
            target=_run_task,
            args=(agent, messages, handler, events),
            daemon=True,
            name="deskagent-task",
        )
        worker.start()

        if HAS_RICH:

            def dashboard(running: bool = True) -> Any:
                return _render_dashboard(
                    task,
                    tool_count=tool_count,
                    model=model,
                    provider=provider,
                    width=console.size.width,
                    height=console.size.height,
                    running=running,
                )

            with Live(
                dashboard(),
                console=console,
                refresh_per_second=10,
                transient=False,
            ) as live:
                while True:
                    try:
                        event = events.get(timeout=0.1)
                    except KeyboardInterrupt:
                        _cancel_unsupported(task)
                        continue
                    except queue.Empty:
                        live.update(dashboard())
                        continue
                    _apply_event(task, event)
                    _track_tool(tool_history, event)
                    finished = event.kind in {"task_completed", "task_failed"}
                    live.update(dashboard(running=not finished))
                    if finished:
                        new_history = _history_from_event(event, messages)
                        if new_history is not None:
                            history = new_history
                        break
            console.print(_result_panel(task))
        else:
            console.print(f"Task received: {_safe_text(user_input, 500)}")
            while True:
                try:
                    event = events.get(timeout=0.15)
                except KeyboardInterrupt:
                    console.print(_plain_event(_cancel_unsupported(task)))
                    continue
                except queue.Empty:
                    continue
                _apply_event(task, event)
                _track_tool(tool_history, event)
                console.print(_plain_event(event))
                if event.kind in {"task_completed", "task_failed"}:
                    new_history = _history_from_event(event, messages)
                    if new_history is not None:
                        history = new_history
                    console.print(task.result)
                    break

        session.tasks += 1
        session.tool_calls += len(task.tools)
        session.busy_time += task.elapsed
        if task.failed:
            session.failed += 1

        if HAS_RICH:
            console.print(_task_summary_line(task, session))
        elif task.failed:
            console.print("Task failed. See the activity timeline for observable errors.")
        else:
            console.print(
                f"Task completed in {task.elapsed:.2f}s using {len(task.tools)} tool call(s)."
            )