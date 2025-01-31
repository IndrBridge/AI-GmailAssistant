// Constants
const API_BASE_URL = 'http://localhost:8000';

// UI Component Class
class GmailAssistant {
  constructor() {
    this.isAuthenticated = false;
    this.panel = null;
    this.sidebarButton = null;
    this.teamMembers = null;
    this.processedEmails = new Set(); // Track processed emails
    this.initialize();
  }

  async initialize() {
    console.log('Initializing Gmail Assistant...');
    // Wait for Gmail UI to load completely
    await this.waitForElement('div[role="navigation"]');
    console.log('Gmail UI loaded, setting up assistant...');
    this.setupSidebarButton();
    this.setupMessageObserver();
    this.checkAuthState();
    this.setupEmailObserver();
  }

  setupSidebarButton() {
    console.log('Setting up sidebar button...');
    const sidebarContainer = document.querySelector('div[role="navigation"]');
    if (!sidebarContainer) {
      console.log('Sidebar container not found');
      return;
    }

    // Create button using Gmail's class structure
    this.sidebarButton = document.createElement('div');
    this.sidebarButton.className = 'T-I T-I-KE L3';
    this.sidebarButton.setAttribute('role', 'button');
    this.sidebarButton.setAttribute('data-tooltip', 'Gmail Assistant');
    this.sidebarButton.style.marginTop = '16px';
    this.sidebarButton.innerHTML = `
      <div class="asa">
        <div class="assistant-toggle-icon">
          <svg viewBox="0 0 24 24">
            <path d="M20.5 3l-.16.03L15 5.1 9 3 3.36 4.9c-.21.07-.36.25-.36.48V20.5c0 .28.22.5.5.5l.16-.03L9 18.9l6 2.1 5.64-1.9c.21-.07.36-.25.36-.48V3.5c0-.28-.22-.5-.5-.5z"/>
          </svg>
        </div>
      </div>
    `;

    // Add click handler
    this.sidebarButton.addEventListener('click', () => {
      console.log('Toggle button clicked, auth state:', this.isAuthenticated);
      if (!this.isAuthenticated) {
        console.log('Not authenticated, ignoring click');
        return;
      }
      
      if (!this.panel) {
        console.log('Creating panel...');
        this.setupAssistantPanel();
      }
      
      console.log('Toggling panel visibility');
      this.panel.classList.toggle('hidden');
      
      // Toggle active state
      this.sidebarButton.classList.toggle('T-I-JO');
    });

    // Add to Gmail's navigation
    sidebarContainer.appendChild(this.sidebarButton);
    console.log('Sidebar button added to navigation');
  }

  async checkAuthState() {
    console.log('Checking auth state...');
    try {
      const response = await chrome.runtime.sendMessage({ action: 'checkAuth' });
      console.log('Auth state response:', response);
      this.isAuthenticated = response.isAuthenticated;
      
      if (this.isAuthenticated) {
        console.log('User is authenticated, updating UI...');
        if (this.sidebarButton) {
          this.sidebarButton.classList.remove('disabled');
        }
        if (!this.panel) {
          this.setupAssistantPanel();
        }
        this.panel?.classList.remove('hidden');
      } else {
        console.log('User is not authenticated, disabling UI...');
        if (this.sidebarButton) {
          this.sidebarButton.classList.add('disabled');
        }
        this.panel?.classList.add('hidden');
      }
    } catch (error) {
      console.error('Error checking auth state:', error);
    }
  }

  // Helper function to wait for element
  waitForElement(selector) {
    return new Promise(resolve => {
      if (document.querySelector(selector)) {
        return resolve(document.querySelector(selector));
      }

      const observer = new MutationObserver(mutations => {
        if (document.querySelector(selector)) {
          observer.disconnect();
          resolve(document.querySelector(selector));
        }
      });

      observer.observe(document.body, {
        childList: true,
        subtree: true
      });
    });
  }

  // Listen for auth state changes
  setupMessageObserver() {
    chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
      if (message.action === 'authStateChanged') {
        this.checkAuthState();
      }
    });
  }

  // Authentication methods
  async handleLogin() {
    try {
      const response = await chrome.runtime.sendMessage({ action: 'initiate_oauth' });
      if (response.success) {
        this.isAuthenticated = true;
        this.checkAuthState();
      }
    } catch (error) {
      console.error('Login failed:', error);
      this.showError('Login failed. Please try again.');
    }
  }

  // Email processing methods
  async detectCurrentEmail() {
    const emailContent = document.querySelector('.a3s.aiL');
    if (emailContent && emailContent.textContent !== this.currentEmail?.content) {
      this.currentEmail = {
        content: emailContent.textContent,
        subject: document.querySelector('h2.hP')?.textContent || '',
        sender: document.querySelector('.gD')?.getAttribute('email') || ''
      };
    }
  }

  async processCurrentEmail() {
    const emailId = this.getCurrentEmailId();
    if (!emailId) {
      this.showError('Could not identify email');
      return;
    }

    if (this.processedEmails.has(emailId)) {
      this.showError('Email already processed');
      return;
    }

    const extractTab = this.panel.querySelector('#extract-tab');
    const tasksContainer = extractTab.querySelector('.extracted-tasks');
    
    tasksContainer.innerHTML = `
      <div class="status-message">Processing email...</div>
      <div class="loading-indicator"></div>
    `;

    try {
      const content = this.getCurrentEmailContent();
      if (!content) {
        this.showError('No email content found');
        return;
      }

      tasksContainer.innerHTML = `
        <div class="status-message">Analyzing email content...</div>
        <div class="loading-indicator"></div>
      `;

      const token = await this.getAuthToken();
      if (!token) {
        this.showError('Not authenticated');
        return;
      }

      tasksContainer.innerHTML = `
        <div class="status-message">Extracting tasks...</div>
        <div class="loading-indicator"></div>
      `;

      const response = await fetch(`${API_BASE_URL}/api/emails/current/process`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          content: content,
          subject: document.querySelector('.hP')?.innerText || '',
          sender: document.querySelector('.gD')?.getAttribute('email') || '',
          gmail_id: emailId,
          thread_id: emailId
        })
      });

      if (!response.ok) {
        throw new Error(`Failed to extract tasks: ${response.status}`);
      }

      const result = await response.json();
      console.log('API response:', result); // Debug log

      if (result && result.tasks && result.tasks.length > 0) {
        this.displayExtractedTasks(result.tasks, result.suggested_reply);
        this.processedEmails.add(emailId);
        this.showSuccess('Tasks extracted successfully');
      } else {
        tasksContainer.innerHTML = '<div class="no-tasks">No tasks found in this email.</div>';
      }
    } catch (error) {
      console.error('Error processing email:', error);
      this.showError(error.message || 'Failed to process email');
      tasksContainer.innerHTML = `
        <div class="status-message" style="color: #d93025;">
          ${error.message || 'Failed to process email'}
        </div>
      `;
    }
  }

  async confirmTask(taskId) {
    try {
      const response = await fetch(`http://localhost:8000/api/tasks/${taskId}/confirm`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${await this.getAuthToken()}`
        }
      });

      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
      
      const taskElement = document.querySelector(`[data-task-id="${taskId}"]`).closest('.task-item');
      taskElement.classList.add('confirmed');
      setTimeout(() => taskElement.remove(), 500);
    } catch (error) {
      console.error('Error confirming task:', error);
      this.showError('Failed to confirm task. Please try again.');
    }
  }

  async rejectTask(taskId) {
    try {
      const response = await fetch(`http://localhost:8000/api/tasks/${taskId}/reject`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${await this.getAuthToken()}`
        }
      });

      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
      
      const taskElement = document.querySelector(`[data-task-id="${taskId}"]`).closest('.task-item');
      taskElement.classList.add('rejected');
      setTimeout(() => taskElement.remove(), 500);
    } catch (error) {
      console.error('Error rejecting task:', error);
      this.showError('Failed to reject task. Please try again.');
    }
  }

  async assignTask(taskId, memberId) {
    try {
      const response = await fetch(`${API_BASE_URL}/api/tasks/${taskId}/assign`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${await this.getAuthToken()}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ member_id: memberId })
      });

      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
      this.showSuccess('Task assigned successfully');
    } catch (error) {
      console.error('Error assigning task:', error);
      this.showError('Failed to assign task');
    }
  }

  async useReply(replyText) {
    // Find Gmail's reply button and insert the reply
    const replyButton = document.querySelector('div[data-tooltip="Reply"]');
    if (replyButton) {
      replyButton.click();
      
      // Wait for reply window to open and add text
      setTimeout(() => {
        const messageBody = document.querySelector('div[aria-label="Message Body"]');
        if (messageBody) {
          messageBody.innerHTML = replyText;
        }
      }, 500);
    } else {
      this.showError('Could not find reply button');
    }
  }

  getCurrentEmailContent() {
    try {
      // Try different Gmail selectors for email content
      const selectors = [
        '.a3s.aiL', // Primary content
        '.ii.gt', // Alternative content
        '.gE.iv.gt', // Another possible content area
        '.adP.adO > div[dir="ltr"]', // Direct message content
        '.gmail_quote', // Quoted content
      ];

      let content = '';
      
      // Try each selector and combine content
      for (const selector of selectors) {
        const element = document.querySelector(selector);
        if (element && element.textContent.trim()) {
          content += element.textContent.trim() + '\n';
        }
      }

      // If no content found through selectors, try getting the entire email body
      if (!content) {
        const emailBody = document.querySelector('.gs');
        if (emailBody) {
          content = emailBody.textContent.trim();
        }
      }

      if (!content) {
        console.error('No email content found');
        return null;
      }

      return content;
    } catch (error) {
      console.error('Error getting email content:', error);
      return null;
    }
  }

  getCurrentEmailId() {
    try {
      // Get ID from URL
      const url = window.location.href;
      const match = url.match(/#inbox\/([^/]+)/);
      if (match) return match[1];

      // Alternative: try data attribute
      const emailContainer = document.querySelector('[data-message-id]');
      if (emailContainer) return emailContainer.getAttribute('data-message-id');

      console.error('No email ID found');
      return null;
    } catch (error) {
      console.error('Error getting email ID:', error);
      return null;
    }
  }

  updateEmailSummary(summary) {
    const container = document.getElementById('email-summary') || this.createSummaryContainer();
    if (container) {
      container.innerHTML = `<div class="summary-content">${summary || 'No summary available'}</div>`;
    }
  }

  updateTaskSuggestions(tasks) {
    const container = document.getElementById('task-suggestions') || this.createTaskContainer();
    if (container) {
      if (!tasks || tasks.length === 0) {
        container.innerHTML = '<div class="no-tasks">No tasks found</div>';
        return;
      }

      const tasksList = tasks.map(task => `
        <div class="task-item">
          <div class="task-content">${task.content}</div>
          ${task.due_date ? `<div class="task-due-date">Due: ${new Date(task.due_date).toLocaleDateString()}</div>` : ''}
          <div class="task-actions">
            <button class="action-button confirm-task" data-task-id="${task.id}">Confirm</button>
            <button class="action-button reject-task" data-task-id="${task.id}">Reject</button>
          </div>
        </div>
      `).join('');

      container.innerHTML = tasksList;
    }
  }

  createSummaryContainer() {
    const existingContainer = document.getElementById('email-summary');
    if (existingContainer) return existingContainer;

    const container = document.createElement('div');
    container.id = 'email-summary';
    container.className = 'email-summary';
    
    // Insert after the email content
    const emailContainer = document.querySelector('.a3s.aiL');
    if (emailContainer) {
      emailContainer.parentNode.insertBefore(container, emailContainer.nextSibling);
    }
    return container;
  }

  createTaskContainer() {
    const existingContainer = document.getElementById('task-suggestions');
    if (existingContainer) return existingContainer;

    const container = document.createElement('div');
    container.id = 'task-suggestions';
    container.className = 'task-suggestions';
    
    // Insert after the summary container
    const summaryContainer = document.getElementById('email-summary');
    if (summaryContainer) {
      summaryContainer.parentNode.insertBefore(container, summaryContainer.nextSibling);
    } else {
      // Fallback: insert after email content
      const emailContainer = document.querySelector('.a3s.aiL');
      if (emailContainer) {
        emailContainer.parentNode.insertBefore(container, emailContainer.nextSibling);
      }
    }
    return container;
  }

  // Task management methods
  async loadTasks() {
    try {
      const response = await chrome.runtime.sendMessage({ action: 'fetch', endpoint: '/api/tasks', options: { method: 'GET' } });

      if (response.ok) {
        this.tasks = response.data.tasks;
        this.renderTasks();
      }
    } catch (error) {
      console.error('Failed to load tasks:', error);
    }
  }

  async createTask(taskData) {
    try {
      const response = await chrome.runtime.sendMessage({ action: 'fetch', endpoint: '/api/tasks', options: { method: 'POST', body: JSON.stringify(taskData) } });

      if (response.ok) {
        const newTask = response.data.task;
        this.tasks.push(newTask);
        this.renderTasks();
        this.showSuccess('Task created successfully');
      }
    } catch (error) {
      console.error('Failed to create task:', error);
      this.showError('Failed to create task');
    }
  }

  async updateTask(taskId, taskData) {
    try {
      const response = await chrome.runtime.sendMessage({ action: 'fetch', endpoint: `/api/tasks/${taskId}`, options: { method: 'PUT', body: JSON.stringify(taskData) } });

      if (response.ok) {
        const updatedTask = response.data.task;
        this.tasks = this.tasks.map(task => task.id === taskId ? updatedTask : task);
        this.renderTasks();
        this.showSuccess('Task updated successfully');
      }
    } catch (error) {
      console.error('Failed to update task:', error);
      this.showError('Failed to update task');
    }
  }

  async deleteTask(taskId) {
    try {
      const response = await chrome.runtime.sendMessage({ action: 'fetch', endpoint: `/api/tasks/${taskId}`, options: { method: 'DELETE' } });

      if (response.ok) {
        this.tasks = this.tasks.filter(task => task.id !== taskId);
        this.renderTasks();
        this.showSuccess('Task deleted successfully');
      }
    } catch (error) {
      console.error('Failed to delete task:', error);
      this.showError('Failed to delete task');
    }
  }

  // UI update methods
  updateUIState() {
    if (!this.panel) return;
    
    if (this.isAuthenticated) {
      this.panel.classList.remove('hidden');
      this.loadTasks();
    } else {
      this.panel.classList.add('hidden');
    }
  }

  renderTasks() {
    const taskList = document.getElementById('task-list');
    taskList.innerHTML = this.tasks.map(task => `
      <div class="task-item ${task.completed ? 'completed' : ''}" data-task-id="${task.id}">
        <div class="task-header">
          <input type="checkbox" ${task.completed ? 'checked' : ''} 
                 onchange="window.gmailAssistant.toggleTask(${task.id})">
          <span class="task-title">${task.title}</span>
          <div class="task-actions">
            <button class="icon-button" onclick="window.gmailAssistant.editTask(${task.id})" title="Edit">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                <path d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04c.39-.39.39-1.02 0-1.41l-2.34-2.34c-.39-.39-1.02-.39-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z"/>
              </svg>
            </button>
            <button class="icon-button" onclick="window.gmailAssistant.showReminderDialog(${task.id})" title="Set Reminder">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 22c1.1 0 2-.9 2-2h-4c0 1.1.9 2 2 2zm6-6v-5c0-3.07-1.63-5.64-4.5-6.32V4c0-.83-.67-1.5-1.5-1.5s-1.5.67-1.5 1.5v.68C7.64 5.36 6 7.92 6 11v5l-2 2v1h16v-1l-2-2zm-2 1H8v-6c0-2.48 1.51-4.5 4-4.5s4 2.02 4 4.5v6z"/>
              </svg>
            </button>
            <button class="icon-button" onclick="window.gmailAssistant.deleteTask(${task.id})" title="Delete">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                <path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/>
              </svg>
            </button>
          </div>
        </div>
        ${task.due_date ? `
          <div class="task-details">
            <span class="task-due-date">Due: ${new Date(task.due_date).toLocaleDateString()}</span>
          </div>
        ` : ''}
      </div>
    `).join('');
  }

  // Dialog methods
  showAddTaskDialog() {
    const dialog = document.createElement('div');
    dialog.className = 'dialog-overlay';
    dialog.innerHTML = `
      <div class="dialog">
        <div class="dialog-header">
          <h3>Add Task</h3>
          <button class="close-button" onclick="this.closest('.dialog-overlay').remove()">×</button>
        </div>
        <div class="dialog-content">
          <div class="form-group">
            <label for="task-title">Title</label>
            <input type="text" id="task-title" placeholder="Enter task title">
          </div>
          <div class="form-group">
            <label for="task-due-date">Due Date</label>
            <input type="date" id="task-due-date">
          </div>
          <div class="form-group">
            <label for="task-description">Description</label>
            <textarea id="task-description" rows="3" placeholder="Enter task description"></textarea>
          </div>
        </div>
        <div class="dialog-footer">
          <button class="secondary-button" onclick="this.closest('.dialog-overlay').remove()">Cancel</button>
          <button class="primary-button" onclick="window.gmailAssistant.handleAddTask()">Add Task</button>
        </div>
      </div>
    `;
    document.body.appendChild(dialog);
  }

  async handleAddTask() {
    const title = document.getElementById('task-title').value;
    const dueDate = document.getElementById('task-due-date').value;
    const description = document.getElementById('task-description').value;

    if (!title) {
      this.showError('Task title is required');
      return;
    }

    const taskData = {
      title,
      description,
      due_date: dueDate || null
    };

    await this.createTask(taskData);
    document.querySelector('.dialog-overlay').remove();
  }

  showEditTaskDialog(taskId) {
    const task = this.tasks.find(t => t.id === taskId);
    if (!task) return;

    const dialog = document.createElement('div');
    dialog.className = 'dialog-overlay';
    dialog.innerHTML = `
      <div class="dialog">
        <div class="dialog-header">
          <h3>Edit Task</h3>
          <button class="close-button" onclick="this.closest('.dialog-overlay').remove()">×</button>
        </div>
        <div class="dialog-content">
          <div class="form-group">
            <label for="edit-task-title">Title</label>
            <input type="text" id="edit-task-title" value="${task.title}" placeholder="Enter task title">
          </div>
          <div class="form-group">
            <label for="edit-task-due-date">Due Date</label>
            <input type="date" id="edit-task-due-date" value="${task.due_date || ''}">
          </div>
          <div class="form-group">
            <label for="edit-task-description">Description</label>
            <textarea id="edit-task-description" rows="3" placeholder="Enter task description">${task.description || ''}</textarea>
          </div>
        </div>
        <div class="dialog-footer">
          <button class="secondary-button" onclick="this.closest('.dialog-overlay').remove()">Cancel</button>
          <button class="primary-button" onclick="window.gmailAssistant.handleEditTask(${taskId})">Save Changes</button>
        </div>
      </div>
    `;
    document.body.appendChild(dialog);
  }

  async handleEditTask(taskId) {
    const title = document.getElementById('edit-task-title').value;
    const dueDate = document.getElementById('edit-task-due-date').value;
    const description = document.getElementById('edit-task-description').value;

    if (!title) {
      this.showError('Task title is required');
      return;
    }

    const taskData = {
      title,
      description,
      due_date: dueDate || null
    };

    await this.updateTask(taskId, taskData);
    document.querySelector('.dialog-overlay').remove();
  }

  showReminderDialog(taskId) {
    const task = this.tasks.find(t => t.id === taskId);
    if (!task) return;

    const dialog = document.createElement('div');
    dialog.className = 'dialog-overlay';
    dialog.innerHTML = `
      <div class="dialog">
        <div class="dialog-header">
          <h3>Set Reminder</h3>
          <button class="close-button" onclick="this.closest('.dialog-overlay').remove()">×</button>
        </div>
        <div class="dialog-content">
          <div class="form-group">
            <label for="reminder-date">Date</label>
            <input type="date" id="reminder-date" min="${new Date().toISOString().split('T')[0]}">
          </div>
          <div class="form-group">
            <label for="reminder-time">Time</label>
            <input type="time" id="reminder-time">
          </div>
        </div>
        <div class="dialog-footer">
          <button class="secondary-button" onclick="this.closest('.dialog-overlay').remove()">Cancel</button>
          <button class="primary-button" onclick="window.gmailAssistant.handleSetReminder(${taskId})">Set Reminder</button>
        </div>
      </div>
    `;
    document.body.appendChild(dialog);
  }

  async handleSetReminder(taskId) {
    const date = document.getElementById('reminder-date').value;
    const time = document.getElementById('reminder-time').value;

    if (!date || !time) {
      this.showError('Both date and time are required');
      return;
    }

    const reminderTime = new Date(`${date}T${time}`);
    if (reminderTime < new Date()) {
      this.showError('Reminder time must be in the future');
      return;
    }

    const reminderData = {
      reminder_time: reminderTime.toISOString()
    };

    await this.setReminder(taskId, reminderData);
    document.querySelector('.dialog-overlay').remove();
  }

  // Helper methods
  async getAuthHeader() {
    const { access_token } = await chrome.storage.local.get(['access_token']);
    return `Bearer ${access_token}`;
  }

  async getAuthToken() {
    try {
      const response = await chrome.runtime.sendMessage({ action: 'getAuthToken' });
      if (!response || !response.token) {
        console.log('No auth token found, initiating OAuth...');
        await chrome.runtime.sendMessage({ action: 'initiate_oauth' });
        // Try getting token again after OAuth
        const newResponse = await chrome.runtime.sendMessage({ action: 'getAuthToken' });
        return newResponse?.token;
      }
      return response.token;
    } catch (error) {
      console.error('Error getting auth token:', error);
      throw error;
    }
  }

  showError(message) {
    this.showToast(message, 'error');
  }

  showSuccess(message) {
    this.showToast(message, 'success');
  }

  showToast(message, type) {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);

    setTimeout(() => {
      toast.remove();
    }, 3000);
  }

  // Email processing methods
  setupEmailObserver() {
    const emailObserver = new MutationObserver(() => {
      this.detectCurrentEmail();
    });
    
    emailObserver.observe(document.body, {
      childList: true,
      subtree: true
    });
  }

  async extractTasksFromEmail() {
    try {
      // Get current email content
      const emailContent = this.getCurrentEmailContent();
      if (!emailContent) {
        console.log('No email content found');
        return;
      }

      // Get auth token first
      const token = await this.getAuthToken();
      if (!token) {
        console.error('No auth token available');
        this.showError('Please login first');
        return;
      }

      console.log('Extracting tasks from email...');
      const response = await fetch(`${API_BASE_URL}/api/extract`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
          'Accept': 'application/json'
        },
        credentials: 'include',
        body: JSON.stringify({
          content: emailContent,
          email_id: this.getCurrentEmailId()
        })
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      console.log('Extracted tasks:', result);
      this.displayExtractedTasks(result.tasks, result.suggested_reply);
    } catch (error) {
      console.error('Error extracting tasks:', error);
      this.showError(error.message || 'Failed to extract tasks. Please try again.');
    }
  }

  getCurrentEmailContent() {
    try {
      // Try different Gmail selectors for email content
      const selectors = [
        '.a3s.aiL', // Primary content
        '.ii.gt', // Alternative content
        '.gE.iv.gt', // Another possible content area
        '.adP.adO > div[dir="ltr"]', // Direct message content
        '.gmail_quote', // Quoted content
      ];

      let content = '';
      
      // Try each selector and combine content
      for (const selector of selectors) {
        const element = document.querySelector(selector);
        if (element && element.textContent.trim()) {
          content += element.textContent.trim() + '\n';
        }
      }

      // If no content found through selectors, try getting the entire email body
      if (!content) {
        const emailBody = document.querySelector('.gs');
        if (emailBody) {
          content = emailBody.textContent.trim();
        }
      }

      if (!content) {
        console.error('No email content found');
        return null;
      }

      return content;
    } catch (error) {
      console.error('Error getting email content:', error);
      return null;
    }
  }

  getCurrentEmailId() {
    try {
      // Get ID from URL
      const url = window.location.href;
      const match = url.match(/#inbox\/([^/]+)/);
      if (match) return match[1];

      // Alternative: try data attribute
      const emailContainer = document.querySelector('[data-message-id]');
      if (emailContainer) return emailContainer.getAttribute('data-message-id');

      console.error('No email ID found');
      return null;
    } catch (error) {
      console.error('Error getting email ID:', error);
      return null;
    }
  }

  displayExtractedTasks(tasks, suggestedReply) {
    const extractTab = this.panel.querySelector('#extract-tab');
    const tasksContainer = extractTab.querySelector('.extracted-tasks');
    
    if (!tasks || tasks.length === 0) {
      tasksContainer.innerHTML = '<div class="no-tasks">No tasks found in this email.</div>';
      return;
    }

    let html = tasks.map(task => `
      <div class="task-item" data-task-id="${task.id}">
        <div class="task-header">
          <div class="task-content">${task.title || task.description || task.content || 'No content'}</div>
          <div class="task-priority ${task.priority || 'medium'}">${task.priority || 'medium'}</div>
        </div>
        ${task.due_date ? `<div class="task-due-date">Due: ${new Date(task.due_date).toLocaleDateString()}</div>` : ''}
        <div class="task-actions">
          <button class="action-button confirm-task" data-task-id="${task.id}">Confirm</button>
          <button class="action-button reject-task" data-task-id="${task.id}">Reject</button>
          <select class="assign-select" data-task-id="${task.id}">
            <option value="">Assign to...</option>
            ${this.teamMembers?.map(member => `
              <option value="${member.id}">${member.name}</option>
            `).join('') || ''}
          </select>
        </div>
      </div>
    `).join('');

    // Add suggested reply section if available
    if (suggestedReply) {
      html += `
        <div class="suggested-reply-section">
          <h4>Suggested Reply:</h4>
          <div class="reply-content">${suggestedReply}</div>
          <button class="action-button compose-reply">Add to Compose</button>
        </div>
      `;
    }

    tasksContainer.innerHTML = html;

    // Add click handler for compose reply button
    const composeBtn = tasksContainer.querySelector('.compose-reply');
    if (composeBtn) {
      composeBtn.addEventListener('click', () => this.addToCompose(suggestedReply));
    }
  }

  addToCompose(replyText) {
    // Click Gmail's reply button
    const replyButton = document.querySelector('div[data-tooltip="Reply"]');
    if (replyButton) {
      replyButton.click();
      
      // Wait for reply window to open and add text
      setTimeout(() => {
        const messageBody = document.querySelector('div[aria-label="Message Body"]');
        if (messageBody) {
          messageBody.innerHTML = replyText;
        }
      }, 500);
    }
  }

  async confirmTask(taskId) {
    try {
      const response = await fetch(`http://localhost:8000/api/tasks/${taskId}/confirm`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${await this.getAuthToken()}`
        }
      });

      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
      
      // Remove or update the task in UI
      const taskElement = this.panel.querySelector(`[data-task-id="${taskId}"]`).closest('.task-item');
      taskElement.classList.add('confirmed');
      setTimeout(() => taskElement.remove(), 500);
    } catch (error) {
      console.error('Error confirming task:', error);
      this.showError('Failed to confirm task. Please try again.');
    }
  }

  async rejectTask(taskId) {
    try {
      const response = await fetch(`http://localhost:8000/api/tasks/${taskId}/reject`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${await this.getAuthToken()}`
        }
      });

      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
      
      // Remove the task from UI
      const taskElement = this.panel.querySelector(`[data-task-id="${taskId}"]`).closest('.task-item');
      taskElement.classList.add('rejected');
      setTimeout(() => taskElement.remove(), 500);
    } catch (error) {
      console.error('Error rejecting task:', error);
      this.showError('Failed to reject task. Please try again.');
    }
  }

  showError(message) {
    // Add error message to the panel
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error-message';
    errorDiv.textContent = message;
    
    this.panel.querySelector('.assistant-content').prepend(errorDiv);
    setTimeout(() => errorDiv.remove(), 3000);
  }

  setupAssistantPanel() {
    const panel = document.createElement('div');
    panel.className = 'assistant-panel hidden';
    panel.innerHTML = `
      <div class="assistant-header">
        <div class="brand-section">
          <div class="brand-icon">
            <svg viewBox="0 0 24 24">
              <path d="M20.5 3l-.16.03L15 5.1 9 3 3.36 4.9c-.21.07-.36.25-.36.48V20.5c0 .28.22.5.5.5l.16-.03L9 18.9l6 2.1 5.64-1.9c.21-.07.36-.25.36-.48V3.5c0-.28-.22-.5-.5-.5z"/>
            </svg>
          </div>
          <div class="brand-title">Gmail Assistant</div>
        </div>
        <div class="header-tabs">
          <button class="tab-button active" data-tab="tasks">Tasks & Reminders</button>
          <button class="tab-button" data-tab="team">Team</button>
          <button class="tab-button" data-tab="extract">Extract Tasks</button>
        </div>
        <div class="header-actions">
          <button class="toggle-button" title="Toggle panel">
            <svg viewBox="0 0 24 24">
              <path fill="currentColor" d="M8.59 16.59L13.17 12 8.59 7.41 10 6l6 6-6 6-1.41-1.41z"/>
            </svg>
          </button>
          <button class="close-button" title="Close panel">×</button>
        </div>
      </div>
      <div class="assistant-content">
        <div class="tab-content active" id="tasks-tab">
          <div class="tasks-list">
            <!-- Tasks will be populated here -->
          </div>
        </div>
        <div class="tab-content" id="team-tab">
          <div class="team-members">
            <!-- Team members will be populated here -->
          </div>
        </div>
        <div class="tab-content" id="extract-tab">
          <div class="action-buttons">
            <button class="action-button" id="extract-tasks">Extract Tasks from Email</button>
          </div>
          <div class="extracted-tasks">
            <!-- Extracted tasks will appear here -->
          </div>
        </div>
      </div>
    `;

    document.body.appendChild(panel);
    this.panel = panel;

    // Setup extract button handler
    const extractBtn = panel.querySelector('#extract-tasks');
    if (extractBtn) {
      extractBtn.addEventListener('click', async () => {
        if (!this.currentEmail) {
          this.showError('No email selected');
          return;
        }
        await this.processCurrentEmail();
      });
    }

    // Setup tab switching
    const tabButtons = panel.querySelectorAll('.tab-button');
    tabButtons.forEach(button => {
      button.addEventListener('click', () => {
        const tabName = button.getAttribute('data-tab');
        
        // Update button states
        tabButtons.forEach(btn => btn.classList.remove('active'));
        button.classList.add('active');
        
        // Update tab content
        const tabContents = panel.querySelectorAll('.tab-content');
        tabContents.forEach(content => content.classList.remove('active'));
        panel.querySelector(`#${tabName}-tab`).classList.add('active');
      });
    });

    // Toggle button
    panel.querySelector('.toggle-button').addEventListener('click', () => {
      panel.classList.toggle('collapsed');
    });

    // Close button
    panel.querySelector('.close-button').addEventListener('click', () => {
      panel.classList.add('hidden');
    });
  }

  async loadTasks() {
    try {
      const response = await chrome.runtime.sendMessage({ action: 'fetch', endpoint: '/api/tasks', options: { method: 'GET' } });

      if (response.ok) {
        const tasksList = this.panel.querySelector('.tasks-list');
        tasksList.innerHTML = response.data.tasks.map(task => `
          <div class="task-item">
            <div class="task-content">${task.title}</div>
            <div class="task-due-date">${task.due_date || ''}</div>
          </div>
        `).join('');
      }
    } catch (error) {
      console.error('Failed to load tasks:', error);
    }
  }

  async loadTeamMembers() {
    try {
      const response = await chrome.runtime.sendMessage({ action: 'fetch', endpoint: '/api/team/members', options: { method: 'GET' } });

      if (response.ok) {
        const teamList = this.panel.querySelector('.team-members');
        teamList.innerHTML = response.data.members.map(member => `
          <div class="team-member">
            <div class="member-name">${member.name}</div>
            <div class="member-email">${member.email}</div>
          </div>
        `).join('');
        this.teamMembers = response.data.members;
      }
    } catch (error) {
      console.error('Failed to load team members:', error);
    }
  }
}

// Initialize immediately
console.log('Content script loaded, creating Gmail Assistant...');
new GmailAssistant();
