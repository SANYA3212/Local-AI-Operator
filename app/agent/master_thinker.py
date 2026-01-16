# app/agent/master_thinker.py
import json
from app.utils import ollama_stream_generate

class MasterThinker:
    def __init__(self, model):
        self.model = model

    def analyze_task(self, task: str) -> dict:
        prompt = self._construct_prompt(task)

        response_text = ""
        for part in ollama_stream_generate(self.model, prompt):
            response_text += part.get("response", "")
            if part.get("done"):
                break

        return self._parse_response(response_text)

    def _construct_prompt(self, task: str) -> str:
        return f"""**Задача:** Проанализируй запрос пользователя и прими решение.

**Запрос пользователя:** \"{task}\"

**Инструкции:**
1.  **Твоя главная задача — думать на русском языке.**
2.  Определи, является ли запрос простой беседой (например, "привет", "как дела?") или сложной задачей, требующей использования инструментов (например, "создай файл", "открой программу").
3.  Твой ответ ДОЛЖЕН быть ТОЛЬКО в формате JSON.

**Формат JSON:**
-   Если это **простая беседа**, ответь так:
    ```json
    {{
      "decision": "dialogue",
      "response": "Твой прямой ответ на вопрос пользователя"
    }}
    ```
-   Если это **сложная задача**, ответь так:
    ```json
    {{
      "decision": "planning",
      "thought": "Краткое обдумывание, почему для этого запроса нужен план действий"
    }}
    ```

**Примеры:**

1.  **Запрос:** "привет"
    **Ответ:**
    ```json
    {{
      "decision": "dialogue",
      "response": "Привет! Чем могу помочь?"
    }}
    ```

2.  **Запрос:** "создай текстовый файл с именем 'привет'"
    **Ответ:**
    ```json
    {{
      "decision": "planning",
      "thought": "Для создания файла требуется использование инструментов файловой системы. Необходимо составить план."
    }}
    ```

**Теперь проанализируй запрос пользователя и дай ответ в формате JSON.**
"""

    def _parse_response(self, response_text: str) -> dict:
        try:
            json_str = response_text[response_text.find('{'):response_text.rfind('}')+1]
            return json.loads(json_str)
        except (json.JSONDecodeError, IndexError):
            return {
                "decision": "dialogue",
                "response": "Извините, я не смог обработать ваш запрос."
            }
