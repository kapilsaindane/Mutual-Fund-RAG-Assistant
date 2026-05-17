// Phase 6 Frontend JavaScript - Groww FAQ Assistant (Dark Theme)

class MutualFundAssistant {
    constructor() {
        this.apiBaseUrl = 'http://localhost:5000/api';
        this.uiData = null;
        this.isProcessing = false;
        
        this.init();
    }
    
    async init() {
        this.bindEvents();
        await this.loadUIData();
        await this.checkSystemStatus();
        this.setCurrentTime();
    }
    
    bindEvents() {
        // Example question buttons
        document.querySelectorAll('.example-question').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const query = e.target.closest('[data-query]').dataset.query;
                this.setQuery(query);
                this.submitQuery();
            });
        });
        
        // Submit button
        document.getElementById('submitBtn').addEventListener('click', () => {
            this.submitQuery();
        });
        
        // Clear button
        document.getElementById('clearBtn').addEventListener('click', () => {
            this.clearQuery();
        });
        
        // Query input events
        const queryInput = document.getElementById('queryInput');
        queryInput.addEventListener('input', () => {
            this.updateCharCount();
            this.updateSubmitButton();
        });
        
        queryInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && e.ctrlKey) {
                e.preventDefault();
                this.submitQuery();
            }
        });
        
        // Popular topic buttons
        document.querySelectorAll('.text-primary').forEach(btn => {
            if (btn.textContent.includes('Tax implications') || 
                btn.textContent.includes('SIP vs Lumpsum') || 
                btn.textContent.includes('Redemption rules')) {
                btn.addEventListener('click', () => {
                    const topic = btn.textContent.trim();
                    this.setQuery(`Tell me about ${topic.toLowerCase()} for mutual funds`);
                    this.submitQuery();
                });
            }
        });
    }
    
    async loadUIData() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/ui-data`);
            if (!response.ok) {
                throw new Error('Failed to load UI data');
            }
            
            this.uiData = await response.json();
            this.updateUIWithData();
        } catch (error) {
            console.error('Error loading UI data:', error);
            // Use fallback data
            this.uiData = this.getFallbackUIData();
            this.updateUIWithData();
        }
    }
    
    updateUIWithData() {
        if (!this.uiData) return;
        
        // Update welcome message
        const welcomeMessage = document.querySelector('.font-h3.text-h3');
        if (welcomeMessage && this.uiData.welcome_message) {
            welcomeMessage.textContent = this.uiData.welcome_message;
        }
        
        // Update disclaimer
        const disclaimerElements = document.querySelectorAll('.font-label-caps.text-label-caps');
        disclaimerElements.forEach(el => {
            if (this.uiData.disclaimer) {
                el.textContent = this.uiData.disclaimer;
            }
        });
        
        // Update example questions
        const exampleButtons = document.querySelectorAll('[data-query]');
        if (this.uiData.example_questions && this.uiData.example_questions.length > 0) {
            exampleButtons.forEach((btn, index) => {
                if (index < this.uiData.example_questions.length) {
                    btn.dataset.query = this.uiData.example_questions[index];
                    const textSpan = btn.querySelector('.font-body-md.text-body-md');
                    if (textSpan) {
                        textSpan.textContent = this.uiData.example_questions[index];
                    }
                }
            });
        }
    }
    
    getFallbackUIData() {
        return {
            welcome_message: 'Welcome to Groww FAQ Assistant',
            disclaimer: 'Facts-only. No investment advice.',
            example_questions: [
                'What is expense ratio of SBI Bluechip Fund?',
                'What is minimum SIP amount for SBI Bluechip Fund?',
                'What is lock-in period for SBI Bluechip Fund?'
            ],
            system_status: {
                orchestrator: 'unknown',
                groq_available: false,
                retrieval_available: false
            }
        };
    }
    
    async checkSystemStatus() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/../health`);
            const status = await response.json();
            
            this.updateSystemStatus(status);
        } catch (error) {
            console.error('Error checking system status:', error);
            this.updateSystemStatus({ status: 'offline' });
        }
    }
    
    updateSystemStatus(status) {
        const statusIndicator = document.getElementById('statusIndicator');
        const statusText = document.getElementById('statusText');
        
        if (status.status === 'healthy') {
            statusIndicator.className = 'status-indicator online';
            statusText.textContent = 'System online';
        } else {
            statusIndicator.className = 'status-indicator offline';
            statusText.textContent = 'System offline';
        }
    }
    
    setQuery(query) {
        const queryInput = document.getElementById('queryInput');
        queryInput.value = query;
        this.updateCharCount();
        this.updateSubmitButton();
        queryInput.focus();
    }
    
    clearQuery() {
        const queryInput = document.getElementById('queryInput');
        queryInput.value = '';
        this.updateCharCount();
        this.updateSubmitButton();
        this.hideResponse();
        this.hideError();
        queryInput.focus();
    }
    
    updateCharCount() {
        const queryInput = document.getElementById('queryInput');
        const charCount = document.getElementById('charCount');
        const currentLength = queryInput.value.length;
        charCount.textContent = currentLength;
        
        if (currentLength > 450) {
            charCount.style.color = '#f56565';
        } else if (currentLength > 400) {
            charCount.style.color = '#ed8936';
        } else {
            charCount.style.color = '#9ca3af';
        }
    }
    
    updateSubmitButton() {
        const queryInput = document.getElementById('queryInput');
        const submitBtn = document.getElementById('submitBtn');
        const hasQuery = queryInput.value.trim().length > 0;
        submitBtn.disabled = !hasQuery || this.isProcessing;
    }
    
    async submitQuery() {
        if (this.isProcessing) return;
        
        const queryInput = document.getElementById('queryInput');
        const query = queryInput.value.trim();
        
        if (!query) return;
        
        this.isProcessing = true;
        this.updateSubmitButton();
        this.hideResponse();
        this.hideError();
        this.showProcessing();
        this.addUserMessage(query);
        
        try {
            const response = await fetch(`${this.apiBaseUrl}/query`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    query: query,
                    method: 'auto',
                    show_steps: false,
                    save_logs: false
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const result = await response.json();
            this.displayResponse(result);
            
        } catch (error) {
            console.error('Error submitting query:', error);
            this.showError(error.message);
        } finally {
            this.isProcessing = false;
            this.updateSubmitButton();
            this.hideProcessing();
        }
    }
    
    showProcessing() {
        const submitBtn = document.getElementById('submitBtn');
        const btnText = submitBtn.querySelector('.material-symbols-outlined');
        const arrowIcon = submitBtn.querySelector('[data-icon="arrow_upward"]');
        
        if (btnText) btnText.style.display = 'none';
        if (arrowIcon) arrowIcon.style.display = 'inline-block';
    }
    
    hideProcessing() {
        const submitBtn = document.getElementById('submitBtn');
        const btnText = submitBtn.querySelector('.material-symbols-outlined');
        const arrowIcon = submitBtn.querySelector('[data-icon="arrow_upward"]');
        
        if (btnText) btnText.style.display = 'inline-block';
        if (arrowIcon) arrowIcon.style.display = 'none';
    }
    
    addUserMessage(query) {
        const userMessage = document.getElementById('userMessage');
        const messageTime = document.getElementById('messageTime');
        
        if (userMessage) {
            userMessage.textContent = query;
        }
        if (messageTime) {
            messageTime.textContent = this.getCurrentTime();
        }
        
        // Show user message section
        const chatHistory = document.getElementById('chatHistory');
        if (chatHistory) {
            chatHistory.style.display = 'flex';
        }
    }
    
    displayResponse(result) {
        const botResponse = document.getElementById('botResponse');
        const answerText = document.getElementById('answerText');
        const responseMeta = document.getElementById('responseMeta');
        const sourceLink = document.getElementById('sourceLink');
        const sourceText = document.getElementById('sourceText');
        const lastUpdated = document.getElementById('lastUpdated');
        
        if (!botResponse || !answerText || !responseMeta) return;
        
        // Show bot response
        botResponse.style.display = 'flex';
        
        // Set response text
        if (answerText && result.response) {
            answerText.textContent = result.response;
        }
        
        // Show metadata if available
        if (responseMeta && result.ui_data) {
            const uiData = result.ui_data;
            
            // Show source link
            if (uiData.source_url && sourceLink && sourceText) {
                sourceLink.href = uiData.source_url;
                sourceLink.style.display = 'flex';
                sourceText.textContent = `Source: ${this.formatSourceUrl(uiData.source_url)}`;
            }
            
            // Show last updated
            if (uiData.last_updated && lastUpdated) {
                lastUpdated.textContent = `Last updated from sources: ${uiData.last_updated}`;
                lastUpdated.parentElement.style.display = 'flex';
            }
            
            responseMeta.style.display = 'block';
        }
        
        // Auto-scroll to response
        if (botResponse) {
            botResponse.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
    }
    
    hideResponse() {
        const botResponse = document.getElementById('botResponse');
        const responseMeta = document.getElementById('responseMeta');
        
        if (botResponse) {
            botResponse.style.display = 'none';
        }
        if (responseMeta) {
            responseMeta.style.display = 'none';
        }
    }
    
    showError(message) {
        const errorSection = document.getElementById('errorSection');
        const errorMessage = document.getElementById('errorMessage');
        
        if (errorSection && errorMessage) {
            errorMessage.textContent = message || 'An error occurred while processing your request.';
            errorSection.style.display = 'block';
            errorSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
    }
    
    hideError() {
        const errorSection = document.getElementById('errorSection');
        if (errorSection) {
            errorSection.style.display = 'none';
        }
    }
    
    formatSourceUrl(url) {
        try {
            const urlObj = new URL(url);
            return urlObj.hostname;
        } catch {
            return url;
        }
    }
    
    getCurrentTime() {
        const now = new Date();
        return now.toLocaleTimeString('en-US', { 
            hour: '2-digit', 
            minute: '2-digit',
            hour12: true 
        });
    }
    
    setCurrentTime() {
        const messageTime = document.getElementById('messageTime');
        if (messageTime) {
            messageTime.textContent = this.getCurrentTime();
        }
    }
}

// Initialize application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new MutualFundAssistant();
});

// Handle page visibility changes to refresh system status
document.addEventListener('visibilitychange', () => {
    if (!document.hidden && window.mutualFundAssistant) {
        window.mutualFundAssistant.checkSystemStatus();
    }
});
