document.addEventListener('DOMContentLoaded', () => {
    const socket = io();

    const chatWindow = document.getElementById('chat-window');
    const messageInput = document.getElementById('message-input');
    const sendBtn = document.getElementById('send-btn');
    const newChatBtn = document.getElementById('new-chat-btn');
    const chatList = document.getElementById('chat-list');
    const modelSelector = document.getElementById('model-selector');
    const actionButtonsContainer = document.getElementById('action-buttons-container');

    let currentChatId = null;

    function addMessageToChat(message, clear = false) {
        if (clear) chatWindow.innerHTML = '';
        const messageElement = document.createElement('div');
        messageElement.classList.add('message', message.sender === 'user' ? 'user-message' : 'agent-message');
        messageElement.innerHTML = marked.parse(message.content);
        messageElement.querySelectorAll('pre code').forEach(hljs.highlightElement);
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
        if (chats.length > 0 && !currentChatId) {
            selectChat(chats[0].id);
        }
    }

    async function selectChat(chatId) {
        currentChatId = chatId;
        chatWindow.innerHTML = '';
        document.querySelectorAll('.chat-item').forEach(item => item.classList.remove('selected'));
        document.querySelector(`.chat-item[data-chat-id='${chatId}']`).classList.add('selected');
        const response = await fetch(`/api/chats/${chatId}/messages`);
        const messages = await response.json();
        messages.forEach(msg => addMessageToChat(msg));
    }

    async function newChat() {
        const response = await fetch('/api/chats', { method: 'POST' });
        const chat = await response.json();
        await loadChats();
        selectChat(chat.id);
    }

    function sendMessage(messageContent) {
        const message = messageContent || messageInput.value.trim();
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

    actionButtonsContainer.addEventListener('click', (e) => {
        if (e.target.classList.contains('action-btn')) {
            const action = e.target.dataset.action;
            handleAction(action);
        }
    });

    function handleAction(action) {
        let task = '';
        switch (action) {
            case 'write_file':
                const path = prompt("Enter the file path:");
                if (!path) return;
                const content = prompt("Enter the file content:");
                if (content === null) return;
                task = `/task create a file at ${path} with the content: "${content}"`;
                break;
            case 'shell_command':
                const command = prompt("Enter the shell command to run:");
                if (!command) return;
                task = `/task run the shell command: ${command}`;
                break;
            case 'take_screenshot':
                const filename = prompt("Enter the filename for the screenshot (e.g., screenshot.png):", "screenshot.png");
                if (!filename) return;
                task = `/task take a screenshot and save it as ${filename}`;
                break;
        }
        if (task) {
            sendMessage(task);
        }
    }

    sendBtn.addEventListener('click', () => sendMessage());
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
            if (!response.ok) throw new Error('Failed to fetch models');
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
