"""
tools/developer_tools.py
Developer tools: Git, pip management, Python code runner, and VS Code opener.
All use subprocess — no external API keys required.
"""

import os
import sys
import io
import subprocess
import traceback
from langchain_core.tools import tool
from tools.safety import dangerous_tools_enabled


# ─────────────────────────────────────────────────────────────────────────────
# GIT TOOLS
# ─────────────────────────────────────────────────────────────────────────────

@tool
def git_status(repo_path: str = ".") -> str:
    """Shows the git status of a repository (modified, untracked, staged files).

    Args:
        repo_path: Path to the git repository (default: current directory '.').
    """
    try:
        result = subprocess.run(
            ["git", "status"],
            cwd=os.path.abspath(repo_path),
            capture_output=True, text=True, timeout=15
        )
        if result.returncode != 0:
            return f"❌ Git error: {result.stderr.strip()}"
        return f"📁 Git Status — {os.path.abspath(repo_path)}\n{'─' * 50}\n{result.stdout.strip()}"
    except FileNotFoundError:
        return "❌ git is not installed or not on PATH."
    except Exception as e:
        return f"❌ Error: {e}"


@tool
def git_log(repo_path: str = ".", num_commits: int = 10) -> str:
    """Shows recent git commit history.

    Args:
        repo_path: Path to the git repository (default: '.').
        num_commits: Number of commits to show (default 10).
    """
    try:
        result = subprocess.run(
            ["git", "log", f"--max-count={num_commits}",
             "--pretty=format:%h  %ad  %an  %s", "--date=short"],
            cwd=os.path.abspath(repo_path),
            capture_output=True, text=True, timeout=15
        )
        if result.returncode != 0:
            return f"❌ Git error: {result.stderr.strip()}"
        if not result.stdout.strip():
            return "No commits found."
        header = f"{'Hash':<8}  {'Date':<12}  {'Author':<20}  Message\n" + "─" * 70 + "\n"
        return f"📜 Git Log (last {num_commits} commits)\n{header}{result.stdout.strip()}"
    except FileNotFoundError:
        return "❌ git is not installed or not on PATH."
    except Exception as e:
        return f"❌ Error: {e}"


@tool
def git_commit(repo_path: str, message: str, add_all: bool = True) -> str:
    """Stages changes and creates a git commit.

    Args:
        repo_path: Path to the git repository.
        message: Commit message.
        add_all: If True, stages all changes with 'git add -A' first (default True).
    """
    if not dangerous_tools_enabled():
        return (
            "⛔ Disabled for safety. Set ALLOW_DANGEROUS_TOOLS=1 in your environment to enable."
        )
    try:
        abs_path = os.path.abspath(repo_path)
        if add_all:
            add_result = subprocess.run(
                ["git", "add", "-A"],
                cwd=abs_path, capture_output=True, text=True, timeout=15
            )
            if add_result.returncode != 0:
                return f"❌ git add failed: {add_result.stderr.strip()}"

        commit_result = subprocess.run(
            ["git", "commit", "-m", message],
            cwd=abs_path, capture_output=True, text=True, timeout=15
        )
        if commit_result.returncode != 0:
            return f"❌ git commit failed: {commit_result.stderr.strip()}"
        return f"✅ Committed!\n{commit_result.stdout.strip()}"
    except FileNotFoundError:
        return "❌ git is not installed or not on PATH."
    except Exception as e:
        return f"❌ Error: {e}"


@tool
def git_diff(repo_path: str = ".", file_path: str = "") -> str:
    """Shows uncommitted changes in a git repository.

    Args:
        repo_path: Path to the git repository (default: '.').
        file_path: Specific file to diff (optional, shows all changes if empty).
    """
    try:
        cmd = ["git", "diff", "--stat"] if not file_path else ["git", "diff", file_path]
        result = subprocess.run(
            cmd,
            cwd=os.path.abspath(repo_path),
            capture_output=True, text=True, timeout=15
        )
        if result.returncode != 0:
            return f"❌ Git error: {result.stderr.strip()}"
        return result.stdout.strip() or "✅ No changes (working tree is clean)."
    except FileNotFoundError:
        return "❌ git is not installed or not on PATH."
    except Exception as e:
        return f"❌ Error: {e}"


# ─────────────────────────────────────────────────────────────────────────────
# PIP TOOLS
# ─────────────────────────────────────────────────────────────────────────────

@tool
def install_pip_package(package_name: str) -> str:
    """Installs a Python package using pip.

    Args:
        package_name: Package name to install (e.g., 'requests', 'pandas==2.0.0').
    """
    if not dangerous_tools_enabled():
        return (
            "⛔ Disabled for safety. Set ALLOW_DANGEROUS_TOOLS=1 in your environment to enable."
        )
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", package_name],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode == 0:
            # Extract the key "Successfully installed" line
            lines = result.stdout.strip().splitlines()
            summary = next((l for l in lines if "Successfully installed" in l or "already satisfied" in l), "")
            return f"✅ {summary or 'Package installed.'}\n{package_name}"
        return f"❌ pip install failed:\n{result.stderr.strip()}"
    except Exception as e:
        return f"❌ Error: {e}"


@tool
def list_pip_packages(filter_query: str = "") -> str:
    """Lists installed Python packages, optionally filtered by name.

    Args:
        filter_query: Optional text to filter package names (e.g., 'lang' to find langchain).
    """
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "list", "--format=columns"],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0:
            return f"❌ pip list failed: {result.stderr.strip()}"
        lines = result.stdout.strip().splitlines()
        if filter_query:
            lines = [lines[0], lines[1]] + [
                l for l in lines[2:] if filter_query.lower() in l.lower()
            ]
            if len(lines) <= 2:
                return f"No packages found matching '{filter_query}'."
        return f"📦 Installed Packages ({len(lines) - 2} shown):\n" + "\n".join(lines[:52])
    except Exception as e:
        return f"❌ Error: {e}"


@tool
def uninstall_pip_package(package_name: str) -> str:
    """Uninstalls a Python package using pip.

    Args:
        package_name: Package name to uninstall (e.g., 'requests').
    """
    if not dangerous_tools_enabled():
        return (
            "⛔ Disabled for safety. Set ALLOW_DANGEROUS_TOOLS=1 in your environment to enable."
        )
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "uninstall", "-y", package_name],
            capture_output=True, text=True, timeout=60
        )
        if result.returncode == 0:
            return f"✅ Uninstalled: {package_name}\n{result.stdout.strip()}"
        return f"❌ pip uninstall failed:\n{result.stderr.strip()}"
    except Exception as e:
        return f"❌ Error: {e}"


# ─────────────────────────────────────────────────────────────────────────────
# PYTHON CODE RUNNER
# ─────────────────────────────────────────────────────────────────────────────

@tool
def run_python_code(code: str) -> str:
    """Executes a Python code snippet and returns the output and any errors.

    Args:
        code: Python code to execute. Use print() to produce output.
              Multi-line code is supported.

    Example:
        code = "for i in range(3): print(i * 2)"
    """
    if not dangerous_tools_enabled():
        return (
            "⛔ Disabled for safety. Set ALLOW_DANGEROUS_TOOLS=1 in your environment to enable."
        )
    try:
        # Capture stdout
        old_stdout = sys.stdout
        sys.stdout = buffer = io.StringIO()

        try:
            exec(code, {"__builtins__": __builtins__})  # noqa: S102
            output = buffer.getvalue()
        except Exception:
            output = buffer.getvalue()
            error = traceback.format_exc()
            sys.stdout = old_stdout
            return (
                f"⚠️  Code ran with error:\n"
                f"Output so far:\n{output}\n"
                f"Error:\n{error}"
            )
        finally:
            sys.stdout = old_stdout

        if not output.strip():
            return "✅ Code executed successfully (no output produced)."
        return f"✅ Output:\n{output.strip()}"
    except Exception as e:
        return f"❌ Error executing code: {e}"


# ─────────────────────────────────────────────────────────────────────────────
# VS CODE
# ─────────────────────────────────────────────────────────────────────────────

@tool
def open_in_vscode(path: str) -> str:
    """Opens a file or folder in Visual Studio Code.

    Args:
        path: Path to a file or directory to open in VS Code.
    """
    try:
        abs_path = os.path.abspath(path)
        if not os.path.exists(abs_path):
            return f"❌ Path not found: {abs_path}"
        result = subprocess.run(
            ["code", abs_path],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode != 0 and result.stderr:
            return f"❌ VS Code error: {result.stderr.strip()}"
        return f"✅ Opened in VS Code: {abs_path}"
    except FileNotFoundError:
        return "❌ VS Code ('code') is not installed or not on PATH."
    except Exception as e:
        return f"❌ Error: {e}"


# ─────────────────────────────────────────────────────────────────────────────
# TERMINAL
# ─────────────────────────────────────────────────────────────────────────────

@tool
def run_commands_in_terminal(command: str) -> str:
    """Executes a shell command and returns its output.

    Args:
        command: The shell command to execute (e.g., 'dir', 'echo hello', 'python --version').
    """
    if not dangerous_tools_enabled():
        return (
            "⛔ Disabled for safety. Set ALLOW_DANGEROUS_TOOLS=1 in your environment to enable."
        )
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            return f"✅ Command executed:\n{result.stdout.strip()}"
        return f"❌ Command failed (exit {result.returncode}):\n{result.stderr.strip()}"
    except subprocess.TimeoutExpired:
        return "⏱️  Command timed out after 30 seconds."
    except Exception as e:
        return f"❌ Error: {e}"
