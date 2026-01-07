from app.extensions import socketio
from app.database.database import SessionLocal
from app.database.models import Message
from app.utils import ollama_stream_generate
from app.agent.agent_core import AgentCore
import sys
import os
import json
from datetime import datetime
from flask import request

HISTORY_DIR = "app.chat_history"
os.makedirs(HISTORY_DIR, exist_ok=True)

def log_to_history(chat_id, sender, message):
    log_path = os.path.join(HISTORY_DIR, f"chat_{chat_id}.txt")
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {sender.upper()}:\n{message}\n\n")

active_agents = {}

DECISION_PROMPT = """
Analyze the user's request and decide if it requires using tools to interact with the system (e.g., write files, run commands, control UI) or if it's a simple question that can be answered directly.

Respond ONLY with a JSON object with two keys:
1. "decision": either "task" or "dialogue".
2. "explanation": a brief, one-sentence explanation of your decision.

User request: "{user_prompt}"
"""

@socketio.on('connect')
def handle_connect():
    print(f"<<<<< CLIENT CONNECTED (SID: {request.sid}) >>>>>", file=sys.stdout)

@socketio.on('user_message')
def handle_user_message(data):
    chat_id = data.get('chat_id')
    message_content = data.get('message', '')
    model = data.get('model')
    image_data = data.get('image')

    if not chat_id or not model: return

    log_to_history(chat_id, "user", message_content)
    db = SessionLocal()
    db.add(Message(chat_id=chat_id, sender='user', content=message_content))
    db.commit()
    db.close()

    # --- AUTOMATIC TASK DETECTION ---
    prompt = DECISION_PROMPT.format(user_prompt=message_content)
    full_decision_response = ""
    for part in ollama_stream_generate(model, prompt):
        full_decision_response += part.get("response", "")
        if part.get("done"): break

    try:
        decision_json = json.loads(full_decision_response)
        decision = decision_json.get("decision")
    except (json.JSONDecodeError, AttributeError):
        decision = "dialogue" # Default to dialogue on error

    if decision == "task":
        print(f"--- DECISION: TASK ---", file=sys.stdout)
        if chat_id in active_agents: active_agents[chat_id].stop()
        agent_thread = AgentCore(message_content, model, chat_id, socketio)
        active_agents[chat_id] = agent_thread
        agent_thread.start()
    else:
        print(f"--- DECISION: DIALOGUE ---", file=sys.stdout)
        full_response = ""
        message_id = f"agent-msg-{request.sid}"

        generator = ollama_stream_generate(model=model, prompt=message_content, image_data=image_data)

        for part in generator:
            token = part.get("response", "")
            if token:
                full_response += token
                socketio.emit('agent_token', {'chat_id': chat_id, 'token': token, 'message_id': message_id})

            if part.get("done"):
                log_to_history(chat_id, "agent", full_response)
                db = SessionLocal()
                db.add(Message(chat_id=chat_id, sender='agent', content=full_response))
                db.commit()
                db.close()
                socketio.emit('stream_end', {'chat_id': chat_id, 'message_id': message_id})
                break
    sys.stdout.flush()
