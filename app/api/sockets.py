from run import socketio
from app.database.database import SessionLocal
from app.database.models import Message
from app.utils import ollama_stream_generate
from app.agent.agent_core import AgentCore
import sys
import os
from datetime import datetime

HISTORY_DIR = "app/chat_history"
os.makedirs(HISTORY_DIR, exist_ok=True)

def log_to_history(chat_id, sender, message):
    log_path = os.path.join(HISTORY_DIR, f"chat_{chat_id}.txt")
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {sender.upper()}:\n{message}\n\n")

active_agents = {}

@socketio.on('connect')
def handle_connect():
    print("<<<<< CLIENT CONNECTED >>>>>", file=sys.stdout)

@socketio.on('user_message')
def handle_user_message(data):
    chat_id = data.get('chat_id')
    message_content = data.get('message', '')
    model = data.get('model')
    image_data = data.get('image')

    # Simplified, robust check
    if not chat_id or not model:
        print(f"!!! Aborting: Missing chat_id or model. Data: {data}", file=sys.stdout)
        return

    log_to_history(chat_id, "user", message_content)

    db = SessionLocal()
    db.add(Message(chat_id=chat_id, sender='user', content=message_content))
    db.commit()
    db.close()

    # --- Main Logic Branch ---
    if message_content.strip().startswith("/task"):
        print(f"--- DETECTED TASK ---", file=sys.stdout)
        task = message_content.replace("/task", "").strip()
        if chat_id in active_agents:
            active_agents[chat_id].stop()
        agent_thread = AgentCore(task, model, chat_id, socketio)
        active_agents[chat_id] = agent_thread
        agent_thread.start()
    else:
        print(f"--- STARTING DIALOGUE STREAM ---", file=sys.stdout)
        full_response = ""
        message_id = f"agent-msg-{socketio.sid}-{Message().id}"

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
                print(f"--- STREAM FINISHED ---", file=sys.stdout)
                break
    sys.stdout.flush()
