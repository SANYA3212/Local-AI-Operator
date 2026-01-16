from app.extensions import socketio
from app.database.database import SessionLocal
from app.database.models import Message
from app.agent.agent_core import AgentCore
from app.utils import ollama_stream_generate # Make sure this import is present
import sys
from flask import request

# In-memory storage for active agent threads
active_agents = {}

@socketio.on('connect')
def handle_connect():
    """Handles a new client connection."""
    print(f"<<<<< CLIENT CONNECTED (SID: {request.sid}) >>>>>", file=sys.stdout)

@socketio.on('disconnect')
def handle_disconnect():
    print(f">>>>> CLIENT DISCONNECTED (SID: {request.sid}) <<<<<", file=sys.stdout)

@socketio.on('start_task')
def handle_start_task(data):
    """Starts a new agent task."""
    chat_id = data.get('chat_id')
    task = data.get('task')
    model = data.get('model')

    if not all([chat_id, task, model]):
        print(f"ERROR: Missing data for start_task: {data}", file=sys.stdout)
        return

    print(f"--- TASK RECEIVED (CHAT_ID: {chat_id}) ---", file=sys.stdout)

    db = SessionLocal()
    db.add(Message(chat_id=chat_id, sender='user', content=f"/task {task}"))
    db.commit()
    db.close()

    if chat_id in active_agents:
        print(f"--- Stopping existing agent for chat {chat_id} ---", file=sys.stdout)
        active_agents[chat_id].stop()

    agent_thread = AgentCore(task, model, chat_id, socketio)
    active_agents[chat_id] = agent_thread
    agent_thread.start()

    sys.stdout.flush()

@socketio.on('stop_agent')
def handle_stop_agent(data):
    """Stops an active agent task for a given chat."""
    chat_id = data.get('chat_id')
    if chat_id in active_agents:
        print(f"--- STOP SIGNAL RECEIVED FOR CHAT {chat_id} ---", file=sys.stdout)
        active_agents[chat_id].stop()
        socketio.emit('agent_response', {
            'chat_id': chat_id,
            'sender': 'agent',
            'message': 'Agent execution stopped by user.'
        })
        del active_agents[chat_id]
    sys.stdout.flush()

@socketio.on('user_message')
def handle_user_message(data):
    """Handles a regular user message by streaming a response from the LLM."""
    chat_id = data.get('chat_id')
    message_content = data.get('message', '')
    model = data.get('model')

    if not all([chat_id, message_content, model]):
        return

    db = SessionLocal()
    db.add(Message(chat_id=chat_id, sender='user', content=message_content))
    db.commit()
    db.close()

    print(f"--- DIALOGUE RECEIVED (CHAT_ID: {chat_id}) ---", file=sys.stdout)

    full_response = ""
    message_id = f"agent-msg-{request.sid}-{hash(message_content)}"

    try:
        generator = ollama_stream_generate(model=model, prompt=message_content)
        for part in generator:
            token = part.get("response", "")
            if token:
                full_response += token
                socketio.emit('agent_response', {
                    'chat_id': chat_id,
                    'sender': 'token',
                    'message': token,
                    'message_id': message_id
                })

            if part.get("done"):
                break
    except Exception as e:
        print(f"Error during dialogue generation: {e}", file=sys.stdout)
        full_response = f"Sorry, an error occurred: {e}"
        socketio.emit('agent_response', {
            'chat_id': chat_id,
            'sender': 'agent',
            'message': full_response,
        })
    finally:
        db = SessionLocal()
        db.add(Message(chat_id=chat_id, sender='agent', content=full_response))
        db.commit()
        db.close()
        socketio.emit('stream_end', {'chat_id': chat_id, 'message_id': message_id})
        sys.stdout.flush()
