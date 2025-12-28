document.addEventListener('DOMContentLoaded', () => {
    const socket = io();

    // --- DOM Elements ---
    const chatListEl = document.getElementById('chat-list');
    const modelSelector = document.getElementById('model-selector');
    const tpsCounter = document.getElementById('tps-counter');
    const chatWindow = document.getElementById('chat-window');
    const messageInput = document.getElementById('message-input');
    const sendBtn = document.getElementById('send-btn');
    const newChatBtn = document.getElementById('new-chat-btn');
    const clearChatBtn = document.getElementById('clear-chat-btn');
    const themeSwitcher = document.getElementById('theme-switcher');
    const actionButtonsContainer = document.getElementById('action-buttons-container');

    // --- State ---
    let currentChatId = null;
    let tokenCount = 0;
    let startTime = null;

    // =================================================================================
    // RENDER FUNCTIONS
    // =================================================================================
    function renderChatList(chats) {
        chatListEl.innerHTML = '';
        if (!chats || chats.length === 0) return;
        chats.forEach(chat => {
            const el = document.createElement('div');
            el.className = `chat-list-item p-3 rounded-xl cursor-pointer border ${currentChatId === chat.id ? 'border-primary/50 bg-gray-800/50' : 'border-gray-700/50 hover:border-primary/30'}`;
            el.dataset.chatId = chat.id;
            el.innerHTML = `<h3 class="font-medium truncate">Chat ${chat.id}</h3><p class="text-xs text-gray-400 truncate mt-1">${new Date(chat.created_at).toLocaleString()}</p>`;
            el.addEventListener('click', () => selectChat(chat.id));
            chatListEl.appendChild(el);
        });
    }

    function renderMessage(message) {
        const bubble = document.createElement('div');
        const isUser = message.sender === 'user';
        bubble.className = `message-bubble max-w-[85%] rounded-2xl p-4 shadow-lg ${isUser ? 'user-bubble ml-auto' : 'ai-bubble'}`;
        if (message.id) bubble.id = message.id;

        const content = message.content.includes('```') ? marked.parse(message.content) : `<p>${message.content.replace(/</g, "&lt;").replace(/>/g, "&gt;")}</p>`;

        bubble.innerHTML = `<div class="prose prose-invert max-w-none prose-sm">${content}</div>`;
        chatWindow.appendChild(bubble);
        chatWindow.scrollTop = chatWindow.scrollHeight;
        bubble.querySelectorAll('pre code').forEach(hljs.highlightElement);
        return bubble;
    }

    // =================================================================================
    // CORE LOGIC
    // =================================================================================
    async function loadModels() {
        const response = await fetch('/api/models');
        const models = await response.json();
        modelSelector.innerHTML = models.map(m => `<option>${m}</option>`).join('');
    }

    async function loadChats() {
        const response = await fetch('/api/chats');
        const chats = await response.json();
        renderChatList(chats);
        if (chats.length > 0 && !currentChatId) {
            selectChat(chats[0].id);
        } else if (chats.length === 0) {
            await newChat();
        }
    }

    async function selectChat(chatId) {
        currentChatId = chatId;
        chatWindow.innerHTML = '';
        const response = await fetch(`/api/chats/${chatId}/messages`);
        const messages = await response.json();
        messages.forEach(renderMessage);
        renderChatList(await (await fetch('/api/chats')).json());
    }

    async function newChat() {
        const response = await fetch('/api/chats', { method: 'POST' });
        const chat = await response.json();
        currentChatId = chat.id;
        await loadChats();
    }

    function sendMessage(content, image = null) {
        const message = content || messageInput.value.trim();
        if (!message || !currentChatId) return;

        renderMessage({ sender: 'user', content: image ? `![User Upload](${image}) \n ${message}`: message });

        socket.emit('user_message', {
            chat_id: currentChatId,
            message: message,
            model: modelSelector.value,
            image: image
        });
        messageInput.value = '';
    }

    // =================================================================================
    // EVENT LISTENERS
    // =================================================================================
    sendBtn.addEventListener('click', () => sendMessage());
    messageInput.addEventListener('keydown', (e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); } });
    newChatBtn.addEventListener('click', newChat);
    clearChatBtn.addEventListener('click', async () => {
        if (!currentChatId || !confirm("Delete chat?")) return;
        await fetch(`/api/chats/${currentChatId}`, { method: 'DELETE' });
        await newChat();
    });
    themeSwitcher.addEventListener('change', () => document.documentElement.classList.toggle('dark', themeSwitcher.checked));

    actionButtonsContainer.addEventListener('click', (e) => {
        const action = e.target.closest('.action-btn')?.dataset.action;
        if (!action) return;

        let task = '';
        if (action === 'write_file') task = `/task write file "${prompt('Path:')}" with content: "${prompt('Content:')}"`;
        if (action === 'shell_command') task = `/task run command: ${prompt('Command:')}`;
        if (action === 'take_screenshot') task = `/task screenshot to "${prompt('Filename:', 'screenshot.png')}"`;

        if (task.includes('null')) return; // User cancelled prompt
        sendMessage(task);
    });

    // --- Image Upload ---
    messageInput.addEventListener('paste', e => {
        const file = e.clipboardData.files[0];
        if (file && file.type.startsWith('image/')) {
            const reader = new FileReader();
            reader.onload = e => sendMessage(messageInput.value, e.target.result);
            reader.readAsDataURL(file);
        }
    });

    // =================================================================================
    // SOCKET.IO HANDLERS
    // =================================================================================
    socket.on('agent_token', (data) => {
        if (data.chat_id !== currentChatId) return;

        if (startTime === null) startTime = Date.now();
        tokenCount++;
        const tps = (tokenCount / ((Date.now() - startTime) / 1000)).toFixed(1);
        tpsCounter.textContent = tps;

        let bubble = document.getElementById(data.message_id);
        if (!bubble) {
            bubble = renderMessage({ sender: 'agent', content: '', id: data.message_id });
        }

        const proseDiv = bubble.querySelector('.prose');
        proseDiv.innerHTML += data.token;
    });

    socket.on('stream_end', (data) => {
        tokenCount = 0;
        startTime = null;
        const bubble = document.getElementById(data.message_id);
        if(bubble) {
            const proseDiv = bubble.querySelector('.prose');
            proseDiv.innerHTML = marked.parse(proseDiv.textContent);
            bubble.querySelectorAll('pre code').forEach(hljs.highlightElement);
        }
    });

    socket.on('agent_message', (data) => { // For non-streaming agent messages
        if (data.chat_id === currentChatId) {
            renderMessage({ sender: 'agent', content: data.message, id: data.message_id });
        }
    });

    // =================================================================================
    // INITIALIZATION
    // =================================================================================
    function init() {
        themeSwitcher.checked = document.documentElement.classList.contains('dark');
        loadModels();
        loadChats();
    }

    init();
});
