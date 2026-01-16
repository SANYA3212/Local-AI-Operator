# app/agent/executor.py
import json
import sys
from app.utils import ollama_stream_generate

class Executor:
    """
    The Executor class is responsible for executing a single step of a given plan.
    It operates on a think-act-observe loop, where it first thinks about the best tool
    to use for the current step, executes that tool, and then observes the result.
    This process is repeated until the step's objective is achieved or a maximum
    number of attempts is reached.
    """
    def __init__(self, model, tools, socketio_instance, chat_id):
        self.model = model
        self.tools = tools
        self.socketio = socketio_instance
        self.chat_id = chat_id
        self.history = []

    def execute_step(self, step: str, full_task: str):
        """
        Executes a single step of the plan.
        """
        self.log_and_emit("agent", f"**Executing Step:** {step}")

        for i in range(5):
            prompt = self._construct_execution_prompt(step, full_task)

            response_text = ""
            for part in ollama_stream_generate(self.model, prompt):
                response_text += part.get("response", "")
                if part.get("done"):
                    break

            thought, tool_name, tool_args = self._parse_response(response_text)

            self.log_and_emit("thought", thought)
            self.history.append({"role": "assistant", "content": response_text})

            if tool_name:
                self.log_and_emit("agent", f"**Action:** `{tool_name}` with args: `{json.dumps(tool_args)}`")
                if tool_name in self.tools:
                    observation = self.tools[tool_name].execute(**tool_args)
                else:
                    observation = json.dumps({"status": "error", "message": f"Tool '{tool_name}' not found."})

                self.log_and_emit("observation", f"**Observation:**\n```json\n{observation}\n```")
                self.history.append({"role": "user", "content": f"Observation: {observation}"})

                if "error" not in observation.lower() and "failed" not in observation.lower():
                    self.log_and_emit("agent", f"Step '{step}' appears to be complete.")
                    return observation
            else:
                self.log_and_emit("agent", "No tool was chosen. Moving to the next step or finishing.")
                return "No action taken."

        self.log_and_emit("agent", f"Failed to complete step '{step}' after multiple attempts.")
        return "Step failed after multiple attempts."

    def _construct_execution_prompt(self, step: str, full_task: str) -> str:
        """Constructs the prompt for the Ollama model to decide on an action."""
        tools_desc = "\n".join([f'- `{name}`: {tool.get_description()}' for name, tool in self.tools.items()])
        history_str = "\n".join([f"**{item['role'].upper()}**: {item['content']}" for item in self.history])

        prompt = (
            f"**Objective:** You are an execution agent. Your task is to perform the current step of a plan to achieve a larger goal. "
            f"You must choose the single best tool to make progress on the current step.\n\n"
            f"**Overall Goal:** \"{full_task}\"\n"
            f"**Current Step:** \"{step}\"\n\n"
            f"**Available Tools:**\n{tools_desc}\n\n"
            f"**Execution History (for this step):**\n{history_str}\n\n"
            f"**Instructions:**\n"
            f"1. First, think step-by-step about what you need to do to accomplish the **Current Step**. This is your thought process.\n"
            f"2. Based on your thought, choose exactly one tool from the **Available Tools** list.\n"
            f"3. Provide the tool name and the arguments in a JSON format.\n\n"
            f"**Output Format:** Your response MUST be a JSON object with three keys: 'thought', 'tool', and 'args'.\n"
            f"Example:\n"
            f"```json\n"
            f"{{\n"
            f'  "thought": "I need to write the text \\"Hello, World!\\" to a file named hello.py. The `write_file` tool is perfect for this. I will specify the path and the content.",\n'
            f'  "tool": "write_file",\n'
            f'  "args": {{\n'
            f'    "path": "hello.py",\n'
            f'    "content": "print(\\"Hello, World!\\")"\n'
            f"  }}\n"
            f"}}\n"
            f"```\n\n"
            f"Now, decide the next action for the **Current Step**.\n"
            f"**Response:**"
        )
        return prompt

    def _parse_response(self, response_text: str) -> (str, str, dict):
        """Parses the JSON response from the model to extract thought, tool, and args."""
        try:
            json_str = response_text[response_text.find('{'):response_text.rfind('}')+1]
            data = json.loads(json_str)
            thought = data.get("thought", "No thought provided.")
            tool_name = data.get("tool")
            tool_args = data.get("args", {})
            return thought, tool_name, tool_args
        except (json.JSONDecodeError, IndexError):
            return f"Failed to parse model response: {response_text}", None, {}

    def log_and_emit(self, sender, content):
        """Logs a message and emits it to the frontend via Socket.IO."""
        print(f"[{sender.upper()}] CHAT_ID({self.chat_id}): {content}", file=sys.stdout)
        sys.stdout.flush()

        self.socketio.emit('agent_response', {
            'chat_id': self.chat_id,
            'sender': sender,
            'message': content
        })
