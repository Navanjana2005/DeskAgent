import os


def dangerous_tools_enabled() -> bool:
    """Checks the opt-in flag when a guarded tool is invoked."""
    return os.getenv("ALLOW_DANGEROUS_TOOLS", "0") == "1"
