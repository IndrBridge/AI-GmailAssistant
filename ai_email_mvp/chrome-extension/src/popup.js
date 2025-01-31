// Constants
const API_BASE_URL = 'http://localhost:8000';

// State management
let isInitialized = false;

// DOM Elements
let elements = {
    connectionStatus: null,
    signInPanel: null,
    mainContent: null,
    signInButton: null,
    tasksCount: null,
    remindersCount: null,
    openGmailButton: null,
    message: null
};

// Initialize popup
document.addEventListener('DOMContentLoaded', async () => {
    console.log('Initializing popup');
    
    // Initialize DOM elements
    elements = {
        connectionStatus: document.getElementById('connection-status'),
        signInPanel: document.getElementById('sign-in-panel'),
        mainContent: document.getElementById('main-content'),
        signInButton: document.getElementById('sign-in-button'),
        tasksCount: document.getElementById('tasks-count'),
        remindersCount: document.getElementById('reminders-count'),
        openGmailButton: document.getElementById('open-gmail'),
        message: document.getElementById('message')
    };

    // Verify all elements exist
    if (!Object.values(elements).every(element => element)) {
        console.error('Failed to initialize DOM elements');
        showError('Extension initialization failed');
        return;
    }

    // Set up event listeners
    elements.signInButton.addEventListener('click', handleSignInClick);
    elements.openGmailButton.addEventListener('click', () => {
        chrome.tabs.create({ url: 'https://mail.google.com' });
    });

    // Initialize
    await initialize();
});

// Initialize the popup state
async function initialize() {
    if (isInitialized) return;
    
    try {
        const authStatus = await checkAuthStatus();
        if (authStatus.error) {
            showError(authStatus.error);
            updateUIState('disconnected');
        } else if (authStatus.isAuthenticated) {
            updateUIState('connected');
            await updateStats();
        } else {
            updateUIState('disconnected');
        }
        isInitialized = true;
    } catch (error) {
        console.error('Initialization failed:', error);
        showError('Failed to initialize. Please try again.');
        updateUIState('disconnected');
    }
}

// Handle sign in click
async function handleSignInClick() {
    console.log('Initiating sign in');
    updateUIState('signing-in');
    hideMessages();

    try {
        const response = await sendMessage('initiate_oauth');
        console.log('Sign in response:', response);

        if (response?.success) {
            const authStatus = await checkAuthStatus();
            if (authStatus.error) {
                throw new Error(authStatus.error);
            }
            showSuccess('Successfully signed in!');
            updateUIState('connected');
            await updateStats();
        } else {
            throw new Error(response?.error || 'Sign in failed');
        }
    } catch (error) {
        console.error('Sign in failed:', error);
        showError('Sign in failed: ' + error.message);
        updateUIState('disconnected');
    }
}

// Check authentication status
async function checkAuthStatus() {
    try {
        const response = await new Promise((resolve) => {
            chrome.runtime.sendMessage({ action: 'checkAuth' }, resolve);
        });
        console.log('Auth check response:', response);
        return response;
    } catch (error) {
        console.error('Auth check failed:', error);
        return { isAuthenticated: false, error: error.message };
    }
}

// Update statistics
async function updateStats() {
    try {
        const authResponse = await checkAuthStatus();
        if (!authResponse.isAuthenticated || !authResponse.user) {
            throw new Error('Not authenticated');
        }

        // Get tasks
        const tasksResponse = await new Promise((resolve) => {
            chrome.runtime.sendMessage({ 
                action: 'fetch',
                endpoint: `/api/tasks/${authResponse.user.email}` 
            }, resolve);
        });

        if (!tasksResponse.ok) {
            throw new Error('Failed to get tasks');
        }

        const tasksData = tasksResponse.data.tasks || [];
        
        // Update UI
        const tasksCount = document.getElementById('tasks-count');
        const remindersCount = document.getElementById('reminders-count');
        
        tasksCount.textContent = tasksData.length.toString();
        remindersCount.textContent = tasksData.filter(task => task.reminder_time).length.toString();
    } catch (error) {
        console.error('Failed to update stats:', error);
        showError('Failed to load statistics');
    }
}

// Helper: Update UI state
function updateUIState(state) {
    const statusDot = elements.connectionStatus.querySelector('.status-dot');
    const statusText = elements.connectionStatus.querySelector('.status-text');

    switch (state) {
        case 'connected':
            elements.connectionStatus.className = 'status-indicator connected';
            statusText.textContent = 'Connected';
            elements.signInPanel.style.display = 'none';
            elements.mainContent.style.display = 'block';
            break;
        case 'disconnected':
            elements.connectionStatus.className = 'status-indicator disconnected';
            statusText.textContent = 'Disconnected';
            elements.signInPanel.style.display = 'block';
            elements.mainContent.style.display = 'none';
            break;
        case 'signing-in':
            elements.connectionStatus.className = 'status-indicator';
            statusText.textContent = 'Signing in...';
            elements.signInButton.disabled = true;
            break;
    }
}

// Helper: Show error message
function showError(message, duration = 5000) {
    elements.message.textContent = message;
    elements.message.className = 'error';
    if (duration) {
        setTimeout(hideMessages, duration);
    }
}

// Helper: Show success message
function showSuccess(message, duration = 3000) {
    elements.message.textContent = message;
    elements.message.className = 'success';
    if (duration) {
        setTimeout(hideMessages, duration);
    }
}

// Helper: Hide messages
function hideMessages() {
    elements.message.textContent = '';
    elements.message.className = '';
}

// Helper: Send message to background script
function sendMessage(action, data = {}) {
    return new Promise((resolve) => {
        chrome.runtime.sendMessage({ action, ...data }, resolve);
    });
}

// Helper: Get access token
async function getAccessToken() {
    try {
        const data = await chrome.storage.local.get(['backend_token', 'token_type']);
        return data.backend_token;
    } catch (error) {
        console.error('Error getting access token:', error);
        return null;
    }
}

// Helper: Fetch with authentication
async function fetchWithAuth(endpoint, options = {}) {
    const token = await getAccessToken();
    if (!token) {
        throw new Error('Not authenticated');
    }

    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        ...options,
        headers: {
            ...options.headers,
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        },
        mode: 'cors'
    });

    const contentType = response.headers.get('content-type');
    const responseData = contentType?.includes('application/json') 
        ? await response.json()
        : await response.text();

    if (!response.ok) {
        throw new Error(typeof responseData === 'string' ? responseData : responseData.detail || 'API request failed');
    }

    return responseData;
}

// Check authentication status and update UI
async function checkAuthAndUpdateUI() {
    try {
        console.log('Checking auth status...');
        const response = await new Promise((resolve) => {
            chrome.runtime.sendMessage({ action: 'checkAuth' }, (response) => {
                if (chrome.runtime.lastError) {
                    resolve({ isAuthenticated: false, error: chrome.runtime.lastError });
                } else {
                    resolve(response);
                }
            });
        });
        console.log('Auth check response:', response);

        const signInPanel = document.getElementById('sign-in-panel');
        const mainContent = document.getElementById('main-content');
        const statusIndicator = document.getElementById('connection-status');
        const statusText = statusIndicator.querySelector('.status-text');

        if (response && response.isAuthenticated && response.user) {
            console.log('User is authenticated:', response.user.email);
            signInPanel.style.display = 'none';
            mainContent.style.display = 'block';
            statusIndicator.classList.remove('disconnected');
            statusIndicator.classList.add('connected');
            statusText.textContent = 'Connected';
            return true;
        } else {
            console.log('User is not authenticated');
            signInPanel.style.display = 'block';
            mainContent.style.display = 'none';
            statusIndicator.classList.remove('connected');
            statusIndicator.classList.add('disconnected');
            statusText.textContent = 'Disconnected';
            return false;
        }
    } catch (error) {
        console.error('Error checking auth:', error);
        document.getElementById('sign-in-panel').style.display = 'block';
        document.getElementById('main-content').style.display = 'none';
        return false;
    }
}

// Handle sign in button click
document.getElementById('sign-in-button').addEventListener('click', async () => {
    try {
        console.log('Starting sign in...');
        const response = await new Promise((resolve) => {
            chrome.runtime.sendMessage({ action: 'initiate_oauth' }, resolve);
        });
        console.log('Sign in response:', response);
        
        if (response && response.success) {
            console.log('Sign in successful');
            await checkAuthAndUpdateUI();
        } else {
            console.error('Sign in failed:', response && response.error);
            throw new Error((response && response.error) || 'Failed to sign in');
        }
    } catch (error) {
        console.error('Sign in error:', error);
        // Update connection status
        const statusIndicator = document.getElementById('connection-status');
        const statusText = document.querySelector('.status-text');
        statusIndicator.classList.remove('connected');
        statusIndicator.classList.add('disconnected');
        statusText.textContent = 'Disconnected';
    }
});

// Initial auth check
document.addEventListener('DOMContentLoaded', () => {
    checkAuthAndUpdateUI();
});
