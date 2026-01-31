// API base URL - use localhost when opening file directly, empty when served by backend
const API_BASE = window.location.protocol === 'file:' ? 'http://localhost:8000' : '';

// DOM Elements
const loginScreen = document.getElementById('login-screen');
const chatScreen = document.getElementById('chat-screen');
const loginBtn = document.getElementById('login-btn');
const logoutBtn = document.getElementById('logout-btn');
const newChatBtn = document.getElementById('new-chat-btn');
const chatForm = document.getElementById('chat-form');
const messageInput = document.getElementById('message-input');
const messagesContainer = document.getElementById('messages');
const sendBtn = document.getElementById('send-btn');
const sidebar = document.getElementById('sidebar');
const menuToggle = document.getElementById('menu-toggle');

// State
let isLoading = false;

// Initialize app
async function init() {
    await checkAuthStatus();
    setupEventListeners();
    setupTextareaAutoResize();
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

// Setup textarea auto-resize
function setupTextareaAutoResize() {
    messageInput.addEventListener('input', () => {
        messageInput.style.height = 'auto';
        messageInput.style.height = Math.min(messageInput.scrollHeight, 200) + 'px';

        // Enable/disable send button based on input
        sendBtn.disabled = !messageInput.value.trim();
    });
}

// Setup event listeners
function setupEventListeners() {
    // Login button
    loginBtn.addEventListener('click', handleLogin);

    // Logout button
    logoutBtn.addEventListener('click', handleLogout);

    // New chat button
    newChatBtn.addEventListener('click', handleResetChat);

    // Chat form submit
    chatForm.addEventListener('submit', handleSendMessage);

    // Handle Enter key (submit) vs Shift+Enter (new line)
    messageInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            if (messageInput.value.trim() && !isLoading) {
                handleSendMessage(e);
            }
        }
    });

    // Suggestion cards
    document.querySelectorAll('.suggestion-card').forEach(btn => {
        btn.addEventListener('click', () => {
            const message = btn.dataset.message;
            messageInput.value = message;
            sendBtn.disabled = false;
            handleSendMessage(new Event('submit'));
        });
    });

    // Sidebar items
    document.querySelectorAll('.sidebar-item[data-message]').forEach(btn => {
        btn.addEventListener('click', () => {
            const message = btn.dataset.message;
            messageInput.value = message;
            sendBtn.disabled = false;
            handleSendMessage(new Event('submit'));
            closeSidebar();
        });
    });

    // Mobile menu toggle
    if (menuToggle) {
        menuToggle.addEventListener('click', toggleSidebar);
    }

    // Sidebar overlay
    const sidebarOverlay = document.getElementById('sidebar-overlay');
    if (sidebarOverlay) {
        sidebarOverlay.addEventListener('click', closeSidebar);
    }

    // Close sidebar when clicking outside on mobile
    document.addEventListener('click', (e) => {
        if (window.innerWidth <= 768 &&
            sidebar.classList.contains('open') &&
            !sidebar.contains(e.target) &&
            e.target !== menuToggle &&
            e.target !== sidebarOverlay) {
            closeSidebar();
        }
    });
}

function toggleSidebar() {
    const sidebarOverlay = document.getElementById('sidebar-overlay');
    sidebar.classList.toggle('open');
    if (sidebarOverlay) {
        sidebarOverlay.classList.toggle('open');
    }
}

function closeSidebar() {
    const sidebarOverlay = document.getElementById('sidebar-overlay');
    sidebar.classList.remove('open');
    if (sidebarOverlay) {
        sidebarOverlay.classList.remove('open');
    }
}

// Handle login
async function handleLogin() {
    try {
        loginBtn.disabled = true;
        loginBtn.innerHTML = '<span>Connecting...</span>';

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
            <svg viewBox="0 0 24 24" width="20" height="20">
                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
            </svg>
            <span>Continue with Google</span>
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
        showWelcomeState();
    } catch (error) {
        console.error('Reset chat error:', error);
    }
}

// Clear messages
function clearMessages() {
    messagesContainer.innerHTML = '';
}

// Show welcome state
function showWelcomeState() {
    messagesContainer.innerHTML = `
        <div class="welcome-state">
            <div class="welcome-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                    <path d="M8 2v4M16 2v4M3 10h18M5 4h14a2 2 0 012 2v14a2 2 0 01-2 2H5a2 2 0 01-2-2V6a2 2 0 012-2z"/>
                    <path d="M8 14h.01M12 14h.01M16 14h.01M8 18h.01M12 18h.01M16 18h.01"/>
                </svg>
            </div>
            <h2>How can I help you today?</h2>
            <p>I can manage your emails, check your calendar, schedule meetings, and more.</p>

            <div class="welcome-suggestions">
                <button class="suggestion-card" data-message="Summarize my important emails from today">
                    <div class="suggestion-icon">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                            <path d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/>
                        </svg>
                    </div>
                    <div class="suggestion-text">
                        <span class="suggestion-title">Email Summary</span>
                        <span class="suggestion-desc">Get important emails from today</span>
                    </div>
                </button>
                <button class="suggestion-card" data-message="What meetings do I have coming up?">
                    <div class="suggestion-icon">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                            <path d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"/>
                        </svg>
                    </div>
                    <div class="suggestion-text">
                        <span class="suggestion-title">Upcoming Meetings</span>
                        <span class="suggestion-desc">View your scheduled meetings</span>
                    </div>
                </button>
                <button class="suggestion-card" data-message="Schedule a meeting for tomorrow at 2pm titled 'Team Sync'">
                    <div class="suggestion-icon">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                            <path d="M12 9v3m0 0v3m0-3h3m-3 0H9m12 0a9 9 0 11-18 0 9 9 0 0118 0z"/>
                        </svg>
                    </div>
                    <div class="suggestion-text">
                        <span class="suggestion-title">Create Event</span>
                        <span class="suggestion-desc">Schedule a new meeting</span>
                    </div>
                </button>
                <button class="suggestion-card" data-message="When am I free this week for a 1-hour meeting?">
                    <div class="suggestion-icon">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                            <path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"/>
                        </svg>
                    </div>
                    <div class="suggestion-text">
                        <span class="suggestion-title">Check Availability</span>
                        <span class="suggestion-desc">Find free time slots</span>
                    </div>
                </button>
            </div>
        </div>
    `;

    // Re-attach suggestion listeners
    document.querySelectorAll('.suggestion-card').forEach(btn => {
        btn.addEventListener('click', () => {
            const message = btn.dataset.message;
            messageInput.value = message;
            sendBtn.disabled = false;
            handleSendMessage(new Event('submit'));
        });
    });
}

// Handle send message
async function handleSendMessage(e) {
    e.preventDefault();

    const message = messageInput.value.trim();
    if (!message || isLoading) return;

    // Remove welcome state if present
    const welcomeState = messagesContainer.querySelector('.welcome-state');
    if (welcomeState) {
        welcomeState.remove();
    }

    // Add user message
    addMessage(message, 'user');
    messageInput.value = '';
    messageInput.style.height = 'auto';
    sendBtn.disabled = true;

    // Show typing indicator
    isLoading = true;
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
        messageInput.focus();
    }
}

// Add message to chat
function addMessage(content, role) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;

    const userIcon = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2"/>
        <circle cx="12" cy="7" r="4"/>
    </svg>`;

    const assistantIcon = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <path d="M8 2v4M16 2v4M3 10h18M5 4h14a2 2 0 012 2v14a2 2 0 01-2 2H5a2 2 0 01-2-2V6a2 2 0 012-2z"/>
    </svg>`;

    messageDiv.innerHTML = `
        <div class="message-avatar">${role === 'user' ? userIcon : assistantIcon}</div>
        <div class="message-content"><p>${escapeHtml(content)}</p></div>
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
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M8 2v4M16 2v4M3 10h18M5 4h14a2 2 0 012 2v14a2 2 0 01-2 2H5a2 2 0 01-2-2V6a2 2 0 012-2z"/>
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
    const chatContainer = document.querySelector('.chat-container');
    if (chatContainer) {
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }
}

// Escape HTML to prevent XSS
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', init);
