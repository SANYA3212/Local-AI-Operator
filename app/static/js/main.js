document.addEventListener('DOMContentLoaded', () => {
    const socket = io("http://127.0.0.1:8000", { transports: ['websocket'] });

    // --- DOM Elements ---
    const chatListEl = document.getElementById('chat-list');
    const modelSelector = document.getElementById('model-selector');
    const tpsCounter = document.getElementById('tps-counter');
    const chatWindow = document.getElementById('chat-window');
    const messageInput = document.getElementById('message-input');
    const sendBtn = document.getElementById('send-btn');
    const newChatBtn = document.getElementById('new-chat-btn');
    const clearChatBtn = document.getElementById('clear-chat-btn');
    const actionButtonsContainer = document.getElementById('action-buttons-container');

    // --- State ---
    let currentChatId = null;
    let tokenCount = 0;
    let startTime = null;

    // =================================================================================
    // FIX CHAT DELETION LOGIC
    // =================================================================================
    clearChatBtn.addEventListener('click', async () => {
        if (!currentChatId || !confirm("Are you sure you want to delete this chat?")) return;

        const response = await fetch(`/api/chats/${currentChatId}`, { method: 'DELETE' });

        if (response.ok) {
            currentChatId = null; // Reset current chat ID
            await loadChats(); // Reload the list, which will select the top chat or create a new one
        } else {
            alert("Failed to delete chat.");
        }
    });

    // =================================================================================
    // ALL OTHER FUNCTIONS (UNCHANGED, PASTED FOR COMPLETENESS)
    // =================================================================================

    // --- Render Functions ---
    function renderChatList(chats) {
        chatListEl.innerHTML = '';
        if (!chats || chats.length === 0) return;
        chats.forEach(chat => {
            const el = document.createElement('div');
            el.className = `chat-list-item p-3 rounded-xl cursor-pointer border ${currentChatId === chat.id ? 'border-indigo-500/50 bg-indigo-900/30' : 'border-gray-700/50 hover:bg-gray-800/40'}`;
            el.dataset.chatId = chat.id;
            el.innerHTML = `<h3 class="font-medium truncate">Chat ${chat.id}</h3><p class="text-xs text-gray-400 truncate mt-1">${new Date(chat.created_at).toLocaleString()}</p>`;
            el.addEventListener('click', () => selectChat(chat.id));
            chatListEl.appendChild(el);
        });
    }

    function renderMessage(message) {
        const bubble = document.createElement('div');
        const isUser = message.sender === 'user';
        bubble.className = `message-bubble max-w-[85%] rounded-2xl p-5 shadow-lg ${isUser ? 'user-bubble ml-auto' : 'ai-bubble'}`;
        if (message.id) bubble.id = message.id;

        const content = marked.parse(message.content);
        bubble.innerHTML = `<div class="prose prose-invert max-w-none text-left">${content}</div>`;

        chatWindow.appendChild(bubble);
        chatWindow.scrollTop = chatWindow.scrollHeight;
        bubble.querySelectorAll('pre code').forEach(hljs.highlightElement);
        return bubble;
    }

    // --- Core Logic ---
    async function loadModels() {
        try {
            const response = await fetch('/api/models');
            const models = await response.json();
            modelSelector.innerHTML = models.map(m => `<option>${m}</option>`).join('');
        } catch (e) { console.error("Failed to load models:", e); }
    }

    async function loadChats() {
        try {
            const response = await fetch('/api/chats');
            const chats = await response.json();
            renderChatList(chats);
            if (chats.length > 0 && !currentChatId) {
                selectChat(chats[0].id);
            } else if (chats.length === 0) {
                await newChat();
            }
        } catch(e) { console.error("Failed to load chats:", e); }
    }

    async function selectChat(chatId) {
        currentChatId = chatId;
        chatWindow.innerHTML = '';
        const response = await fetch(`/api/chats/${chatId}/messages`);
        const messages = await response.json();
        messages.forEach(renderMessage);
        const chats = await (await fetch('/api/chats')).json();
        renderChatList(chats);
    }

    async function newChat() {
        const response = await fetch('/api/chats', { method: 'POST' });
        const chat = await response.json();
        await loadChats();
        selectChat(chat.id);
    }

    function sendMessage(content, image = null) {
        const message = content || messageInput.value.trim();
        if ((!message && !image) || !currentChatId) return;

        const displayContent = image ? `![User Upload](${image}) \n\n ${message}` : message;
        renderMessage({ sender: 'user', content: displayContent });

        socket.emit('user_message', {
            chat_id: currentChatId,
            message: message,
            model: modelSelector.value,
            image: image
        });
        messageInput.value = '';
    }

    // --- Event Listeners ---
    sendBtn.addEventListener('click', () => sendMessage());
    messageInput.addEventListener('keydown', (e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); } });
    newChatBtn.addEventListener('click', newChat);

    actionButtonsContainer.addEventListener('click', (e) => {
        const action = e.target.closest('.action-btn')?.dataset.action;
        if (!action) return;
        let task = '';
        if (action === 'write_file') task = `/task write file "${prompt('Path:')}" with content: "${prompt('Content:')}"`;
        if (action === 'shell_command') task = `/task run command: ${prompt('Command:')}`;
        if (action === 'take_screenshot') task = `/task screenshot to "${prompt('Filename:', 'screenshot.png')}"`;
        if (task.includes('null')) return;
        sendMessage(task);
    });

    // --- Image Upload ---
    function setupImageUploadListeners() {
        const dropZone = document.body;
        dropZone.addEventListener('dragover', (e) => e.preventDefault());
        dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            const file = e.dataTransfer.files[0];
            if (file && file.type.startsWith('image/')) handleImageFile(file);
        });
        messageInput.addEventListener('paste', (e) => {
            const file = e.clipboardData.files[0];
            if (file && file.type.startsWith('image/')) {
                e.preventDefault();
                handleImageFile(file);
            }
        });
    }

    function handleImageFile(file) {
        const reader = new FileReader();
        reader.onload = (event) => sendMessage(messageInput.value, event.target.result);
        reader.readAsDataURL(file);
    }

    // --- Socket.IO Handlers ---
    socket.on('agent_token', (data) => {
        if (data.chat_id !== currentChatId) return;
        if (startTime === null) startTime = Date.now();
        tokenCount++;
        const tps = (tokenCount / ((Date.now() - startTime) / 1000)).toFixed(1);
        tpsCounter.textContent = tps;
        let bubble = document.getElementById(data.message_id);
        if (!bubble) bubble = renderMessage({ sender: 'agent', content: '', id: data.message_id });
        const proseDiv = bubble.querySelector('.prose');
        proseDiv.textContent += data.token;
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

    socket.on('agent_message', (data) => {
        if (data.chat_id === currentChatId) renderMessage({ sender: 'agent', content: data.message, id: data.message_id });
    });

    // --- Init ---
    function init() {
        loadModels();
        loadChats();
        setupImageUploadListeners();
    }
    init();
});
