# app/agent/tools/gui_control.py
import platform
from app.agent.tools.base_tool import BaseTool

IS_WINDOWS = platform.system() == "Windows"

if IS_WINDOWS:
    import pyautogui

class _UnavailableTool(BaseTool):
    """A placeholder for a tool that is not available on this OS."""
    _description = "This tool is only available on Windows."
    @property
    def description(self):
        return self._description

    def execute(self, *args, **kwargs):
        return self._safe_execute(lambda: (_ for _ in ()).throw(Exception(self._description)))

if IS_WINDOWS:
    class MouseClickTool(BaseTool):
        """Clicks the mouse at a specified (x, y) coordinate."""
        def execute(self, x: int, y: int, button: str = 'left'):
            return self._safe_execute(pyautogui.click, x, y, button=button)

    class TypeTextTool(BaseTool):
        """Types the given text using the keyboard."""
        def execute(self, text: str):
            return self._safe_execute(pyautogui.typewrite, text, interval=0.05)

    class HotkeyTool(BaseTool):
        """Presses a combination of hotkeys (e.g., 'ctrl', 'c')."""
        def execute(self, *keys):
            return self._safe_execute(pyautogui.hotkey, *keys)
else:
    class MouseClickTool(_UnavailableTool):
        pass
    class TypeTextTool(_UnavailableTool):
        pass
    class HotkeyTool(_UnavailableTool):
        pass
