# app/agent/agent_core.py
import threading
import json
from app.utils import ollama_stream_generate # CORRECTED IMPORT
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
        }

        self.history = []

    def run(self):
        """The main loop of the agent."""
        self.add_to_history("agent", f"Starting task: {self.task}")

        for _ in range(15): # Increased step limit for more complex tasks
            if self.stop_event.is_set():
                self.add_to_history("agent", "Task stopped by user.")
                break

            plan = self.plan_next_step()
            if not plan or "error" in plan:
                self.add_to_history("agent", "Could not create a valid plan. Stopping.")
                break

            tool_name = plan.get("tool")
            tool_args = plan.get("args", {})

            if tool_name == "task_complete":
                self.add_to_history("agent", "Task marked as complete.")
                break

            self.add_to_history("agent", f"Executing tool: `{tool_name}` with args: `{tool_args}`")
            if tool_name in self.tools:
                tool = self.tools[tool_name]
                observation = tool.execute(**tool_args)
            else:
                observation = json.dumps({"status": "error", "message": f"Tool '{tool_name}' not found."})

            self.add_to_history("observation", f"Result:\n```json\n{observation}\n```")

        self.add_to_history("agent", "Task finished.")

    def plan_next_step(self):
        """Generates the next step by consuming the stream from the LLM."""
        prompt = self.construct_planning_prompt()

        # CORRECTLY HANDLE STREAM
        response_text = ""
        for part in ollama_stream_generate(self.model, prompt):
            response_text += part.get("response", "")
            if part.get("done"):
                break

        try:
            json_part = response_text[response_text.find('{'):response_text.rfind('}')+1]
            if not json_part:
                raise json.JSONDecodeError("No JSON found in response", response_text, 0)
            return json.loads(json_part)
        except json.JSONDecodeError:
            self.add_to_history("agent", f"Error: Failed to decode the plan from LLM response:\n```\n{response_text}\n```")
            return {"error": "Failed to decode plan"}

    def construct_planning_prompt(self):
        tools_description = "\n".join([f'- `{name}`: {tool.get_description()}' for name, tool in self.tools.items()])
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
        Respond ONLY with a valid JSON object in the format:
        {{"tool": "tool_name", "args": {{"arg1": "value1", ...}}}}
        Your response must contain nothing but the JSON object.
        """

    def add_to_history(self, sender, content):
        self.history.append({"sender": sender, "content": content})
        # Use a unique ID for agent messages to avoid conflicts with streaming chat
        message_id = f"agent-task-msg-{self.chat_id}-{len(self.history)}"
        self.socketio.emit('agent_message', {'chat_id': self.chat_id, 'message': content, 'message_id': message_id})

    def stop(self):
        self.stop_event.set()
