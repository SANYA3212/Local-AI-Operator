# app/agent/tool_registry.py
from app.agent.tools.file_system import (
    WriteFileTool, ReadFileTool, ListFilesTool,
    DeleteFileTool, CreateDirectoryTool, DeleteDirectoryTool
)
from app.agent.tools.python_interpreter import PythonInterpreterTool
from app.agent.tools.shell import ShellCommandTool, GetOSInfoTool
from app.agent.tools.gui_control import MouseClickTool, TypeTextTool, HotkeyTool
from app.agent.tools.windows_control import GetActiveWindowTool, MaximizeWindowTool
from app.agent.tools.vision import ScreenshotTool

# The registry is a simple dictionary that maps tool names to their class instances.
# The Executor will use this registry to find and execute the appropriate tool.
TOOL_REGISTRY = {
    # File System Tools
    "write_file": WriteFileTool(),
    "read_file": ReadFileTool(),
    "list_files": ListFilesTool(),
    "delete_file": DeleteFileTool(),
    "create_directory": CreateDirectoryTool(),
    "delete_directory": DeleteDirectoryTool(),

    # Python Interpreter
    "python_interpreter": PythonInterpreterTool(),

    # Shell Command
    "get_os_info": GetOSInfoTool(),
    "shell_command": ShellCommandTool(),

    # GUI Control (Windows-specific)
    "mouse_click": MouseClickTool(),
    "type_text": TypeTextTool(),
    "hotkey": HotkeyTool(),

    # Window Management (Windows-specific)
    "get_active_window": GetActiveWindowTool(),
    "maximize_window": MaximizeWindowTool(),

    # Vision
    "take_screenshot": ScreenshotTool(),
}

def get_tool(name: str):
    """Retrieves a tool instance from the registry by its name."""
    tool = TOOL_REGISTRY.get(name)
    if not tool:
        raise ValueError(f"Инструмент '{name}' не найден в реестре.")
    return tool

def get_tool_descriptions():
    """Returns a formatted string of all tool names and their descriptions."""
    return "\n".join(
        f"- {name}: {tool.description}"
        for name, tool in TOOL_REGISTRY.items()
    )
