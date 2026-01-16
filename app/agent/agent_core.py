# app/agent/agent_core.py
import threading
import sys
from app.agent.planner import Planner
from app.agent.executor import Executor
from app.agent.tools.file_system import WriteFileTool, ReadFileTool, ListFilesTool
from app.agent.tools.shell import ShellCommandTool
from app.agent.tools.gui_control import MouseClickTool, TypeTextTool, HotkeyTool
from app.agent.tools.windows_control import GetActiveWindowTool, MaximizeWindowTool
from app.agent.tools.vision import ScreenshotTool
from app.agent.tools.python_interpreter import PythonInterpreterTool

class AgentCore(threading.Thread):
    def __init__(self, task, model, chat_id, socketio_instance):
        super().__init__()
        self.task = task
        self.model = model
        self.chat_id = chat_id
        self.socketio = socketio_instance
        self.stop_event = threading.Event()

        self.tools = {
            "write_file": WriteFileTool(),
            "read_file": ReadFileTool(),
            "list_files": ListFilesTool(),
            "shell_command": ShellCommandTool(),
            "mouse_click": MouseClickTool(),
            "type_text": TypeTextTool(),
            "hotkey": HotkeyTool(),
            "get_active_window": GetActiveWindowTool(),
            "maximize_window": MaximizeWindowTool(),
            "take_screenshot": ScreenshotTool(),
            "python_interpreter": PythonInterpreterTool(),
        }

    def run(self):
        self.log_and_emit("agent", f"Task received: \"{self.task}\". Starting planning process...")

        if self.stop_event.is_set(): return

        planner = Planner(self.model)
        plan = planner.generate_plan(self.task, list(self.tools.keys()))

        if plan and not plan[0].startswith("Error:"):
            plan_str = "\n".join([f"{i+1}. {step}" for i, step in enumerate(plan)])
            self.log_and_emit("plan", f"**Generated Plan:**\n{plan_str}")
        else:
            error_message = plan[0] if plan else "Failed to generate a plan."
            self.log_and_emit("agent", f"Error during planning: {error_message}")
            self.log_and_emit("agent", "Task aborted due to planning failure.")
            return

        if self.stop_event.is_set(): return

        executor = Executor(self.model, self.tools, self.socketio, self.chat_id)

        for i, step in enumerate(plan):
            if self.stop_event.is_set():
                self.log_and_emit("agent", "Task execution stopped by user.")
                break

            self.log_and_emit("agent", f"--- Starting Step {i+1}/{len(plan)} ---")
            executor.execute_step(step, self.task)
            executor.history = []

        if not self.stop_event.is_set():
            self.log_and_emit("agent", "All steps executed. Task finished.")

        sys.stdout.flush()

    def log_and_emit(self, sender, content):
        print(f"[{sender.upper()}] CHAT_ID({self.chat_id}): {content}", file=sys.stdout)

        self.socketio.emit('agent_response', {
            'chat_id': self.chat_id,
            'sender': sender,
            'message': content
        })

    def stop(self):
        self.stop_event.set()
