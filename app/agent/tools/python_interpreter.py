# app/agent/tools/python_interpreter.py
import subprocess
import sys
from app.agent.tools.base_tool import BaseTool

class PythonInterpreterTool(BaseTool):
    """
    Executes Python code in a sandboxed environment using a separate subprocess.
    """

    def execute(self, code: str):
        """
        Executes the given Python code and captures its output.
        """
        if self._is_code_dangerous(code):
            return self._safe_execute(lambda: (_ for _ in ()).throw(Exception("Execution denied: Potentially dangerous code.")))

        return self._safe_execute(self._run_code, code)

    def _run_code(self, code: str):
        """
        Runs the code in a new Python process.
        """
        process = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            timeout=30
        )
        return {
            "stdout": process.stdout,
            "stderr": process.stderr,
            "return_code": process.returncode
        }

    def _is_code_dangerous(self, code: str) -> bool:
        """
        Basic check for dangerous keywords.
        """
        dangerous_keywords = ["os.system", "subprocess", "shutil", "eval", "exec", "open", "socket"]

        if "import os" in code or "import subprocess" in code or "import shutil" in code:
            return True

        for keyword in dangerous_keywords:
            if keyword in code:
                return True

        return False

    def get_description(self):
        return "Executes a string of Python code and returns its stdout, stderr, and return code."
