from run import socketio
from app.database.database import SessionLocal
from app.database.models import Message
from app.utils import ollama_stream_generate
from app.agent.agent_core import AgentCore

active_agents = {}

@socketio.on('user_message')
def handle_user_message(data):
    chat_id = data.get('chat_id')
    message_content = data.get('message')
    model = data.get('model')
    image_data = data.get('image') # Receive image data

    if not chat_id or not message_content or not model:
        return

    # If an image is sent, the content is markdown. We save it as is.
    db = SessionLocal()
    user_message = Message(chat_id=chat_id, sender='user', content=message_content)
    db.add(user_message)
    db.commit()
    db.close()

    if message_content.strip().startswith("/task"):
        task = message_content.replace("/task", "").strip()
        if chat_id in active_agents:
            active_agents[chat_id].stop()
        agent_thread = AgentCore(task, model, chat_id, socketio)
        active_agents[chat_id] = agent_thread
        agent_thread.start()
    else:
        full_response = ""
        message_id = f"agent-msg-{socketio.sid}-{Message().id}"

        # Pass image_data to the generator
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
