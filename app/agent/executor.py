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
        tools_desc = "\n".join([f'- `{name}`: {tool.description}' for name, tool in self.tools.items()])
        history_str = "\n".join([f"**{item['role'].upper()}**: {item['content']}" for item in self.history])

        return f"""**Цель:** Ты — продвинутый ИИ-исполнитель, способный управлять графическим интерфейсом компьютера.

**Общая задача:** \"{full_task}\"
**Текущий шаг:** \"{step}\"

**Доступные инструменты:**
{tools_desc}

**История выполнения (для всей задачи):**
{history_str}

**Твой алгоритм действий (Визуальный Цикл):**
1.  **ПОСМОТРИ:** Если ты не знаешь, что на экране, или тебе нужно найти кнопку/элемент, **первым делом** используй `analyze_screen_ocr`. Этот инструмент даст тебе текстовое представление экрана с координатами.
2.  **РЕШИ:** Проанализируй результат `analyze_screen_ocr`. Найди текст нужного элемента (например, кнопки 'Сохранить') и его координаты. Рассчитай центр этого элемента, чтобы точно по нему кликнуть.
3.  **ДЕЙСТВУЙ:** Используй `mouse_click`, `type_text` или другой инструмент для взаимодействия с найденным элементом.
4.  **ПОДОЖДИ:** Если интерфейс может не успеть обновиться, используй `wait(seconds=...)`, чтобы сделать паузу.
5.  **ПРОВЕРЬ:** Снова используй `analyze_screen_ocr`, чтобы убедиться, что твое действие привело к ожидаемому результату (например, появилось новое окно).

**Важные инструкции:**
-   **Думай и отвечай на русском языке.**
-   **Не гадай.** Если не знаешь, что на экране, используй `analyze_screen_ocr`.
-   **Действуй по одному шагу за раз.** Выбери только **один** инструмент.
-   **Используй историю.** Если ты уже определил ОС, не делай это снова.
-   Твой ответ ДОЛЖЕН быть ТОЛЬКО в формате JSON с ключами `thought`, `tool` и `args`.

**Пример выполнения шага "Нажать кнопку 'Далее'":**
```json
{{
  "thought": "Я не знаю, где находится кнопка 'Далее'. Сначала мне нужно проанализировать экран, чтобы найти ее координаты.",
  "tool": "analyze_screen_ocr",
  "args": {{}}
}}
```
*(После этого ты получишь Observation с текстом и координатами)*

**Следующий шаг после анализа:**
```json
{{
  "thought": "Анализ экрана показал, что кнопка с текстом 'Далее' находится в области [500, 300, 580, 340]. Я рассчитаю центр этой области (540, 320) и нажму туда.",
  "tool": "mouse_click",
  "args": {{
    "x": 540,
    "y": 320
  }}
}}
```

**Теперь прими решение для выполнения текущего шага.**
"""

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
