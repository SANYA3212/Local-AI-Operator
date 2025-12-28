# app/agent/tools/shell.py
import subprocess
import shlex
import platform
from app.agent.tools.base_tool import BaseTool

# Define a blacklist of dangerous commands to prevent the agent from executing them
DANGEROUS_COMMANDS = {
    "linux": ["rm", "sudo", "mv", "mkfs"],
    "windows": ["del", "rd", "rmdir", "format", "powershell"],
    "darwin": ["rm", "sudo", "mv"]
}

class ShellCommandTool(BaseTool):
    """Executes a command in the system's shell securely. Dangerous commands are blocked."""

    def execute(self, command: str):
        return self._safe_execute(self._run_command, command)

    def _run_command(self, command: str):
        """
        Executes a command, checking against a blacklist of dangerous commands first.
        """
        try:
            cmd_list = shlex.split(command)
            if not cmd_list:
                raise ValueError("Command cannot be empty.")

            # Check if the command is in the blacklist for the current OS
            os_type = platform.system().lower()
            if cmd_list[0].lower() in DANGEROUS_COMMANDS.get(os_type, []):
                raise PermissionError(f"Command '{cmd_list[0]}' is blocked for security reasons.")

            result = subprocess.run(
                cmd_list,
                shell=False,
                check=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            output = ""
            if result.stdout:
                output += f"STDOUT:\n{result.stdout}\n"
            if result.stderr:
                output += f"STDERR:\n{result.stderr}\n"

            return output if output else "Command executed successfully with no output."

        except subprocess.CalledProcessError as e:
            return f"Command failed with exit code {e.returncode}.\nSTDOUT:\n{e.stdout}\nSTDERR:\n{e.stderr}"
        except subprocess.TimeoutExpired:
            return "Command timed out after 30 seconds."
        except FileNotFoundError:
            return f"Error: Command '{shlex.split(command)[0]}' not found. Make sure it is in your PATH."
        except (PermissionError, ValueError) as e:
            return f"Error: {e}"
