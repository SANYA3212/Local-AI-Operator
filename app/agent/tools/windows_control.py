# app/agent/tools/windows_control.py
import platform
from app.agent.tools.base_tool import BaseTool

IS_WINDOWS = platform.system() == "Windows"

if IS_WINDOWS:
    import pygetwindow as gw

class _UnavailableTool(BaseTool):
    """A placeholder for a tool that is not available on this OS."""
    description = "This tool is only available on Windows."
    def execute(self, *args, **kwargs):
        return self._safe_execute(lambda: (_ for _ in ()).throw(Exception(self.description)))
    def get_description(self):
        return self.description

if IS_WINDOWS:
    class GetActiveWindowTool(BaseTool):
        """Gets the title of the currently active window."""
        def execute(self):
            def _get_active_window():
                active_window = gw.getActiveWindow()
                return f"Active window is: '{active_window.title}'" if active_window else "No active window found."
            return self._safe_execute(_get_active_window)

    class MaximizeWindowTool(BaseTool):
        """Maximizes the window with the specified title."""
        def execute(self, title: str):
            def _maximize_window():
                windows = gw.getWindowsWithTitle(title)
                if windows:
                    windows[0].maximize()
                    return f"Window '{title}' maximized."
                return f"Window with title '{title}' not found."
            return self._safe_execute(_maximize_window)
else:
    class GetActiveWindowTool(_UnavailableTool):
        pass
    class MaximizeWindowTool(_UnavailableTool):
        pass
