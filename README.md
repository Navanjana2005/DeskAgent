# DeskAgent

DeskAgent is a modern, local-first Python assistant with a modular tools system and a polished terminal experience.

## Overview

- `agent.py` is the main agent entrypoint.
- `tools/` contains extensible, auto-discovered tool definitions.
- When `rich` is installed, DeskAgent uses a colorized CLI with panels, tables, and prompts.
- If LLM support is unavailable, DeskAgent falls back to a tools-only interactive mode.
- Optional LLM support is provided through `MISTRAL_API_KEY`.

## Highlights

- Modular tool discovery via `langchain_core.tools.BaseTool`
- Local-first utility operations with optional AI assistance
- Safe defaults: dangerous actions are gated behind `.env` flags
- Modern CLI experience with `rich`
- Tools-only usability without an LLM key

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
pip install python-dotenv rich langchain langchain-mistralai
```

## Configuration

Copy `.env.example` to `.env`:

```powershell
copy .env.example .env
```

Set optional values:

```text
MISTRAL_API_KEY=your_api_key_here
MISTRAL_MODEL=mistral-medium
ALLOW_DANGEROUS_TOOLS=0
```

> `ALLOW_DANGEROUS_TOOLS` should remain `0` in public or untrusted environments.

## Usage

Run DeskAgent in tools-only mode:

```powershell
python agent.py
```

Run with optional LLM support when configured:

```powershell
setx MISTRAL_API_KEY "your_key_here"
python agent.py
```

## Behavior

- If `rich` is installed, DeskAgent presents a styled CLI with tool tables and prompts.
- If no LLM key or model packages are found, it stays in tools-only mode.
- If LLM support is available, DeskAgent attempts an LLM-backed agent flow.

## Security

- Do not commit `.env` or API keys.
- `.env.example` is safe to publish.
- Review any automation tools before use; they can interact with your desktop.
