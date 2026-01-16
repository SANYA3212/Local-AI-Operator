# app/agent/planner.py
import json
from app.utils import ollama_stream_generate

class Planner:
    """
    The Planner class is responsible for breaking down a high-level task into a series of smaller,
    executable steps. It interacts with the Ollama model to generate these plans based on the
    user's request and the available tools.
    """
    def __init__(self, model):
        self.model = model

    def generate_plan(self, task: str, tools: list) -> list:
        """
        Generates a step-by-step plan for a given task.
        """
        prompt = self._construct_planning_prompt(task, tools)

        response_text = ""
        for part in ollama_stream_generate(self.model, prompt):
            response_text += part.get("response", "")
            if part.get("done"):
                break

        return self._parse_plan(response_text)

    def _construct_planning_prompt(self, task: str, tools: list) -> str:
        """Constructs the prompt for the Ollama model to generate a plan."""
        tools_desc = "\n".join([f'- {tool}' for tool in tools])

        prompt = (
            f"**Objective:** You are a meticulous AI planner. Your job is to break down a complex user request into a sequence of simple, clear, and actionable steps. "
            f"Each step should be a single, straightforward instruction for an execution agent.\n\n"
            f"**User Request:** \"{task}\"\n\n"
            f"**Available Tools:** The execution agent has access to tools for file system operations, shell commands, GUI control, and web browsing. You don't need to specify the tools, just the actions.\n\n"
            f"**Instructions:**\n"
            f"1. Think step-by-step to deconstruct the request.\n"
            f"2. List the steps in a logical sequence.\n"
            f"3. The steps should be high-level and describe 'what to do', not 'how to do it'. For example, instead of 'Click the button at (500, 300)', say 'Click the Save button'.\n"
            f"4. The final step should always be to verify the task is complete and report back.\n\n"
            f"**Output Format:** Please provide the plan as a JSON array of strings. For example:\n"
            f"```json\n"
            f"[\n"
            f'  "Open the main application window.",\n'
            f'  "Navigate to the settings page.",\n'
            f'  "Change the theme to dark mode.",\n'
            f'  "Verify that the theme has been applied successfully."\n'
            f"]\n"
            f"```\n\n"
            f"Now, generate the plan for the user's request.\n"
            f"**Response:**"
        )
        return prompt

    def _parse_plan(self, response_text: str) -> list:
        """Parses the JSON plan from the model's response."""
        try:
            json_str = response_text[response_text.find('['):response_text.rfind(']')+1]
            plan = json.loads(json_str)
            if isinstance(plan, list) and all(isinstance(step, str) for step in plan):
                return plan
            return ["Error: The generated plan is not a list of strings."]
        except (json.JSONDecodeError, IndexError):
            return [f"Error: Failed to parse the plan from the model's response. Response: {response_text}"]
