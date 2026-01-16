# app/agent/tools/vision.py
from app.agent.tools.base_tool import BaseTool

try:
    import mss
    import mss.tools
    GUI_AVAILABLE = True
except (ImportError, KeyError, OSError):
    mss = None
    GUI_AVAILABLE = False

class _UnavailableTool(BaseTool):
    """A placeholder for a tool that is not available in the current environment."""
    _description = "This tool is not available in the current environment."
    @property
    def description(self):
        return self._description

    def execute(self, *args, **kwargs):
        return self._safe_execute(lambda: (_ for _ in ()).throw(Exception(self._description)))

if GUI_AVAILABLE:
    class ScreenshotTool(BaseTool):
        """Takes a screenshot of the entire screen and saves it to a file."""
        def execute(self, output_path: str = "screenshot.png"):
            def _take_screenshot():
                with mss.mss() as sct:
                    filename = sct.shot(output=output_path)
                return f"Screenshot saved to '{filename}'."
            return self._safe_execute(_take_screenshot)
else:
    class ScreenshotTool(_UnavailableTool):
        description = "Screen capture is not available in this environment."
