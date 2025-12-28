# app/agent/agent_core.py
import threading
import json
from app.utils import ollama_generate
from app.agent.tools.file_system import WriteFileTool, ReadFileTool, ListFilesTool
from app.agent.tools.shell import ShellCommandTool
from app.agent.tools.gui_control import MouseClickTool, TypeTextTool, HotkeyTool
from app.agent.tools.windows_control import GetActiveWindowTool, MaximizeWindowTool
from app.agent.tools.vision import ScreenshotTool

class AgentCore(threading.Thread):
    def __init__(self, task, model, chat_id, socketio_instance):
        super().__init__()
        self.task = task
        self.model = model
        self.chat_id = chat_id
        self.socketio = socketio_instance
        self.stop_event = threading.Event()

        self.tools = {
            # File System
            "write_file": WriteFileTool(),
            "read_file": ReadFileTool(),
            "list_files": ListFilesTool(),
            # Shell
            "shell_command": ShellCommandTool(),
            # GUI Control
            "mouse_click": MouseClickTool(),
            "type_text": TypeTextTool(),
            "hotkey": HotkeyTool(),
            # Window Management
            "get_active_window": GetActiveWindowTool(),
            "maximize_window": MaximizeWindowTool(),
            # Vision
            "take_screenshot": ScreenshotTool(),
        }

        self.history = []

    def run(self):
        """The main loop of the agent."""
        self.add_to_history("agent", f"Starting task: {self.task}")

        for _ in range(10): # Add a limit of 10 steps to prevent infinite loops
            if self.stop_event.is_set():
                break

            # 1. PLAN
            plan = self.plan_next_step()
            if not plan or "error" in plan:
                self.add_to_history("agent", "Could not create a plan. Stopping.")
                break

            tool_name = plan.get("tool")
            tool_args = plan.get("args", {})

            if tool_name == "task_complete":
                self.add_to_history("agent", "Task marked as complete.")
                break

            # 2. ACT
            self.add_to_history("agent", f"Executing tool: `{tool_name}` with args: `{tool_args}`")
            if tool_name in self.tools:
                tool = self.tools[tool_name]
                observation = tool.execute(**tool_args)
            else:
                observation = json.dumps({"status": "error", "message": f"Tool '{tool_name}' not found."})

            # 3. OBSERVE & ANALYZE
            self.add_to_history("observation", f"Result:\n```\n{observation}\n```")

        self.add_to_history("agent", "Task finished.")

    def plan_next_step(self):
        """Generates the next step using the LLM."""
        prompt = self.construct_planning_prompt()
        response_text = ollama_generate(self.model, prompt).get("response", "")

        try:
            json_part = response_text[response_text.find('{'):response_text.rfind('}')+1]
            return json.loads(json_part)
        except (json.JSONDecodeError, IndexError):
            self.add_to_history("agent", f"Error decoding LLM plan: {response_text}")
            return {"error": "Failed to decode plan"}

    def construct_planning_prompt(self):
        tools_description = "\n".join([f"- `{name}`: {tool.get_description()}" for name, tool in self.tools.items()])
        history_str = "\n".join([f"**{item['sender'].upper()}**: {item['content']}" for item in self.history])

        return f"""
        **Goal:** {self.task}

        **Available Tools:**
        {tools_description}
        - `task_complete`: Use this tool when the task is fully completed.

        **History:**
        {history_str}

        **Instruction:**
        Based on the goal and history, decide the next single action.
        Respond ONLY with a JSON object in the format:
        {{"tool": "tool_name", "args": {{"arg1": "value1", ...}}}}
        """

    def add_to_history(self, sender, content):
        self.history.append({"sender": sender, "content": content})
        self.socketio.emit('agent_message', {'chat_id': self.chat_id, 'message': content})

    def stop(self):
        self.stop_event.set()
