// This will be a complete replacement for main.js to ensure no old code interferes.

document.addEventListener('DOMContentLoaded', () => {
    // --- DIAGONSTIC STEP ---
    // Explicitly connect to the server's Socket.IO endpoint.
    // This is more robust than relying on the default.
    const socket = io("http://127.0.0.1:8000", {
        transports: ['websocket'] // Force WebSocket to avoid potential issues with polling
    });

    // --- DOM Elements ---
    const chatListEl = document.getElementById('chat-list');
    const modelSelector = document.getElementById('model-selector');
    const tpsCounter = document.getElementById('tps-counter');
    const chatWindow = document.getElementById('chat-window');
    const messageInput = document.getElementById('message-input');
    const sendBtn = document.getElementById('send-btn');
    const newChatBtn = document.getElementById('new-chat-btn');
    const clearChatBtn = document.getElementById('clear-chat-btn');

    // --- State ---
    let currentChatId = null;

    // =================================================================================
    // DIAGNOSTIC LOGGING
    // =================================================================================
    console.log("JavaScript loaded. Attempting to connect to WebSocket...");

    socket.on('connect', () => {
        console.log('%c<<<<< SOCKET CONNECTED >>>>>', 'color: #4CAF50; font-weight: bold;');
        console.log('Socket ID:', socket.id);
    });

    socket.on('disconnect', (reason) => {
        console.log('%c>>>>> SOCKET DISCONNECTED <<<<<', 'color: #F44336; font-weight: bold;');
        console.log('Reason:', reason);
    });

    socket.on('connect_error', (error) => {
        console.error('%c!!!! SOCKET CONNECTION ERROR !!!!', 'color: #FFC107; font-weight: bold;', error);
    });

    // =================================================================================
    // CORE LOGIC WITH LOGGING
    // =================================================================================
    function sendMessage() {
        const message = messageInput.value.trim();
        if (!message || !currentChatId) {
            console.warn("SendMessage aborted: message or currentChatId is missing.");
            return;
        }

        const payload = {
            chat_id: currentChatId,
            message: message,
            model: modelSelector.value
        };

        console.log('%c--- CLIENT SENDING user_message ---', 'color: #2196F3; font-weight: bold;');
        console.log('Payload:', payload);

        // Render user message immediately
        renderMessage({ sender: 'user', content: message });

        socket.emit('user_message', payload);
        messageInput.value = '';
    }

    // --- The rest of the functions (render, load, etc.) ---
    // For this diagnostic step, I will keep them minimal to isolate the problem.
    // The full functionality will be restored after the connection issue is solved.

    function renderMessage(message) {
        const bubble = document.createElement('div');
        const isUser = message.sender === 'user';
        bubble.className = `p-4 my-2 rounded-lg max-w-[85%] ${isUser ? 'bg-blue-600 ml-auto' : 'bg-gray-700'}`;
        bubble.innerHTML = `<div class="prose prose-invert max-w-none">${marked.parse(message.content)}</div>`;
        chatWindow.appendChild(bubble);
        chatWindow.scrollTop = chatWindow.scrollHeight;
        bubble.querySelectorAll('pre code').forEach(hljs.highlightElement);
    }

    async function initialize() {
        console.log("Initializing chat...");
        try {
            const response = await fetch('/api/chats', { method: 'POST' });
            if (!response.ok) throw new Error('Failed to create initial chat');
            const chat = await response.json();
            currentChatId = chat.id;
            console.log("Initialization complete. Current chat ID:", currentChatId);
            chatListEl.innerHTML = `<div class="p-3 text-sm text-green-400">Diagnostic Mode. Chat ID: ${currentChatId}</div>`;

            const modelsResponse = await fetch('/api/models');
            if (!modelsResponse.ok) throw new Error('Failed to load models');
            const models = await modelsResponse.json();
            modelSelector.innerHTML = models.map(m => `<option>${m}</option>`).join('');
        } catch (error) {
            console.error("Initialization failed:", error);
            chatListEl.innerHTML = `<div class="p-3 text-sm text-red-400">Initialization failed. Check console.</div>`;
        }
    }

    sendBtn.addEventListener('click', sendMessage);
    messageInput.addEventListener('keydown', (e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); } });

    // Dummy listeners for other buttons to prevent errors
    newChatBtn.addEventListener('click', () => console.log("New Chat clicked"));
    clearChatBtn.addEventListener('click', () => console.log("Clear Chat clicked"));

    // Simplified receiver for now
    socket.on('agent_token', (data) => {
        let bubble = document.getElementById(data.message_id);
        if (!bubble) {
            bubble = renderMessage({ sender: 'agent', content: '', id: data.message_id });
        }
        bubble.querySelector('.prose').textContent += data.token;
    });

    initialize();
});
