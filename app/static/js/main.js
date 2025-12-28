document.addEventListener('DOMContentLoaded', () => {
    const socket = io();

    const chatWindow = document.getElementById('chat-window');
    const messageInput = document.getElementById('message-input');
    const sendBtn = document.getElementById('send-btn');
    const newChatBtn = document.getElementById('new-chat-btn');
    const chatList = document.getElementById('chat-list');
    const modelSelector = document.getElementById('model-selector');

    let currentChatId = null;

    function addMessageToChat(message, clear = false) {
        if (clear) {
            chatWindow.innerHTML = '';
        }
        const messageElement = document.createElement('div');
        messageElement.classList.add('message', message.sender === 'user' ? 'user-message' : 'agent-message');

        messageElement.innerHTML = marked.parse(message.content);

        messageElement.querySelectorAll('pre code').forEach((block) => {
            hljs.highlightElement(block);
        });

        chatWindow.appendChild(messageElement);
        chatWindow.scrollTop = chatWindow.scrollHeight;
    }

    async function loadChats() {
        const response = await fetch('/api/chats');
        const chats = await response.json();
        chatList.innerHTML = '';
        chats.forEach(chat => {
            const chatElement = document.createElement('div');
            chatElement.classList.add('chat-item');
            chatElement.dataset.chatId = chat.id;
            chatElement.textContent = `Chat ${chat.id} - ${new Date(chat.created_at).toLocaleString()}`;
            chatElement.addEventListener('click', () => selectChat(chat.id));
            chatList.appendChild(chatElement);
        });
        if (chats.length > 0) {
            selectChat(chats[0].id);
        }
    }

    async function selectChat(chatId) {
        currentChatId = chatId;
        chatWindow.innerHTML = '';
        const response = await fetch(`/api/chats/${chatId}/messages`);
        const messages = await response.json();
        messages.forEach(msg => addMessageToChat(msg));
    }

    async function newChat() {
        const response = await fetch('/api/chats', { method: 'POST' });
        const chat = await response.json();
        loadChats();
        selectChat(chat.id);
    }

    function sendMessage() {
        const message = messageInput.value.trim();
        const selectedModel = modelSelector.value;
        if (message && currentChatId && selectedModel) {
            const messageData = { sender: 'user', content: message };
            addMessageToChat(messageData);
            socket.emit('user_message', {
                chat_id: currentChatId,
                message: message,
                model: selectedModel
            });
            messageInput.value = '';
        }
    }

    sendBtn.addEventListener('click', sendMessage);
    messageInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    newChatBtn.addEventListener('click', newChat);

    socket.on('agent_message', (data) => {
        if (data.chat_id === currentChatId) {
            addMessageToChat({ sender: 'agent', content: data.message });
        }
    });

    async function loadModels() {
        try {
            const response = await fetch('/api/models');
            if (!response.ok) {
                throw new Error('Failed to fetch models');
            }
            const models = await response.json();
            modelSelector.innerHTML = '';
            models.forEach(model => {
                const option = document.createElement('option');
                option.value = model;
                option.textContent = model;
                modelSelector.appendChild(option);
            });
        } catch (error) {
            console.error(error);
            modelSelector.innerHTML = '<option value="">Error loading models</option>';
        }
    }

    function init() {
        loadChats();
        loadModels();
    }

    init();
});
