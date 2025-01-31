// Constants
const API_BASE_URL = 'http://localhost:8000';

console.log('Background script loaded');

// Handle OAuth flow
async function initiateOAuth() {
  try {
    console.log('=== Starting OAuth flow ===');
    
    const token = await new Promise((resolve, reject) => {
      chrome.identity.getAuthToken({ 
        interactive: true,
        scopes: [
          'https://www.googleapis.com/auth/gmail.readonly',
          'https://www.googleapis.com/auth/gmail.modify',
          'https://www.googleapis.com/auth/gmail.labels',
          'https://www.googleapis.com/auth/userinfo.profile',
          'https://www.googleapis.com/auth/userinfo.email'
        ]
      }, (token) => {
        if (chrome.runtime.lastError) {
          console.error('Chrome Identity error:', chrome.runtime.lastError);
          reject(chrome.runtime.lastError);
          return;
        }
        console.log('Got Chrome Identity token:', token ? 'Token received' : 'No token');
        resolve(token);
      });
    });

    if (!token) {
      throw new Error('No token received from Chrome Identity');
    }

    console.log('Exchanging token with backend...');

    const response = await fetch(`${API_BASE_URL}/api/oauth/callback`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      },
      body: JSON.stringify({ token }),
      mode: 'cors'
    });

    console.log('Backend response status:', response.status);
    const data = await response.json();
    console.log('Backend response:', data.access_token ? 'Token received' : 'No token in response');
    console.log('Token type:', data.token_type);

    // Store the backend token
    console.log('Storing tokens in chrome.storage...');
    await chrome.storage.local.set({ 
      backend_token: data.access_token,
      token_type: data.token_type || 'Bearer'
    });
    
    console.log('Verifying storage...');
    const stored = await chrome.storage.local.get(['backend_token', 'token_type']);
    console.log('Stored token exists:', !!stored.backend_token);
    console.log('Stored token type:', stored.token_type);

    console.log('=== OAuth flow completed successfully ===');
    return { success: true };
  } catch (error) {
    console.error('OAuth flow failed:', error);
    return { success: false, error: error.message };
  }
}

// Add this function to notify content script of auth changes
async function notifyAuthStateChange() {
  const tabs = await chrome.tabs.query({ url: '*://mail.google.com/*' });
  tabs.forEach(tab => {
    chrome.tabs.sendMessage(tab.id, { action: 'authStateChanged' });
  });
}

// Update the handleAuthCallback function
async function handleAuthCallback(token) {
  if (token) {
    await chrome.storage.local.set({ 'authToken': token });
    notifyAuthStateChange();
    return { success: true };
  }
  return { success: false };
}

// Check auth status
async function checkAuth() {
  try {
    console.log('=== Checking auth status ===');
    
    const stored = await chrome.storage.local.get(['backend_token', 'token_type']);
    console.log('Retrieved from storage:', {
      hasToken: !!stored.backend_token,
      tokenType: stored.token_type
    });
    
    if (!stored.backend_token) {
      console.log('No backend token found in storage');
      return { isAuthenticated: false };
    }

    console.log('Making backend verification request...');
    const response = await fetch(`${API_BASE_URL}/api/users/me`, {
      headers: {
        'Authorization': `${stored.token_type || 'Bearer'} ${stored.backend_token}`,
        'Accept': 'application/json'
      },
      mode: 'cors'
    });

    console.log('Backend verification:', {
      status: response.status,
      ok: response.ok
    });
    
    if (!response.ok) {
      const errorText = await response.text();
      console.error('Verification failed:', errorText);
      return { isAuthenticated: false, error: errorText };
    }

    const userData = await response.json();
    console.log('User data:', userData);
    return { isAuthenticated: true, user: userData };
    
  } catch (error) {
    console.error('Auth check failed:', error);
    return { isAuthenticated: false, error: error.message };
  }
}

// Handle API requests
async function handleFetch(endpoint, options = {}) {
  try {
    const { backend_token, token_type } = await chrome.storage.local.get(['backend_token', 'token_type']);
    if (!backend_token) {
      return { ok: false, error: 'No auth token' };
    }

    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      headers: {
        ...options.headers,
        'Authorization': `${token_type || 'Bearer'} ${backend_token}`,
        'Accept': 'application/json'
      },
      mode: 'cors'
    });

    if (!response.ok) {
      const error = await response.text();
      return { ok: false, error };
    }

    const data = await response.json();
    return { ok: true, data };
  } catch (error) {
    console.error('API request failed:', error);
    return { ok: false, error: error.message };
  }
}

// Listen for messages
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  console.log('Received message:', request.action);

  if (request.action === 'getAuthToken') {
    chrome.storage.local.get(['backend_token'], (result) => {
      console.log('Sending stored token:', result.backend_token ? 'Token exists' : 'No token');
      sendResponse({ token: result.backend_token });
    });
    return true; // Will respond asynchronously
  }

  if (request.action === 'initiate_oauth') {
    initiateOAuth().then(sendResponse);
    return true; // Will respond asynchronously
  }

  if (request.action === 'checkAuth') {
    checkAuth()
      .then(result => {
        console.log('Sending auth check response:', result);
        sendResponse(result);
      })
      .catch(error => {
        console.error('Auth check error:', error);
        sendResponse({ isAuthenticated: false, error: error.message });
      });
    return true; // Will respond asynchronously
  }

  if (request.action === 'fetch') {
    handleFetch(request.endpoint, request.options)
      .then(sendResponse)
      .catch(error => sendResponse({ ok: false, error: error.message }));
    return true; // Will respond asynchronously
  }

  return false;
});

// Handle extension installation or update
chrome.runtime.onInstalled.addListener((details) => {
  console.log('Extension installed/updated:', details.reason);
  // Clear any existing auth data
  chrome.storage.local.remove(['backend_token', 'auth_time']);
});
