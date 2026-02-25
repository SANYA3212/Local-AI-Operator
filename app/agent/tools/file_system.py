# app/agent/tools/file_system.py
import os
import shutil
from app.agent.tools.base_tool import BaseTool

# Define a list of protected directories to prevent the agent from modifying system files
PROTECTED_DIRS = [
    os.environ.get("WINDIR", "C:\\Windows").lower(),
    os.environ.get("ProgramFiles", "C:\\Program Files").lower(),
    os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)").lower(),
]

def is_path_protected(path: str):
    """Checks if a given path is within a protected directory."""
    abs_path = os.path.abspath(path).lower()
    return any(abs_path.startswith(p) for p in PROTECTED_DIRS)

class WriteFileTool(BaseTool):
    """Writes content to a specified file. Fails if the path is in a protected system directory."""

    def execute(self, path: str, content: str):
        if is_path_protected(path):
            return self._safe_execute(lambda: (_ for _ in ()).throw(Exception(f"Access to protected path '{path}' is denied.")))
        return self._safe_execute(self._write_file, path, content)

    def _write_file(self, path: str, content: str):
        dir_name = os.path.dirname(path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"File '{path}' written successfully."

class ReadFileTool(BaseTool):
    """Reads the content of a specified file."""

    def execute(self, path: str):
        return self._safe_execute(self._read_file, path)

    def _read_file(self, path: str):
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()

class ListFilesTool(BaseTool):
    """Lists all files and directories in a specified path."""

    def execute(self, path: str = '.'):
        return self._safe_execute(self._list_files, path)

    def _list_files(self, path: str):
        return os.listdir(path)

class DeleteFileTool(BaseTool):
    """Deletes a specified file. Fails if the path is in a protected system directory."""

    def execute(self, path: str):
        if is_path_protected(path):
            return self._safe_execute(lambda: (_ for _ in ()).throw(Exception(f"Access to protected path '{path}' is denied.")))
        return self._safe_execute(self._delete_file, path)

    def _delete_file(self, path: str):
        os.remove(path)
        return f"File '{path}' deleted successfully."

class CreateDirectoryTool(BaseTool):
    """Creates a new directory at the specified path. Fails if the path is in a protected system directory."""

    def execute(self, path: str):
        if is_path_protected(path):
            return self._safe_execute(lambda: (_ for _ in ()).throw(Exception(f"Access to protected path '{path}' is denied.")))
        return self._safe_execute(self._create_directory, path)

    def _create_directory(self, path: str):
        os.makedirs(path, exist_ok=True)
        return f"Directory '{path}' created successfully."

class DeleteDirectoryTool(BaseTool):
    """Deletes a specified directory and all its contents. Fails if the path is in a protected system directory."""

    def execute(self, path: str):
        if is_path_protected(path):
            return self._safe_execute(lambda: (_ for _ in ()).throw(Exception(f"Access to protected path '{path}' is denied.")))
        return self._safe_execute(self._delete_directory, path)

    def _delete_directory(self, path: str):
        shutil.rmtree(path)
        return f"Directory '{path}' deleted successfully."
