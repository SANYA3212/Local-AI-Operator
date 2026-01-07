# app/agent/agent_core.py
import threading
import json
import sys
from app.utils import ollama_stream_generate
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
            "write_file": WriteFileTool(), "read_file": ReadFileTool(), "list_files": ListFilesTool(),
            "shell_command": ShellCommandTool(), "mouse_click": MouseClickTool(), "type_text": TypeTextTool(),
            "hotkey": HotkeyTool(), "get_active_window": GetActiveWindowTool(), "maximize_window": MaximizeWindowTool(),
            "take_screenshot": ScreenshotTool(),
        }
        self.history = []

    def run(self):
        self.log_and_emit("agent", f"Task started: {self.task}")

        for i in range(15): # Step limit
            if self.stop_event.is_set():
                self.log_and_emit("agent", "Task stopped by user.")
                break

            self.log_and_emit("agent", f"Step {i+1}: Planning next action...")
            plan = self.plan_next_step()

            if not plan or "error" in plan:
                self.log_and_emit("agent", "Could not create a valid plan. Stopping.")
                break

            tool_name = plan.get("tool")
            tool_args = plan.get("args", {})

            if tool_name == "task_complete":
                self.log_and_emit("agent", "Task marked as complete by LLM.")
                break

            self.log_and_emit("agent", f"Executing tool: `{tool_name}` with args: `{json.dumps(tool_args)}`")

            if tool_name in self.tools:
                observation = self.tools[tool_name].execute(**tool_args)
            else:
                observation = json.dumps({"status": "error", "message": f"Tool '{tool_name}' not found."})

            self.log_and_emit("observation", f"Result:\n```json\n{observation}\n```")

        self.log_and_emit("agent", "Task finished.")
        sys.stdout.flush()

    def plan_next_step(self):
        prompt = self.construct_planning_prompt()
        response_text = ""
        for part in ollama_stream_generate(self.model, prompt):
            response_text += part.get("response", "")
            if part.get("done"):
                break

        try:
            json_part = response_text[response_text.find('{'):response_text.rfind('}')+1]
            return json.loads(json_part)
        except json.JSONDecodeError:
            self.log_and_emit("agent", f"Error: Failed to decode plan from LLM:\n```\n{response_text}\n```")
            return {"error": "Failed to decode plan"}

    def construct_planning_prompt(self):
        tools_desc = "\n".join([f'- `{name}`: {tool.get_description()}' for name, tool in self.tools.items()])
        history_str = "\n".join([f"**{item['sender'].upper()}**: {item['content']}" for item in self.history])
        return f"**Goal:** {self.task}\n\n**Tools:**\n{tools_desc}\n- `task_complete`\n\n**History:**\n{history_str}\n\n**Instruction:** Decide the next action. Respond ONLY with a valid JSON object."

    def log_and_emit(self, sender, content):
        self.history.append({"sender": sender, "content": content})
        print(f"[{sender.upper()}] CHAT_ID({self.chat_id}): {content}", file=sys.stdout)
        self.socketio.emit('agent_message', {'chat_id': self.chat_id, 'message': content})

    def stop(self):
        self.stop_event.set()
