import os
import inspect
import json
try:
    import dotenv
    dotenv.load_dotenv()
except Exception:
    pass

from langchain_core.tools import BaseTool
import tools as agent_tools  # modular tools package

try:
    from rich.console import Console
    from rich.prompt import Prompt
    from rich.table import Table
    from rich.panel import Panel
    from rich.syntax import Syntax
    from rich.text import Text
    RICH_ENABLED = True
    console = Console()
except Exception:
    RICH_ENABLED = False
    console = None

# Prefer creating an LLM-backed agent when credentials and packages exist,
# but do not fail import-time if an API key or the model package is missing.
llm = None
agent = None
tool_list = [obj for name, obj in inspect.getmembers(agent_tools) if isinstance(obj, BaseTool)]

try:
    from langchain.agents import create_agent
    from langchain_mistralai.chat_models import ChatMistralAI
    MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
    MISTRAL_MODEL = os.getenv("MISTRAL_MODEL", "mistral-medium")
    if MISTRAL_API_KEY:
        try:
            llm = ChatMistralAI(api_key=MISTRAL_API_KEY, model=MISTRAL_MODEL)
            if RICH_ENABLED:
                console.print(Panel(f"✅ LLM configured with model: {MISTRAL_MODEL}", title="DeskAgent", subtitle="LLM enabled", style="bold green"))
            else:
                print(f"✅ LLM configured with model: {MISTRAL_MODEL}")
        except Exception as e:
            if RICH_ENABLED:
                console.print(Panel(f"⚠️  Could not initialize LLM: {e}", title="DeskAgent", style="bold yellow"))
            else:
                print(f"⚠️  Could not initialize LLM: {e}")
    else:
        if RICH_ENABLED:
            console.print(Panel("⚠️  MISTRAL_API_KEY not found — running in tools-only mode.", title="DeskAgent", style="bold yellow"))
        else:
            print("⚠️  MISTRAL_API_KEY not found — running in tools-only mode.")
except Exception as e:
    if RICH_ENABLED:
        console.print(Panel("⚠️  LLM packages not available — running in tools-only mode.", title="DeskAgent", style="bold yellow"))
    else:
        print("⚠️  LLM packages not available — running in tools-only mode.")


if not tool_list:
    if RICH_ENABLED:
        console.print(Panel("⚠️  No tools discovered in tools/ — ensure functions are decorated with @tool", title="DeskAgent", style="bold red"))
    else:
        print("⚠️  No tools discovered in tools/ — ensure functions are decorated with @tool")
else:
    if RICH_ENABLED:
        header = Text("DeskAgent", style="bold magenta")
        sub = Text(f"  {len(tool_list)} tools loaded", style="bright_cyan")
        console.print(Panel(header + sub, title="Welcome", subtitle="Your local command center", border_style="magenta"))
    else:
        print(f"✅ Discovered {len(tool_list)} tools: {[t.name for t in tool_list]}")


def _print_panel(message: str, title: str = "DeskAgent", style: str = "green"):
    if RICH_ENABLED:
        console.print(Panel(Text(message, style="white"), title=title, border_style=style))
    else:
        print(message)


def _syntax_panel(content: str, title: str = "Result", style: str = "green"):
    if RICH_ENABLED:
        syntax = Syntax(content, "text", theme="monokai", line_numbers=False)
        console.print(Panel(syntax, title=title, border_style=style))
    else:
        print(f"{title}:\n{content}")


def _tools_cli():
    """Simple interactive CLI for listing and invoking tools when LLM is unavailable.

    The CLI shows available tools, their docstrings, and accepts JSON arguments
    to invoke them. This is safe for publishing and keeps the project usable
    without requiring an LLM key at import time.
    """
    tools_by_name = {t.name: t for t in tool_list}

    _print_panel("🤖 DeskAgent tools-only mode is active. Type 'exit' to quit.", title="DeskAgent", style="bright_blue")
    while True:
        try:
            if RICH_ENABLED:
                table = Table(title="Available Tools", title_style="bold cyan")
                table.add_column("#", justify="right", style="bright_magenta")
                table.add_column("Tool", style="bold white")
                table.add_column("Description", style="cyan")
                for i, t in enumerate(tool_list, 1):
                    table.add_row(str(i), t.name, (t.description or "-")[:60])
                console.print(table)
            else:
                for i, t in enumerate(tool_list, 1):
                    print(f"{i}. {t.name} — {(t.description or '-')[:60]}")

            if RICH_ENABLED:
                choice = Prompt.ask("Select a tool number or name", default="", show_default=False).strip()
            else:
                choice = input("Enter tool number or name (or 'exit'): ").strip()
        except (EOFError, KeyboardInterrupt):
            _print_panel("Goodbye!", title="Exit", style="bright_red")
            break
        if choice.lower() in ("exit", "quit"):
            print("Goodbye!")
            break
        if not choice:
            continue

        # Resolve by number or name
        selected = None
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(tool_list):
                selected = tool_list[idx]
        else:
            selected = tools_by_name.get(choice) or next((t for t in tool_list if t.name == choice), None)

        if not selected:
            _print_panel("❌ Tool not found — enter a valid number or exact tool name.", title="Not Found", style="bright_red")
            continue

        _print_panel(f"Selected: [bold green]{selected.name}[/]\n{selected.description or 'No description.'}", title="Tool Selected", style="bright_green")
        prompt_text = "Enter tool arguments as JSON on one line (e.g. {\"path\": \"./file.txt\"}), or {} for none."
        if RICH_ENABLED:
            args_line = Prompt.ask(prompt_text, default="", show_default=False).strip()
        else:
            print(prompt_text)
            args_line = input("Args: ").strip()
        try:
            args = json.loads(args_line) if args_line else {}
            if not isinstance(args, dict):
                _print_panel("❌ Expected a JSON object mapping parameter names to values.", title="Invalid Input", style="bright_red")
                continue
        except Exception as e:
            _print_panel(f"❌ Invalid JSON: {e}", title="Invalid JSON", style="bright_red")
            continue

        try:
            result = selected.run(**args)
            _syntax_panel(str(result), title="Result", style="bright_blue")
        except Exception as e:
            _print_panel(f"❌ Tool raised an exception: {e}", title="Error", style="bright_red")


def chat():
    # If we have an LLM and tool_list, prefer the LLM-driven agent flow.
    if llm is not None and tool_list:
        try:
            agent = create_agent(model=llm, tools=tool_list)
        except Exception as e:
            _print_panel(f"⚠️  Could not create LLM-backed agent: {e}\nFalling back to tools CLI.", title="Fallback", style="bright_yellow")
            _tools_cli()
            return

        _print_panel("🤖 DeskAgent is online. Ask a question or type 'exit' to quit.", title="DeskAgent", style="bright_blue")
        history = []
        while True:
            try:
                if RICH_ENABLED:
                    user_input = Prompt.ask("You")
                else:
                    user_input = input("You: ")
            except (EOFError, KeyboardInterrupt):
                _print_panel("Goodbye!", title="Exit", style="bright_red")
                break
            if user_input.lower() in ("exit", "quit", "bye"):
                _print_panel("Goodbye!", title="Exit", style="bright_red")
                break
            if not user_input.strip():
                continue
            history.append({"role": "user", "content": user_input})
            try:
                response = agent.invoke({"messages": history})
                reply = response["messages"][-1].content
            except Exception as e:
                reply = f"❌ Agent error: {e}"
            _print_panel(reply, title="Agent", style="bright_green")
            history.append({"role": "assistant", "content": reply})
    else:
        _tools_cli()


if __name__ == "__main__":
    chat()
