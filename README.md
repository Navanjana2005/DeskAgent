# DeskAgent

DeskAgent is a Python terminal assistant that can use OpenRouter or NVIDIA's
OpenAI-compatible endpoint with a modular set of local and external tools.

## Overview

- `agent.py` is the main agent entrypoint.
- `tui.py` is the callback-driven terminal interface (Rich-based, with a plain-text fallback).
- `tools/` contains tool definitions imported by an explicit module registry.
- `agent.py` prompts for an API endpoint before initializing the agent. The
  selected endpoint's API key and a working network connection are required.
- Tool availability depends on optional Python packages, operating-system features, and external services.

## Highlights

- Modular tool discovery via `langchain_core.tools.BaseTool`
- Local utility operations with hosted AI assistance
- Opt-in gate for selected high-impact operations through `ALLOW_DANGEROUS_TOOLS`
- Modern terminal dashboard driven by real LangChain callbacks: live task
  status, phase pipeline, tool execution table with latency bars, and an
  execution timeline
- Results rendered as Markdown in their own panel, so long answers scroll in
  your terminal instead of being clipped
- Built-in session commands (`/history`, `/detail N`, `/stats`) for inspecting
  tool activity
- Standard-library fallback if Rich is unavailable

## Capabilities

- File operations: create, read, copy, move, rename, zip/unzip, search
- Windows automation: app control, UI automation, keyboard/mouse actions
- Web research: browser automation and search utilities (Playwright optional)
- Productivity: notes, todos, timers, conversions
- Media: audio/video utilities, image processing, OCR
- Documents: PDF/Word/Excel handling and document workflows
- Security: hashing, encryption, password generation
- Developer utilities: git info, package tools, safe command gating

## Installation

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install the packages you need:

```powershell
pip install python-dotenv langchain langchain-openai openai psutil requests numpy
```

For the full terminal dashboard, install Rich as well:

```powershell
pip install rich
```

Rich is optional; DeskAgent falls back to a plain terminal interface if it is
not installed. The plain interface prints one line per event and supports the
same commands, but has no panels, colors, spinners, or Markdown rendering.

### Terminal recommendations

The dashboard uses Unicode box-drawing characters and 24-bit gradient colors
(Rich downgrades automatically on 256-color and 16-color terminals).

- Use a terminal with Unicode support, such as Windows Terminal, which works
  well on Windows 10/11. The legacy `cmd.exe` console may render glyphs poorly.
- Use a monospaced font with box-drawing glyphs (for example Cascadia Code,
  JetBrains Mono, or Fira Code).
- A width of 100 columns or more shows the tool table and timeline side by
  side; narrower windows stack them vertically. A height of 32 rows or more
  shows more rows in each panel.

## Configuration

Add the following settings to `.env` in the project directory:

```text
OPENROUTER_API_KEY=
NVIDIA_API_KEY=
FIRECRAWL_API_KEY=
OPENWEATHER_API_KEY=
OPENROUTER_MODEL=nvidia/nemotron-3-ultra-550b-a55b:free
NVIDIA_MODEL=z-ai/glm-5.3-flash
ALLOW_DANGEROUS_TOOLS=0
DESKAGENT_HISTORY_TOKEN_BUDGET=4000
DESKAGENT_HISTORY_MAX_TURNS=4
OPENROUTER_TIMEOUT_SECONDS=180
NVIDIA_TIMEOUT_SECONDS=180
```

At startup, choose `1` for OpenRouter or `2` for NVIDIA. Only the selected
provider's key is required. `OPENROUTER_MODEL` and `NVIDIA_MODEL` independently
select each provider's model. OpenRouter defaults to
`nvidia/nemotron-3-ultra-550b-a55b:free`; NVIDIA defaults to
`z-ai/glm-5.3-flash` at `https://integrate.api.nvidia.com/v1`.
OpenRouter requests enable reasoning and replay returned `reasoning_details`
unchanged in follow-up turns. NVIDIA uses the request settings from the
provided example. Both endpoints use LangChain's OpenAI-compatible chat
adapter for agent/tool orchestration.
`FIRECRAWL_API_KEY` and `OPENWEATHER_API_KEY` are optional and enable their
respective integrations. `ALLOW_DANGEROUS_TOOLS` is a safety setting, not an
API key; keep it at `0` unless you deliberately need a guarded operation.
`OPENROUTER_TIMEOUT_SECONDS` and `NVIDIA_TIMEOUT_SECONDS` set their respective
HTTP timeouts (both default to 180 seconds). Test a provider with
`python "test codes/test_llm_api.py" --provider openrouter` or
`python "test codes/test_llm_api.py" --provider nvidia`.

To limit prompt tokens across a conversation, DeskAgent keeps only recent
completed turns, removes intermediate tool-call/result messages from stored
history, and trims that history to an approximate token budget before the next
request. `DESKAGENT_HISTORY_TOKEN_BUDGET` (default `4000`) and
`DESKAGENT_HISTORY_MAX_TURNS` (default `4`) control those limits. The budget
uses LangChain's approximate message counter, not the model tokenizer, and
does not cap the current user request or the current turn's tool outputs.

The application loads `.env` at startup. Do not commit `.env` or API keys.

## Usage

Run DeskAgent after adding at least one provider API key to `.env`:

```powershell
python agent.py
```

### Terminal UI

On launch, DeskAgent shows a banner with the active provider, model, and number
of registered tools, followed by example prompts and a command list. Type a
request in plain language at the `❯` prompt.

While a task runs, a live dashboard shows:

- **Current task**: an animated spinner, a status pill (for example
  `THINKING` or `EXECUTING TOOL`), elapsed time, your request, and a short
  explanation of what is happening.
- **Phase pipeline**: `Received → Thinking → Tools → Done`. The marker moves
  back to Thinking when the model is called again after a tool finishes, and
  shows a failure marker on the phase where an error occurred.
- **Tool execution**: one row per tool call with a category icon, status
  (running, done, or failed), and a latency bar with duration. A latency
  sparkline appears once two or more tool calls have completed.
- **Timeline**: timestamped model and tool events, with failures highlighted.

When the task finishes, the dashboard stays on screen and the final answer is
printed below it as a Markdown panel, with the elapsed time and tool-call count.
A one-line summary then shows the outcome and running session totals.

The monitor displays real LangChain model/tool callbacks, task duration, tool
arguments, status, and a short result summary. Sensitive tool outputs are
withheld from the activity monitor, and secrets in arguments and output are
redacted before display.

### Commands

| Command | Description |
| --- | --- |
| *(any text)* | Run a natural-language task |
| `/history` | Show recent tool executions with status and latency bars |
| `/detail N` | Inspect tool execution number `N`: category, status, duration, description, arguments, and result summary |
| `/stats` | Show session uptime, tasks run and failed, tool calls, and time spent working |
| `/clear` | Clear the display without changing conversation history or user files |
| `/help` | Show the command list |
| `/quit` | Exit (`exit`, `quit`, and `bye` also work) |

Ctrl+C during a running request does not cancel the underlying invocation;
DeskAgent reports this limitation in the timeline and waits for completion.
Ctrl+C or Ctrl+D at the prompt exits. Model connectivity is only established
when a request is made.

DeskAgent does not currently have a tools-only fallback; startup fails with a
configuration error if the selected provider's API key is missing.

## Customizing the UI

The color theme is defined by a few constants at the top of `tui.py`:
`ACCENT`, `ACCENT2`, `OK`, `WARN`, `ERR`, and `MUTED`. Edit these to restyle
the dashboard. `EXAMPLE_PROMPTS` controls the sample prompts on the welcome
screen, and `PHASES` controls the pipeline labels.

## Security

- Do not commit `.env` or API keys.
- High-impact tools are disabled unless `ALLOW_DANGEROUS_TOOLS=1`.
- Review automation tools before use; they can interact with your desktop and
  access local files. Tool results may be sent to the hosted model.
- The activity monitor redacts known credential patterns and secret-like
  argument names, but redaction is best-effort. Do not rely on it as your only
  protection when sharing screenshots or logs.

## Key files

- `agent.py` — agent orchestration and application entry point
- `tui.py` — callback-driven terminal presentation (dashboard, commands, plain-text fallback)
- `tools/` — modular tool definitions
- `.env` — local, ignored credentials configuration (create manually)