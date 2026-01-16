from flask import Blueprint, jsonify
from app.database.database import SessionLocal
from app.database.models import Chat, Message
import requests
from app.config import OLLAMA_BASE_URL

api = Blueprint('api', __name__)

@api.route('/chats', methods=['GET'])
def get_chats():
    db = SessionLocal()
    chats = db.query(Chat).order_by(Chat.created_at.desc()).all()
    db.close()
    return jsonify([{'id': chat.id, 'created_at': chat.created_at.isoformat()} for chat in chats])

@api.route('/chats', methods=['POST'])
def create_chat():
    db = SessionLocal()
    new_chat = Chat()
    db.add(new_chat)
    db.commit()
    db.refresh(new_chat)
    db.close()
    return jsonify({'id': new_chat.id, 'created_at': new_chat.created_at.isoformat()})

@api.route('/chats/<int:chat_id>/messages', methods=['GET'])
def get_messages(chat_id):
    db = SessionLocal()
    messages = db.query(Message).filter(Message.chat_id == chat_id).order_by(Message.created_at.asc()).all()
    db.close()
    return jsonify([{'sender': msg.sender, 'content': msg.content} for msg in messages])

@api.route('/chats/<int:chat_id>', methods=['DELETE'])
def delete_chat(chat_id):
    db = SessionLocal()
    chat_to_delete = db.query(Chat).filter(Chat.id == chat_id).first()
    if chat_to_delete:
        db.delete(chat_to_delete) # This will also delete associated messages due to cascading
        db.commit()
        status = 'success'
    else:
        status = 'not found'
    db.close()
    return jsonify({'status': status})

@api.route('/models', methods=['GET'])
def get_models():
    try:
        # Set a timeout to prevent long waits if Ollama is unresponsive
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        response.raise_for_status()
        models = [model['name'] for model in response.json().get('models', [])]
        return jsonify(models)
    except requests.exceptions.RequestException:
        # If Ollama is not available, return an empty list.
        # The frontend will handle this gracefully.
        return jsonify([])
