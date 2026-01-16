# app/agent/agent_core.py
import threading
import sys
from .master_thinker import MasterThinker
from .planner import Planner
from .executor import Executor
from .tools.file_system import WriteFileTool, ReadFileTool, ListFilesTool
from .tools.shell import ShellCommandTool
from .tools.gui_control import MouseClickTool, TypeTextTool, HotkeyTool
from .tools.windows_control import GetActiveWindowTool, MaximizeWindowTool
from .tools.vision import ScreenshotTool
from .tools.python_interpreter import PythonInterpreterTool

class AgentCore(threading.Thread):
    def __init__(self, task, model, chat_id, socketio_instance):
        super().__init__()
        self.task = task
        self.model = model
        self.chat_id = chat_id
        self.socketio = socketio_instance
        self.stop_event = threading.Event()
        self.plan_confirmed_event = threading.Event()

        from .tool_registry import TOOL_REGISTRY
        self.tools = TOOL_REGISTRY

    def confirm_plan(self):
        """Sets the event to confirm the plan and start execution."""
        self.plan_confirmed_event.set()

    def run(self):
        self.log_and_emit("agent", f"Получена задача: \"{self.task}\". Начинаю анализ...")
        if self.stop_event.is_set(): return

        # Step 1: Master Thinker analyzes the task
        master_thinker = MasterThinker(self.model)
        initial_decision = master_thinker.analyze_task(self.task)
        decision = initial_decision.get("decision")

        if self.stop_event.is_set(): return

        if decision == "dialogue":
            self.log_and_emit("agent", initial_decision.get("response", "Я не уверен, как на это ответить."))
            self.log_and_emit("agent", "Задача выполнена (это был диалог).")
            return

        if decision == "planning":
            self.log_and_emit("thought", initial_decision.get("thought", "Требуется планирование."))
            self.execute_plan()
        else:
            self.log_and_emit("agent", "Не удалось принять решение. Задача прервана.")

        sys.stdout.flush()

    def execute_plan(self):
        # Step 2: Planner creates a plan
        planner = Planner(self.model)
        plan = planner.generate_plan(self.task, list(self.tools.keys()))

        if not (plan and not plan[0].startswith("Error:")):
            error_message = plan[0] if plan else "Не удалось сгенерировать план."
            self.log_and_emit("agent", f"Ошибка во время планирования: {error_message}")
            self.log_and_emit("agent", "Задача прервана из-за сбоя планирования.")
            return

        plan_str = "\n".join([f"{i+1}. {step}" for i, step in enumerate(plan)])
        self.log_and_emit("plan", f"**Сгенерированный план:**\n{plan_str}")

        # --- Wait for user confirmation ---
        self.log_and_emit("agent", "Ожидание подтверждения плана...")
        # Wait for the plan to be confirmed, with a timeout of 5 minutes.
        confirmed = self.plan_confirmed_event.wait(timeout=300)

        if self.stop_event.is_set():
            self.log_and_emit("agent", "Выполнение остановлено во время ожидания подтверждения.")
            return

        if not confirmed:
            self.log_and_emit("agent", "План не был подтвержден в течение 5 минут. Задача прервана.")
            return

        self.log_and_emit("agent", "План подтвержден. Начинаю выполнение...")
        # Step 3: Executor executes the plan
        executor = Executor(self.model, self.tools, self.socketio, self.chat_id)
        for i, step in enumerate(plan):
            if self.stop_event.is_set():
                self.log_and_emit("agent", "Выполнение задачи остановлено пользователем.")
                break

            self.log_and_emit("agent", f"--- Выполнение шага {i+1}/{len(plan)} ---")
            executor.execute_step(step, self.task)
            executor.history = []

        if not self.stop_event.is_set():
            self.log_and_emit("agent", "Все шаги выполнены. Задача завершена.")

    def log_and_emit(self, sender, content):
        print(f"[{sender.upper()}] CHAT_ID({self.chat_id}): {content}", file=sys.stdout)
        self.socketio.emit('agent_response', {
            'chat_id': self.chat_id,
            'sender': sender,
            'message': content
        })

    def stop(self):
        self.stop_event.set()
