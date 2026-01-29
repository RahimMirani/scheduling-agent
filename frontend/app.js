// API base URL
const API_BASE = '';

// DOM Elements
const loginScreen = document.getElementById('login-screen');
const chatScreen = document.getElementById('chat-screen');
const loginBtn = document.getElementById('login-btn');
const logoutBtn = document.getElementById('logout-btn');
const resetBtn = document.getElementById('reset-btn');
const chatForm = document.getElementById('chat-form');
const messageInput = document.getElementById('message-input');
const messagesContainer = document.getElementById('messages');
const sendBtn = document.getElementById('send-btn');

// State
let isLoading = false;

// Initialize app
async function init() {
    await checkAuthStatus();
    setupEventListeners();
}

// Check authentication status
async function checkAuthStatus() {
    try {
        const response = await fetch(`${API_BASE}/auth/status`);
        const data = await response.json();

        if (data.authenticated) {
            showChatScreen();
        } else {
            showLoginScreen();
        }
    } catch (error) {
        console.error('Error checking auth status:', error);
        showLoginScreen();
    }
}

// Show login screen
function showLoginScreen() {
    loginScreen.classList.remove('hidden');
    chatScreen.classList.add('hidden');
}

// Show chat screen
function showChatScreen() {
    loginScreen.classList.add('hidden');
    chatScreen.classList.remove('hidden');
    messageInput.focus();
}

// Setup event listeners
function setupEventListeners() {
    // Login button
    loginBtn.addEventListener('click', handleLogin);

    // Logout button
    logoutBtn.addEventListener('click', handleLogout);

    // Reset chat button
    resetBtn.addEventListener('click', handleResetChat);

    // Chat form submit
    chatForm.addEventListener('submit', handleSendMessage);

    // Suggestion buttons
    document.querySelectorAll('.suggestion').forEach(btn => {
        btn.addEventListener('click', () => {
            const message = btn.dataset.message;
            messageInput.value = message;
            handleSendMessage(new Event('submit'));
        });
    });
}

// Handle login
async function handleLogin() {
    try {
        loginBtn.disabled = true;
        loginBtn.innerHTML = 'Redirecting...';

        const response = await fetch(`${API_BASE}/auth/login`);
        const data = await response.json();

        if (data.authorization_url) {
            window.location.href = data.authorization_url;
        } else {
            throw new Error('No authorization URL received');
        }
    } catch (error) {
        console.error('Login error:', error);
        alert('Failed to initiate login. Please try again.');
        loginBtn.disabled = false;
        loginBtn.innerHTML = `
            <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
            </svg>
            Sign in with Google
        `;
    }
}

// Handle logout
async function handleLogout() {
    try {
        await fetch(`${API_BASE}/auth/logout`);
        showLoginScreen();
        clearMessages();
    } catch (error) {
        console.error('Logout error:', error);
    }
}

// Handle reset chat
async function handleResetChat() {
    try {
        await fetch(`${API_BASE}/api/chat/reset`, { method: 'POST' });
        clearMessages();
        showWelcomeMessage();
    } catch (error) {
        console.error('Reset chat error:', error);
    }
}

// Clear messages
function clearMessages() {
    messagesContainer.innerHTML = '';
}

// Show welcome message
function showWelcomeMessage() {
    messagesContainer.innerHTML = `
        <div class="welcome-message">
            <h2>Welcome to Scheduling Agent</h2>
            <p>I can help you manage your emails and calendar. Try asking:</p>
            <div class="suggestions">
                <button class="suggestion" data-message="Do I have any unread emails?">Do I have any unread emails?</button>
                <button class="suggestion" data-message="What's on my calendar today?">What's on my calendar today?</button>
                <button class="suggestion" data-message="What events do I have this week?">What events do I have this week?</button>
                <button class="suggestion" data-message="Find free slots for a 30-minute meeting">Find free slots for a meeting</button>
            </div>
        </div>
    `;

    // Re-attach suggestion listeners
    document.querySelectorAll('.suggestion').forEach(btn => {
        btn.addEventListener('click', () => {
            const message = btn.dataset.message;
            messageInput.value = message;
            handleSendMessage(new Event('submit'));
        });
    });
}

// Handle send message
async function handleSendMessage(e) {
    e.preventDefault();

    const message = messageInput.value.trim();
    if (!message || isLoading) return;

    // Remove welcome message if present
    const welcomeMessage = messagesContainer.querySelector('.welcome-message');
    if (welcomeMessage) {
        welcomeMessage.remove();
    }

    // Add user message
    addMessage(message, 'user');
    messageInput.value = '';

    // Show typing indicator
    isLoading = true;
    sendBtn.disabled = true;
    const typingIndicator = addTypingIndicator();

    try {
        const response = await fetch(`${API_BASE}/api/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ message }),
        });

        const data = await response.json();

        // Remove typing indicator
        typingIndicator.remove();

        if (response.ok) {
            addMessage(data.response, 'assistant');
        } else {
            addMessage(`Error: ${data.detail || 'Something went wrong'}`, 'assistant');
        }
    } catch (error) {
        console.error('Chat error:', error);
        typingIndicator.remove();
        addMessage('Sorry, I encountered an error. Please try again.', 'assistant');
    } finally {
        isLoading = false;
        sendBtn.disabled = false;
        messageInput.focus();
    }
}

// Add message to chat
function addMessage(content, role) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;

    const avatarIcon = role === 'user'
        ? '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>'
        : '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>';

    messageDiv.innerHTML = `
        <div class="message-avatar">${avatarIcon}</div>
        <div class="message-content">${escapeHtml(content)}</div>
    `;

    messagesContainer.appendChild(messageDiv);
    scrollToBottom();
}

// Add typing indicator
function addTypingIndicator() {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message assistant';
    messageDiv.innerHTML = `
        <div class="message-avatar">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>
                <line x1="16" y1="2" x2="16" y2="6"/>
                <line x1="8" y1="2" x2="8" y2="6"/>
                <line x1="3" y1="10" x2="21" y2="10"/>
            </svg>
        </div>
        <div class="message-content">
            <div class="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
            </div>
        </div>
    `;
    messagesContainer.appendChild(messageDiv);
    scrollToBottom();
    return messageDiv;
}

// Scroll to bottom of messages
function scrollToBottom() {
    const chatMain = document.querySelector('.chat-main');
    chatMain.scrollTop = chatMain.scrollHeight;
}

// Escape HTML to prevent XSS
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', init);
