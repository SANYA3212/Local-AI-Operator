# app/agent/tools/wait.py
import time
from app.agent.tools.base_tool import BaseTool

class WaitTool(BaseTool):
    """
    Waits for a specified number of seconds before the next action.
    Example: `wait(seconds=2)` to wait for 2 seconds.
    """
    def execute(self, seconds: int):
        def _wait():
            time.sleep(seconds)
            return f"Waited for {seconds} seconds."
        return self._safe_execute(_wait)
