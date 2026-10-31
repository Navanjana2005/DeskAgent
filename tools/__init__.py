"""
tools/__init__.py
Auto-discovers all @tool decorated BaseTool instances from every submodule
so that agent.py can do:  import tools as agent_tools
and get all tools via inspect.getmembers().
"""

import importlib
from langchain_core.tools import BaseTool

_SUBMODULES = [
    "tools.file_tools",
    "tools.system_tools",
    "tools.web_tools",
    "tools.media_tools",
    "tools.automation_tools",
    "tools.productivity_tools",
    "tools.image_tools",
    "tools.document_tools",
    "tools.data_tools",
    "tools.security_tools",
    "tools.developer_tools",
    "tools.calculator_auto",
    "tools.default_app_automation",
    "tools.messaging_app_automation",
]

_TOOLS = {}
_TOOL_METADATA = {}

for _module_name in _SUBMODULES:
    try:
        _mod = importlib.import_module(_module_name)
        for _obj in vars(_mod).values():
            if isinstance(_obj, BaseTool):
                _existing = _TOOLS.get(_obj.name)
                if _existing is not None and _existing is not _obj:
                    raise RuntimeError(f"Duplicate tool name: {_obj.name}")
                _TOOLS[_obj.name] = _obj
                _TOOL_METADATA[_obj.name] = {
                    "category": _module_name.replace("tools.", "", 1).replace("_", " "),
                    "description": _obj.description or "",
                }
    except Exception as _e:
        print(f"⚠️  Could not load module {_module_name}: {_e}")

globals().update(_TOOLS)


def get_tools() -> list[BaseTool]:
    """Returns the registered tools in deterministic module order."""
    return list(_TOOLS.values())


def get_tool_metadata() -> dict[str, dict[str, str]]:
    """Returns descriptions and source categories for registered tools."""
    return {name: metadata.copy() for name, metadata in _TOOL_METADATA.items()}


__all__ = ["get_tools", "get_tool_metadata", *_TOOLS]
