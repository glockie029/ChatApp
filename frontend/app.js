// DOM Elements
const messagesBox = document.getElementById('messagesBox');
const messageForm = document.getElementById('messageForm');
const messageInput = document.getElementById('messageInput');
const usernameInput = document.getElementById('usernameInput');
const apiUrlInput = document.getElementById('apiUrl');
const aesKeyInput = document.getElementById('aesKeyInput');
const sendBtn = document.getElementById('sendBtn');
const refreshBtn = document.getElementById('refreshBtn');
const loadingSpinner = document.getElementById('loadingSpinner');
const toast = document.getElementById('toast');
const toastMessage = document.getElementById('toastMessage');

// State
let isFetching = false;
let lastMessageCount = 0;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    // Attempt to load saved config from localStorage
    const savedApi = localStorage.getItem('chatApiUrl');
    const savedName = localStorage.getItem('chatUsername');
    const savedAesKey = localStorage.getItem('chatAesKey');
    
    if (savedApi) {
        apiUrlInput.value = savedApi;
    } else {
        // Automatically adapt to the local or public IP
        const host = window.location.hostname || '127.0.0.1';
        apiUrlInput.value = `http://${host}:8000`;
    }
    
    if (savedName) usernameInput.value = savedName;
    if (savedAesKey) aesKeyInput.value = savedAesKey;

    // Save configurations on blur/change
    apiUrlInput.addEventListener('change', () => {
        localStorage.setItem('chatApiUrl', apiUrlInput.value.trim());
        fetchMessages();
    });
    
    usernameInput.addEventListener('change', () => {
        localStorage.setItem('chatUsername', usernameInput.value.trim() || 'Anonymous');
    });

    aesKeyInput.addEventListener('change', () => {
        localStorage.setItem('chatAesKey', aesKeyInput.value.trim());
        // Re-render when key changes to attempt decryption
        messagesBox.innerHTML = '';
        lastMessageCount = 0;
        fetchMessages();
    });

    // Event Listeners
    messageForm.addEventListener('submit', handleFormSubmit);
    refreshBtn.addEventListener('click', () => {
        refreshBtn.querySelector('i').classList.add('fa-spin');
        fetchMessages().then(() => {
            setTimeout(() => refreshBtn.querySelector('i').classList.remove('fa-spin'), 500);
        });
    });

    // Paste event listener for images
    document.addEventListener('paste', handlePaste);

    // Auto-fetch periodically
    fetchMessages();
    setInterval(fetchMessagesSilently, 5000); // Polling every 5 seconds
});

// Helper: Show Toast Notification
function showToast(msg, isError = false) {
    toastMessage.textContent = msg;
    toast.className = `toast show ${isError ? 'error' : ''}`;
    
    setTimeout(() => {
        toast.className = 'toast hidden';
    }, 3000);
}

// Helper: Format Time
function formatTime(isoString) {
    const date = new Date(isoString);
    const today = new Date();
    
    if (date.toDateString() === today.toDateString()) {
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }
    return date.toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
}

// AES Crypto Wrappers
function encryptContent(plaintext) {
    const secret = aesKeyInput.value.trim();
    if (!secret) return plaintext; // Fallback to plaintext if no key
    const ciphertext = CryptoJS.AES.encrypt(plaintext, secret).toString();
    return `[AES]:${ciphertext}`; // add a prefix marker
}

function decryptContent(rawText) {
    if (!rawText.startsWith('[AES]:')) return { text: rawText, error: false }; // Was sent unencrypted
    
    const secret = aesKeyInput.value.trim();
    if (!secret) return { text: null, error: true, msg: '需配置密钥才能解密' };
    
    const ciphertext = rawText.substring(6);
    try {
        const bytes = CryptoJS.AES.decrypt(ciphertext, secret);
        const originalText = bytes.toString(CryptoJS.enc.Utf8);
        if (!originalText) throw new Error("Incorrect key");
        return { text: originalText, error: false };
    } catch (err) {
        return { text: null, error: true, msg: '🔐 密钥错误，解密失败' };
    }
}

// Image Paste Handler
function handlePaste(e) {
    // Only capture paste if they aren't typing in an input field right now (or if it's the messageInput)
    // Actually we support pasting anywhere on the document since it's a chat app!
    const items = (e.clipboardData || e.originalEvent.clipboardData).items;
    let imageFound = false;
    for (const item of items) {
        if (item.type.indexOf('image') !== -1) {
            imageFound = true;
            const blob = item.getAsFile();
            const reader = new FileReader();
            reader.onload = function(event) {
                const base64Data = event.target.result;
                const imagePayload = `[IMAGE]:${base64Data}`;
                
                if (confirm("是否发送提取到的剪贴板图片?")) {
                    sendRawMessage(imagePayload);
                }
            };
            reader.readAsDataURL(blob);
            break; // take first image
        }
    }
}

// Fetch Messages Displaying Spinner (Manual Refresh)
async function fetchMessages() {
    if (isFetching) return;
    isFetching = true;
    loadingSpinner.classList.add('active');
    messagesBox.innerHTML = ''; // clear for loading
    messagesBox.appendChild(loadingSpinner);
    
    await performFetch();
    loadingSpinner.classList.remove('active');
    isFetching = false;
}

// Silent Fetch (Polling)
async function fetchMessagesSilently() {
    if (isFetching) return;
    await performFetch(true);
}

// Core Fetch Logic
async function performFetch(silent = false) {
    const baseUrl = apiUrlInput.value.trim().replace(/\/$/, "");
    if (!baseUrl) return;

    try {
        const response = await fetch(`${baseUrl}/messages/?limit=50`);
        if (!response.ok) throw new Error('API Response not ok');
        
        const data = await response.json();
        
        // Reverse array because API returns latest first, but chat UI needs oldest top, latest bottom
        const messages = data.reverse();
        
        renderMessages(messages, silent);
    } catch (error) {
        console.error("Fetch error:", error);
        if (!silent) {
            renderEmptyState(true);
            showToast("Failed to connect to API", true);
        }
    }
}

// Render Messages to DOM
function renderMessages(messages, silent = false) {
    if (!messages || messages.length === 0) {
        if (!silent) renderEmptyState();
        return;
    }

    if (silent && messages.length === lastMessageCount) {
        return; 
    }

    lastMessageCount = messages.length;
    const currentUser = usernameInput.value.trim() || 'Anonymous';
    const fragment = document.createDocumentFragment();

    messages.forEach(msg => {
        const isSelf = msg.username === currentUser;
        
        const msgDiv = document.createElement('div');
        msgDiv.className = `message ${isSelf ? 'self' : ''}`;
        
        const initial = (msg.username && msg.username.length > 0) ? msg.username.charAt(0).toUpperCase() : '?';
        
        const avatarDiv = document.createElement('div');
        avatarDiv.className = 'msg-avatar';
        avatarDiv.textContent = initial;
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'msg-content';
        
        const headerDiv = document.createElement('div');
        headerDiv.className = 'msg-header';
        
        const authorSpan = document.createElement('span');
        authorSpan.className = 'msg-author';
        authorSpan.textContent = msg.username;
        
        const timeSpan = document.createElement('span');
        timeSpan.className = 'msg-time';
        timeSpan.textContent = formatTime(msg.created_at);
        
        headerDiv.appendChild(authorSpan);
        headerDiv.appendChild(timeSpan);
        
        const bubbleDiv = document.createElement('div');
        bubbleDiv.className = 'msg-bubble';
        
        // ---- Decryption Check ----
        const decrypted = decryptContent(msg.content);
        
        if (decrypted.error) {
            bubbleDiv.innerHTML = `<span class="crypto-error"><i class="fa-solid fa-lock"></i> ${decrypted.msg}</span>`;
            bubbleDiv.style.borderColor = 'var(--danger)'; 
            if(isSelf) bubbleDiv.style.backgroundColor = 'var(--danger)';
        } else {
            // Check if it's an image payload
            if (decrypted.text && decrypted.text.startsWith('[IMAGE]:')) {
                const b64 = decrypted.text.substring(8);
                const img = document.createElement('img');
                img.src = b64;
                img.className = 'msg-image';
                
                // Add click to view full size basic implementation
                img.onclick = () => {
                    const w = window.open("");
                    w.document.write(`<img src="${b64}" style="max-width:100%;">`);
                }
                bubbleDiv.appendChild(img);
            } else {
                bubbleDiv.textContent = decrypted.text; // Text node prevents XSS
            }
        }
        
        contentDiv.appendChild(headerDiv);
        contentDiv.appendChild(bubbleDiv);
        
        msgDiv.appendChild(avatarDiv);
        msgDiv.appendChild(contentDiv);
        
        fragment.appendChild(msgDiv);
    });

    messagesBox.innerHTML = '';
    messagesBox.appendChild(fragment);
    scrollToBottom();
}

function renderEmptyState(isError = false) {
    messagesBox.innerHTML = `
        <div class="empty-state">
            <i class="fa-solid fa-ghost"></i>
            <p>${isError ? 'Cannot connect to Server.' : 'No messages yet. Be the first to say hi!'}</p>
        </div>
    `;
}

function scrollToBottom() {
    messagesBox.scrollTop = messagesBox.scrollHeight;
}

// Form Submit Handler
function handleFormSubmit(e) {
    e.preventDefault();
    const content = messageInput.value.trim();
    if (!content) return;
    
    // Clear input
    messageInput.value = '';
    
    if (!aesKeyInput.value.trim()) {
        showToast("⚠️ 保护隐私请先在左侧设置群组密码 (AES Key)", true);
        return; // Optional: Force users to set a key
    }

    sendRawMessage(content);
}

// Actually POST the message to backend
async function sendRawMessage(rawContent) {
    const baseUrl = apiUrlInput.value.trim().replace(/\/$/, "");
    if (!baseUrl) {
        showToast("Please configure API URL", true);
        return;
    }

    sendBtn.disabled = true;
    sendBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';

    try {
        // ENCRYPT
        const finalContent = encryptContent(rawContent);

        const payload = {
            content: finalContent,
            username: usernameInput.value.trim() || 'Anonymous'
        };

        const response = await fetch(`${baseUrl}/messages/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            // E.g., validation error if payload too big and backend didn't update max_length
            const errBody = await response.text();
            throw new Error(`HTTP error! status: ${response.status}. ${errBody}`);
        }

        // Fetch new message list instantly
        await performFetch();
        
    } catch (error) {
        console.error("Send error:", error);
        showToast("Failed to send message: " + error.message, true);
    } finally {
        sendBtn.disabled = false;
        sendBtn.innerHTML = '<i class="fa-solid fa-paper-plane"></i>';
        messageInput.focus();
    }
}
