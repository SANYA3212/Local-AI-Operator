from run import socketio
from app.database.database import SessionLocal
from app.database.models import Message
from app.utils import ollama_stream_generate
from app.agent.agent_core import AgentCore
import sys

active_agents = {}

@socketio.on('connect')
def handle_connect():
    """Diagnostic handler to confirm connection."""
    print("<<<<< CLIENT CONNECTED >>>>>", file=sys.stdout)
    sys.stdout.flush()

@socketio.on('disconnect')
def handle_disconnect():
    """Diagnostic handler for disconnections."""
    print(">>>>> CLIENT DISCONNECTED <<<<<", file=sys.stdout)
    sys.stdout.flush()

@socketio.on('user_message')
def handle_user_message(data):
    """Handles incoming user messages with detailed logging."""
    print(f"\n--- SERVER RECEIVED user_message ---\nDATA: {data}\n------------------------------------", file=sys.stdout)
    sys.stdout.flush()

    chat_id = data.get('chat_id')
    message_content = data.get('message')
    model = data.get('model')
    image_data = data.get('image')

    if not all([chat_id, message_content, model]):
        print("!!! Missing data in user_message, aborting.", file=sys.stdout)
        sys.stdout.flush()
        return

    # ... (rest of the logic)
    db = SessionLocal()
    user_message = Message(chat_id=chat_id, sender='user', content=message_content)
    db.add(user_message)
    db.commit()
    db.close()

    if message_content.strip().startswith("/task"):
        # ... (agent logic)
    else:
        # ... (streaming logic)
        full_response = ""
        message_id = f"agent-msg-{socketio.sid}-{Message().id}"

        generator = ollama_stream_generate(model=model, prompt=message_content, image_data=image_data)

        for part in generator:
            token = part.get("response", "")
            if token:
                full_response += token
                socketio.emit('agent_token', {'chat_id': chat_id, 'token': token, 'message_id': message_id})

            if part.get("done"):
                db = SessionLocal()
                agent_message = Message(chat_id=chat_id, sender='agent', content=full_response)
                db.add(agent_message)
                db.commit()
                db.close()
                socketio.emit('stream_end', {'chat_id': chat_id, 'message_id': message_id})
                break
