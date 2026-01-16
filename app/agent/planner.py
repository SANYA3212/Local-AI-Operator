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
        return f"""**Цель:** Ты — ИИ-планировщик. Твоя задача — разбить сложный запрос пользователя на последовательность простых и понятных шагов.

**Запрос пользователя:** \"{task}\"

**Инструкции:**
1.  **Думай и отвечай на русском языке.**
2.  Разбей запрос на логические шаги.
3.  Опиши шаги общими словами (что сделать), а не конкретными действиями (как сделать). Например, вместо "Кликнуть кнопку в координатах (500, 300)", напиши "Нажать кнопку 'Сохранить'".
4.  Последним шагом всегда должна быть проверка, что задача выполнена.
5.  Твой ответ ДОЛЖЕН быть ТОЛЬКО в формате JSON-массива строк.

**Пример формата:**
```json
[
  "Открыть главное окно приложения.",
  "Перейти на страницу настроек.",
  "Изменить тему на темную.",
  "Убедиться, что тема успешно применена."
]
```

**Теперь сгенерируй план для запроса пользователя.**
"""

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
