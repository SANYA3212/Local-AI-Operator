from run import socketio
from app.database.database import SessionLocal
from app.database.models import Message
from app.utils import ollama_generate
from app.agent.agent_core import AgentCore

# A simple in-memory store for active agent threads
active_agents = {}

@socketio.on('user_message')
def handle_user_message(data):
    chat_id = data.get('chat_id')
    message_content = data.get('message')
    model = data.get('model', 'llama3')

    if not chat_id or not message_content:
        return

    # --- Save user message to DB ---
    db = SessionLocal()
    user_message = Message(chat_id=chat_id, sender='user', content=message_content)
    db.add(user_message)
    db.commit()
    db.close()

    # --- Check if it's a task or a dialogue ---
    if message_content.strip().startswith("/task"):
        task = message_content.replace("/task", "").strip()

        # Stop any existing agent for this chat
        if chat_id in active_agents:
            active_agents[chat_id].stop()

        # Start a new agent thread
        agent_thread = AgentCore(task, model, chat_id, socketio)
        active_agents[chat_id] = agent_thread
        agent_thread.start()

    else: # It's a dialogue
        # --- Standard LLM response ---
        ollama_response = ollama_generate(model=model, prompt=message_content)
        agent_response = ollama_response.get('response', 'Error generating response.')

        db = SessionLocal()
        agent_message = Message(chat_id=chat_id, sender='agent', content=agent_response)
        db.add(agent_message)
        db.commit()
        db.close()

        socketio.emit('agent_message', {'chat_id': chat_id, 'message': agent_response})
