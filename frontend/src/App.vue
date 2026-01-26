<script setup>
import { ref, onMounted } from 'vue';
import Sidebar from './components/Sidebar.vue';
import ChatBox from './components/ChatBox.vue';
import ChatInput from './components/ChatInput.vue';
import ModelSelector from './components/ModelSelector.vue';
import Login from './components/Login.vue';
import Register from './components/Register.vue';
import { authService } from './utils/auth';
import { appConfig } from './config/appConfig';
import { Marked } from 'marked';
import { markedHighlight } from "marked-highlight";
import hljs from 'highlight.js';
import 'highlight.js/styles/github-dark.css';

const currentUser = ref(null);
const authPage = ref('login'); // 'login' or 'register'

const currentSessionId = ref(null);
const messages = ref([]);
const sessions = ref([]);
const providers = ref([]);
const modelConfig = ref({
    providerID: '',
    modelID: '',
    mode: 'plan'
});
const isHistoryCollapsed = ref(false);
const isTyping = ref(false);

const handleLoginSuccess = (user) => {
    currentUser.value = user;
    loadHistory();
    loadConfig();
};

const handleLogout = () => {
    authService.logout();
    currentUser.value = null;
    currentSessionId.value = null;
    messages.value = [];
    authPage.value = 'login';
};

const appendMessage = (text, sender, timestamp, providerID, modelID) => {
    messages.value.push({
        text,
        sender,
        timestamp: timestamp || new Date().toISOString(),
        providerID,
        modelID
    });
};

const loadConfig = async () => {
    try {
        const response = await fetch('/api/config/providers');
        const data = await response.json();
        providers.value = data;
        
        // Set default values from first available provider/model if not set
        if (providers.value.length > 0) {
            const firstProvider = providers.value[0];
            modelConfig.value.providerID = firstProvider.id;
            if (firstProvider.models) {
                const models = Object.keys(firstProvider.models);
                if (models.length > 0) {
                    modelConfig.value.modelID = models[0];
                }
            }
        }
    } catch (error) {
        console.error('Error loading config:', error);
    }
};

const loadHistory = async () => {
    if (!currentUser.value) return;
    
    try {
        const response = await fetch(`/api/sessions?username=${encodeURIComponent(currentUser.value.username)}`);
        const data = await response.json();
        sessions.value = data;
    } catch (error) {
        console.error('Error loading history:', error);
    }
};

const handleNewChat = () => {
    currentSessionId.value = null;
    messages.value = [{
        text: appConfig.assistant.welcomeMessage,
        sender: 'assistant',
        timestamp: new Date().toISOString(),
        providerID: '',
        modelID: 'System'
    }];
};

const handleSelectSession = async (sessionId) => {
    if (sessionId === currentSessionId.value) return;
    
    currentSessionId.value = sessionId;
    messages.value = [];
    
    try {
        const response = await fetch(`/api/sessions/${sessionId}/messages`);
        const data = await response.json();
        
        if (Array.isArray(data)) {
            messages.value = data;
        }
    } catch (error) {
        console.error('Error loading session messages:', error);
        appendMessage('**系统错误：** 无法加载会话历史。', 'assistant');
    }
};

const handleSendMessage = async (message) => {
    if (!message.trim()) return;

    appendMessage(message, 'user');
    isTyping.value = true;

    try {
        // Store the config used for this message
        const currentProviderID = modelConfig.value.providerID;
        const currentModelID = modelConfig.value.modelID;

        // Lazy session initialization
        if (!currentSessionId.value) {
            const sessionResp = await fetch('/api/sessions', { 
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    username: currentUser.value.username,
                    title: appConfig.assistant.defaultSessionTitle 
                })
            });
            const sessionData = await sessionResp.json();
            if (sessionData.id) {
                currentSessionId.value = sessionData.id;
                loadHistory();
            } else {
                throw new Error(sessionData.error || 'Failed to create session');
            }
        }

        const response = await fetch(`/api/sessions/${currentSessionId.value}/messages`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                providerID: currentProviderID,
                modelID: currentModelID,
                message: message
            }),
        });

        const data = await response.json();
        if (data.text) {
            appendMessage(data.text, 'assistant', data.timestamp, data.providerID, data.modelID);
        } else if (data.error) {
            throw new Error(data.error);
        } else {
            throw new Error('Unexpected response format from server');
        }
    } catch (error) {
        console.error('Error sending message:', error);
        appendMessage('**系统错误：** ' + (error.message || '无法连接到后端服务器'), 'assistant');
    } finally {
        isTyping.value = false;
    }
};

const handleRenameSession = async (session) => {
    const newTitle = prompt('请输入新的会话标题：', session.title);
    if (newTitle === null || newTitle.trim() === '' || newTitle === session.title) return;

    try {
        const response = await fetch(`/api/sessions/${session.id}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title: newTitle.trim() })
        });
        
        if (response.ok) {
            loadHistory();
        } else {
            alert('重命名失败，请稍后重试。');
        }
    } catch (error) {
        console.error('Error renaming session:', error);
        alert('系统错误：无法重命名会话。');
    }
};

const handleDeleteSession = async (session) => {
    if (!confirm('确定要删除这个会话吗？此操作不可撤销。')) return;

    try {
        const response = await fetch(`/api/sessions/${session.id}?username=${encodeURIComponent(currentUser.value.username)}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            if (session.id === currentSessionId.value) {
                handleNewChat();
            }
            loadHistory();
        } else {
            alert('删除失败，请稍后重试。');
        }
    } catch (error) {
        console.error('Error deleting session:', error);
        alert('系统错误：无法删除会话。');
    }
};

const handleExportHTML = () => {
    if (messages.value.length === 0) {
        alert('当前没有对话内容可以导出。');
        return;
    }

    const currentSession = sessions.value.find(s => s.id === currentSessionId.value);
    const sessionTitle = currentSession ? currentSession.title : '当前对话';

    const marked = new Marked(
        markedHighlight({
            langPrefix: 'hljs language-',
            highlight(code, lang) {
                const language = hljs.getLanguage(lang) ? lang : 'plaintext';
                return hljs.highlight(code, { language }).value;
            }
        })
    );

    let htmlContent = `
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>${sessionTitle} - 对话导出</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github-dark.min.css">
    <style>
        :root {
            --primary: #0F172A;
            --background: #F8FAFC;
            --text-primary: #020617;
            --text-secondary: #475569;
            --message-user: #0369A1;
            --message-assistant: #F1F5F9;
            --border: #E2E8F0;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            line-height: 1.6;
            color: var(--text-primary);
            background-color: var(--background);
            max-width: 900px;
            margin: 0 auto;
            padding: 40px 20px;
        }
        .header {
            margin-bottom: 40px;
            text-align: center;
            border-bottom: 1px solid var(--border);
            padding-bottom: 20px;
        }
        .message {
            margin-bottom: 24px;
            display: flex;
            flex-direction: column;
        }
        .message-content {
            padding: 12px 20px;
            border-radius: 16px;
            max-width: 85%;
            word-wrap: break-word;
        }
        .user { align-items: flex-end; }
        .user .message-content {
            background-color: var(--message-user);
            color: white;
            border-bottom-right-radius: 4px;
            white-space: pre-wrap;
        }
        .assistant { align-items: flex-start; }
        .assistant .message-content {
            background-color: var(--message-assistant);
            color: var(--text-primary);
            border-bottom-left-radius: 4px;
            border: 1px solid var(--border);
        }
        .meta {
            font-size: 0.75rem;
            color: var(--text-secondary);
            margin-top: 4px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .model-tag {
            background: rgba(0, 0, 0, 0.05);
            padding: 2px 8px;
            border-radius: 10px;
        }
        pre {
            background: #1e293b;
            padding: 16px;
            border-radius: 8px;
            overflow-x: auto;
            margin: 12px 0;
        }
        code {
            font-family: 'Fira Code', monospace;
            font-size: 0.9em;
        }
        p { margin-bottom: 8px; }
        p:last-child { margin-bottom: 0; }
    </style>
</head>
<body>
    <div class="header">
        <h1>${sessionTitle}</h1>
        <p>导出时间: ${new Date().toLocaleString()}</p>
    </div>
    <div class="conversation">
    `;

    messages.value.forEach(msg => {
        const content = msg.sender === 'assistant' ? marked.parse(msg.text) : msg.text;
        const time = new Date(msg.timestamp).toLocaleString();
        const modelInfo = msg.sender === 'assistant' && msg.modelID 
            ? `<span class="model-tag">${msg.providerID ? msg.providerID + ' / ' : ''}${msg.modelID}</span>` 
            : '';
        
        htmlContent += `
        <div class="message ${msg.sender}">
            <div class="message-content">${msg.sender === 'assistant' ? content : msg.text}</div>
            <div class="meta">
                ${modelInfo}
                <span>${msg.sender === 'assistant' ? '助手' : '用户'} · ${time}</span>
            </div>
        </div>
        `;
    });

    htmlContent += `
    </div>
</body>
</html>`;

    const blob = new Blob([htmlContent], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `chat-history-${new Date().getTime()}.html`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
};

onMounted(() => {
    document.title = appConfig.app.title;
    currentUser.value = authService.getCurrentUser();
    handleNewChat();
    if (currentUser.value) {
        loadHistory();
        loadConfig();
    }
});
</script>

<template>
  <div v-if="!currentUser">
    <Login 
      v-if="authPage === 'login'" 
      @login-success="handleLoginSuccess" 
      @go-to-register="authPage = 'register'"
    />
    <Register 
      v-else 
      @go-to-login="authPage = 'login'"
    />
  </div>
  
  <div v-else class="app-layout">
    <Sidebar 
      :sessions="sessions" 
      :currentSessionId="currentSessionId"
      :isCollapsed="isHistoryCollapsed"
      @new-chat="handleNewChat"
      @select-session="handleSelectSession"
      @toggle-history="isHistoryCollapsed = !isHistoryCollapsed"
      @rename-session="handleRenameSession"
      @delete-session="handleDeleteSession"
    />
    
    <main class="main-container">
      <header class="app-header">
        <div class="header-info">
          <h1>{{ appConfig.app.headerTitle }}</h1>
          <p>欢迎, {{ currentUser.username }}</p>
        </div>
        <div class="header-actions">
          <button class="icon-btn" title="导出对话" @click="handleExportHTML">
            <i class="fa-solid fa-download" style="font-size: 20px;"></i>
          </button>
          <button class="icon-btn" title="系统状态">
            <i class="fa-solid fa-chart-line" style="font-size: 20px;"></i>
          </button>
          <button class="icon-btn" title="退出登录" @click="handleLogout">
            <i class="fa-solid fa-right-from-bracket" style="font-size: 20px;"></i>
          </button>
        </div>
      </header>

      <ModelSelector 
        v-if="providers.length"
        v-model="modelConfig"
        :providers="providers"
      />
      
      <ChatBox :messages="messages" :isTyping="isTyping" />
      
      <ChatInput @send="handleSendMessage" />
    </main>
  </div>
</template>

<style>
:root {
  --primary: #0F172A;
  --secondary: #334155;
  --accent: #0369A1;
  --background: #F8FAFC;
  --surface: #FFFFFF;
  --text-primary: #020617;
  --text-secondary: #475569;
  --border: #E2E8F0;
  --glass-bg: rgba(255, 255, 255, 0.8);
  --glass-border: rgba(255, 255, 255, 0.2);
  --message-user: #0369A1;
  --message-assistant: #F1F5F9;
}

* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

body {
  font-family: 'Open Sans', sans-serif;
  background-color: var(--background);
  color: var(--text-primary);
  height: 100vh;
  overflow: hidden;
}

.app-layout {
  display: flex;
  height: 100vh;
  width: 100vw;
}

.main-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  background-color: var(--background);
  position: relative;
}

.app-header {
  height: 72px;
  padding: 0 40px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: var(--glass-bg);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid var(--border);
  z-index: 10;
}

.header-info h1 {
  font-size: 1.125rem;
  font-weight: 600;
}

.header-info p {
  font-size: 0.8125rem;
  color: var(--text-secondary);
}

.header-actions {
  display: flex;
  gap: 8px;
}

.icon-btn {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: 1px solid var(--border);
  border-radius: 8px;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.2s;
}

.icon-btn:hover {
  background: var(--surface);
  color: var(--primary);
  border-color: var(--text-secondary);
}

/* Animations */
.animate-fade-in {
  animation: fadeIn 0.3s ease-out forwards;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
