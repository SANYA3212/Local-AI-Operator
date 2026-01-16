document.addEventListener('DOMContentLoaded', () => {
    const socket = io({ transports: ['websocket'] });

    // --- DOM Elements ---
    const chatListEl = document.getElementById('chat-list');
    const modelSelector = document.getElementById('model-selector');
    const tpsCounter = document.getElementById('tps-counter'); // Kept for now, but might be removed
    const chatWindow = document.getElementById('chat-window');
    const messageInput = document.getElementById('message-input');
    const sendBtn = document.getElementById('send-btn');
    const newChatBtn = document.getElementById('new-chat-btn');
    const clearChatBtn = document.getElementById('clear-chat-btn');
    const planContainer = document.getElementById('plan-container');
    const planList = document.getElementById('plan-list');
    const stopAgentBtn = document.getElementById('stop-agent-btn');

    // --- State ---
    let currentChatId = null;
    let isAgentRunning = false;
    let currentPlanSteps = [];

    // =================================================================================
    // Core Functions
    // =================================================================================

    async function loadModels() {
        try {
            const response = await fetch('/api/models');
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            const models = await response.json();
            modelSelector.innerHTML = models.map(m => `<option value="${m}">${m}</option>`).join('');
        } catch (e) {
            console.error("Failed to load models:", e);
            displayError("Could not fetch AI models. Is Ollama running?");
        }
    }

    async function loadChats() {
        try {
            const response = await fetch('/api/chats');
            const chats = await response.json();
            renderChatList(chats);
            if (chats.length > 0 && !currentChatId) {
                await selectChat(chats[0].id);
            } else if (chats.length === 0) {
                await newChat();
            }
        } catch(e) { console.error("Failed to load chats:", e); }
    }

    async function selectChat(chatId) {
        if (isAgentRunning) {
            alert("Cannot switch chats while an agent is running.");
            return;
        }
        currentChatId = chatId;
        chatWindow.innerHTML = '';
        resetPlanView();

        const response = await fetch(`/api/chats/${chatId}/messages`);
        const messages = await response.json();
        messages.forEach(renderMessage);

        const chats = await (await fetch('/api/chats')).json();
        renderChatList(chats);
    }

    async function newChat() {
        if (isAgentRunning) {
            alert("Cannot create a new chat while an agent is running.");
            return;
        }
        const response = await fetch('/api/chats', { method: 'POST' });
        const chat = await response.json();
        await loadChats();
        await selectChat(chat.id);
    }

    function sendMessage() {
        const message = messageInput.value.trim();
        if (!message || !currentChatId) return;

        renderMessage({ sender: 'user', content: message });

        if (message.toLowerCase().startsWith('/task')) {
            setAgentStatus(true);
            socket.emit('start_task', {
                chat_id: currentChatId,
                task: message.substring(5).trim(),
                model: modelSelector.value
            });
        } else {
             socket.emit('user_message', {
                chat_id: currentChatId,
                message: message,
                model: modelSelector.value
            });
        }

        messageInput.value = '';
        messageInput.focus();
    }

    function stopAgent() {
        if (!isAgentRunning) return;
        socket.emit('stop_agent', { chat_id: currentChatId });
        setAgentStatus(false);
        renderMessage({ sender: 'agent', content: "Agent execution stopped by user." });
    }

    // =================================================================================
    // UI Rendering and State Management
    // =================================================================================

    function renderChatList(chats) {
        chatListEl.innerHTML = '';
        if (!chats || chats.length === 0) return;
        chats.forEach(chat => {
            const el = document.createElement('div');
            el.className = `p-3 rounded-xl cursor-pointer border ${currentChatId === chat.id ? 'border-indigo-500/50 bg-indigo-900/30' : 'border-gray-700/50 hover:bg-gray-800/40'}`;
            el.dataset.chatId = chat.id;
            el.innerHTML = `<h3 class="font-medium truncate">Chat ${chat.id}</h3><p class="text-xs text-gray-400 truncate mt-1">${new Date(chat.created_at).toLocaleString()}</p>`;
            el.addEventListener('click', () => selectChat(chat.id));
            chatListEl.appendChild(el);
        });
    }

    function renderMessage(message) {
        const { sender, content } = message;
        const bubble = document.createElement('div');
        const isUser = sender === 'user';

        bubble.className = `message-bubble max-w-[85%] rounded-2xl p-4 shadow-lg ${isUser ? 'user-bubble ml-auto' : 'ai-bubble'}`;

        const parsedContent = marked.parse(content || "Thinking...");
        bubble.innerHTML = `<div class="prose prose-invert max-w-none text-left">${parsedContent}</div>`;

        chatWindow.appendChild(bubble);
        chatWindow.scrollTop = chatWindow.scrollHeight;

        bubble.querySelectorAll('pre code').forEach(hljs.highlightElement);
    }

    function displayPlan(planText) {
        const planSteps = planText.replace(/\*\*Generated Plan:\*\*\n/i, "").split('\n').filter(s => s.trim().length > 0);
        currentPlanSteps = planSteps.map(step => step.replace(/^\d+\.\s/, ''));

        planList.innerHTML = '';
        currentPlanSteps.forEach((step, index) => {
            const li = document.createElement('li');
            li.textContent = step;
            li.dataset.stepIndex = index;
            planList.appendChild(li);
        });
        planContainer.classList.remove('hidden');
    }

    function updateActiveStep(stepMessage) {
        const stepMatch = stepMessage.match(/--- Starting Step (\d+)\/(\d+) ---/);
        if (!stepMatch) return;

        const stepNumber = parseInt(stepMatch[1], 10);
        const activeIndex = stepNumber - 1;

        planList.querySelectorAll('li').forEach((li, index) => {
            li.classList.toggle('active', index === activeIndex);
        });
    }

    function resetPlanView() {
        planContainer.classList.add('hidden');
        planList.innerHTML = '';
        currentPlanSteps = [];
    }

    function setAgentStatus(isRunning) {
        isAgentRunning = isRunning;
        stopAgentBtn.classList.toggle('hidden', !isRunning);
        messageInput.disabled = isRunning;
        sendBtn.disabled = isRunning;
        if (!isRunning) {
            resetPlanView();
        }
    }

    function displayError(errorMessage) {
        const errorEl = document.createElement('div');
        errorEl.className = 'p-4 bg-red-800/50 border border-red-600 rounded-lg text-white text-center';
        errorEl.textContent = errorMessage;
        document.body.insertBefore(errorEl, document.body.firstChild);
        setTimeout(() => errorEl.remove(), 5000);
    }

    // =================================================================================
    // Socket.IO Event Handlers
    // =================================================================================

    socket.on('connect', () => console.log('Socket.IO connected.'));
    socket.on('disconnect', () => console.log('Socket.IO disconnected.'));
    socket.on('connect_error', (err) => {
        console.error('Socket.IO connection error:', err);
        displayError("Cannot connect to the backend server.");
    });

    socket.on('agent_response', (data) => {
        if (data.chat_id !== currentChatId) return;

        switch (data.sender) {
            case 'plan':
                displayPlan(data.message);
                break;
            case 'agent':
                renderMessage({ sender: 'agent', content: data.message });
                if (data.message.includes('--- Starting Step')) {
                    updateActiveStep(data.message);
                }
                if (data.message.includes('Task finished') || data.message.includes('Task aborted')) {
                    setAgentStatus(false);
                }
                break;
            case 'thought':
                renderMessage({ sender: 'agent', content: `**Thought:** ${data.message}` });
                break;
            case 'observation':
                renderMessage({ sender: 'agent', content: `**Observation:**\n\`\`\`json\n${data.message}\n\`\`\`` });
                break;
            default:
                renderMessage({ sender: 'agent', content: data.message });
        }
    });

    // =================================================================================
    // Event Listeners
    // =================================================================================

    sendBtn.addEventListener('click', sendMessage);
    messageInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
    newChatBtn.addEventListener('click', newChat);
    stopAgentBtn.addEventListener('click', stopAgent);
    clearChatBtn.addEventListener('click', async () => {
        if (!currentChatId || !confirm("Are you sure you want to delete this chat?")) return;
        if (isAgentRunning) {
            alert("Cannot delete a chat while an agent is running.");
            return;
        }
        const response = await fetch(`/api/chats/${currentChatId}`, { method: 'DELETE' });
        if (response.ok) {
            currentChatId = null;
            await loadChats();
        } else {
            alert("Failed to delete chat.");
        }
    });

    // --- Initialization ---
    function init() {
        loadModels();
        loadChats();
    }

    init();
});
