<script setup>
import { ref, onMounted, computed } from 'vue';
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

const apiFetch = async (url, options = {}) => {
    const token = currentUser.value?.token;
    const headers = {
        ...options.headers,
    };
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }
    const response = await window.fetch(url, { ...options, headers });
    if (response.status === 401) {
        handleLogout();
        throw new Error('Session expired. Please login again.');
    }
    return response;
};

const currentSessionId = ref(null);
const messages = ref([]);
const sessions = ref([]);
const providers = ref([]);
const systemWorkspaces = ref([]);
const userWorkspaces = ref([]);
const currentWorkspacePath = ref(localStorage.getItem('currentWorkspacePath') || '');
const currentWorkspaceId = ref(localStorage.getItem('currentWorkspaceId') || '');

const allWorkspaces = computed(() => {
    return [...systemWorkspaces.value, ...userWorkspaces.value];
});

const effectiveWorkspacePath = computed(() => currentWorkspacePath.value);
const effectiveWorkspaceId = computed(() => currentWorkspaceId.value);

const refreshConfig = async () => {
    try {
        const response = await apiFetch(`/api/config/active?workspace_id=${effectiveWorkspaceId.value}`);
        const data = await response.json();
        // Update appConfig object properties
        Object.assign(appConfig, data);
    } catch (error) {
        console.error('Error refreshing config:', error);
    }
};

const loadWorkspaces = async () => {
    if (!currentUser.value) return;
    try {
        const response = await apiFetch(`/api/auth/workspaces?username=${encodeURIComponent(currentUser.value.username)}`);
        const data = await response.json();
        systemWorkspaces.value = data.system || [];
        userWorkspaces.value = data.user || [];
        
        // If current workspace is not in the list anymore, clear it
        if (currentWorkspacePath.value && !allWorkspaces.value.find(ws => ws.path === currentWorkspacePath.value)) {
            currentWorkspacePath.value = '';
            currentWorkspaceId.value = '';
            localStorage.removeItem('currentWorkspacePath');
            localStorage.removeItem('currentWorkspaceId');
        }
        await refreshConfig();
    } catch (error) {
        console.error('Error loading workspaces:', error);
    }
};

const handleSelectWorkspace = async (path) => {
    const ws = allWorkspaces.value.find(w => w.path === path);
    currentWorkspacePath.value = path;
    currentWorkspaceId.value = ws ? ws.id : '';
    localStorage.setItem('currentWorkspacePath', path);
    localStorage.setItem('currentWorkspaceId', currentWorkspaceId.value);
    
    // 必须等待配置刷新完成，否则 handleNewChat 会使用旧的 welcomeMessage
    await refreshConfig();
    
    handleNewChat();
    loadHistory();
    setupEventSource();
};

const handleCreateWorkspace = async (payload) => {
    if (!currentUser.value) return;
    
    try {
        const response = await apiFetch('/api/auth/workspaces', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                username: currentUser.value.username,
                path: payload.path,
                id: payload.id
            })
        });
        const data = await response.json();
        if (data.success) {
            systemWorkspaces.value = data.system;
            userWorkspaces.value = data.user;
            handleSelectWorkspace(payload.path);
        } else {
            alert('创建工作区失败: ' + (data.error || '未知错误'));
        }
    } catch (error) {
        console.error('Error creating workspace:', error);
        alert('系统错误: 无法保存工作区');
    }
};

const handleDeleteWorkspace = async (ws) => {
    if (!confirm(`确定要移除工作区 "${ws.name || ws.path}" 吗？\n注意：这仅是从列表中移除，不会删除物理文件夹。`)) return;

    try {
        const response = await apiFetch(`/api/auth/workspaces?username=${encodeURIComponent(currentUser.value.username)}&path=${encodeURIComponent(ws.path)}`, {
            method: 'DELETE'
        });
        const data = await response.json();
        if (data.success) {
            // Re-load workspaces to update the list and handle current workspace removal
            await loadWorkspaces();
        } else {
            alert('移除工作区失败: ' + (data.error || '未知错误'));
        }
    } catch (error) {
        console.error('Error deleting workspace:', error);
        alert('系统错误: 无法移除工作区');
    }
};


const modelConfig = ref({
    providerID: '',
    modelID: '',
    mode: 'plan'
});
const isHistoryCollapsed = ref(false);
const isTyping = ref(false);
const eventSource = ref(null);
const sidebarRef = ref(null);

const handlePromptCreate = () => {
    if (sidebarRef.value) {
        sidebarRef.value.handleNewWorkspace();
    }
};

const setupEventSource = () => {
    if (eventSource.value) {
        console.log('[SSE] Closing existing EventSource connection...');
        eventSource.value.close();
    }

    const url = new URL('/api/events', window.location.origin);
    if (currentUser.value?.token) {
        url.searchParams.append('token', currentUser.value.token);
    }
    if (effectiveWorkspacePath.value) {
        url.searchParams.append('workspace_path', effectiveWorkspacePath.value);
    }

    console.log('[SSE] Connecting to:', url.toString());
    const es = new EventSource(url.toString());

    es.onopen = () => {
        console.log('[SSE] Connection opened successfully.');
    };

    es.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            
            // Log non-chunk updates for debugging
            if (data.type !== 'message.part.updated') {
                console.log('[SSE] Received event:', data.type, data);
            }

            if (data.type === 'session.updated') {
                const properties = data.properties || {};
                const info = properties.info || {};
                const title = info.title;
                const targetId = data.id || info.id;
                
                if (title && targetId) {
                    const session = sessions.value.find(s => s.id === targetId);
                    if (session) {
                        session.title = title;
                    } else if (targetId === currentSessionId.value) {
                        // 如果是当前会话但在列表中找不到，刷新列表
                        loadHistory();
                    }
                }
            }

            if (data.type === 'message.part.updated') {
                const delta = data.properties?.delta;
                const part = data.properties?.part;
                if (delta && part) {
                    // Update the last assistant message
                    const assistantMessages = messages.value.filter(m => m.sender === 'assistant');
                    if (assistantMessages.length > 0) {
                        const lastMsg = assistantMessages[assistantMessages.length - 1];
                        // Don't update the welcome message
                        if (lastMsg.modelID !== 'System') {
                            if (!lastMsg.parts) lastMsg.parts = [];
                            
                            let targetPart = lastMsg.parts.find(p => p.id === part.id);
                            if (!targetPart) {
                                targetPart = { id: part.id, type: part.type, content: '' };
                                lastMsg.parts.push(targetPart);
                            }
                            targetPart.content += delta;
                            
                            // Keep text in sync for compatibility
                            if (part.type === 'text') {
                                lastMsg.text += delta;
                            }
                        }
                    }
                }
            }
        } catch (e) {
            console.warn('[SSE] Failed to parse message data:', event.data);
        }
    };

    es.onerror = (e) => {
        console.error('[SSE] Connection error:', e);
        if (es.readyState === EventSource.CLOSED) {
            console.log('[SSE] Connection closed.');
        }
        // Retry after 5 seconds
        setTimeout(setupEventSource, 5000);
    };

    eventSource.value = es;
};

const handleLoginSuccess = (user) => {
    currentUser.value = user;
    loadHistory();
    loadWorkspaces();
    loadConfig();
};

const handleLogout = () => {
    authService.logout();
    currentUser.value = null;
    currentSessionId.value = null;
    messages.value = [];
    authPage.value = 'login';
};

const appendMessage = (text, sender, timestamp, providerID, modelID, isError = false) => {
    messages.value.push({
        text,
        sender,
        timestamp: timestamp || new Date().toISOString(),
        providerID,
        modelID,
        isError,
        parts: sender === 'assistant' ? [] : undefined
    });
};

const loadConfig = async () => {
    try {
        const response = await apiFetch('/api/config/providers');
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
        const headers = {};
        if (effectiveWorkspacePath.value) {
            headers['x-workspace-path'] = effectiveWorkspacePath.value;
            headers['x-workspace-id'] = effectiveWorkspaceId.value;
        }
        
        const response = await apiFetch(`/api/sessions?username=${encodeURIComponent(currentUser.value.username)}`, {
            headers
        });
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
        const headers = {};
        if (effectiveWorkspacePath.value) {
            headers['x-workspace-path'] = effectiveWorkspacePath.value;
            headers['x-workspace-id'] = effectiveWorkspaceId.value;
        }
        
        const response = await apiFetch(`/api/sessions/${sessionId}/messages`, {
            headers
        });
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

    // Create a placeholder for the assistant response
    const assistantMsgIndex = messages.value.length;
    appendMessage('', 'assistant', null, modelConfig.value.providerID, modelConfig.value.modelID);

    try {
        // Store the config used for this message
        const currentProviderID = modelConfig.value.providerID;
        const currentModelID = modelConfig.value.modelID;
        const currentMode = modelConfig.value.mode;

        const commonHeaders = { 'Content-Type': 'application/json' };
        if (effectiveWorkspacePath.value) {
            commonHeaders['x-workspace-path'] = effectiveWorkspacePath.value;
            commonHeaders['x-workspace-id'] = effectiveWorkspaceId.value;
        }

        // Lazy session initialization
        if (!currentSessionId.value) {
            const sessionResp = await apiFetch('/api/sessions', { 
                method: 'POST',
                headers: commonHeaders,
                body: JSON.stringify({ 
                    username: currentUser.value.username
                })
            });
            const sessionData = await sessionResp.json();
            if (sessionData.id) {
                currentSessionId.value = sessionData.id;
                await loadHistory();
            } else {
                throw new Error(sessionData.error || 'Failed to create session');
            }
        }

        const response = await apiFetch(`/api/sessions/${currentSessionId.value}/messages`, {
            method: 'POST',
            headers: commonHeaders,
            body: JSON.stringify({
                providerID: currentProviderID,
                modelID: currentModelID,
                mode: currentMode,
                message: message
            }),
        });

        const data = await response.json();
        if (data.text || data.parts) {
            // 因为只会返回最后一个 msg 的 parts，可能会缺少前面的内容，所以不用替换
            // 直接使用流式输出的结果就足够了，但需要整理一下当前 message 中的 parts，将 reasoning 的部分合并
            const currentMsg = messages.value[assistantMsgIndex];
            if (currentMsg) {
                if (data.parentID) currentMsg.parentID = data.parentID;
                if (currentMsg.parts && currentMsg.parts.length > 0) {
                    const reasoningParts = currentMsg.parts.filter(p => p.type === 'reasoning');
                    const otherParts = currentMsg.parts.filter(p => p.type !== 'reasoning');
                    
                    if (reasoningParts.length > 0) {
                        const mergedReasoning = {
                            id: 'merged-reasoning-' + Date.now(),
                            type: 'reasoning',
                            content: reasoningParts.map(p => p.content).filter(c => c !== undefined && c !== null).join('\n\n')
                        };
                        currentMsg.parts = [mergedReasoning, ...otherParts];
                    }
                }
            }
        } else if (data.error) {
            const errorMsg = typeof data.error === 'object' 
                ? (data.error.message || JSON.stringify(data.error)) 
                : data.error;
            throw new Error(errorMsg);
        } else {
            throw new Error('Unexpected response format from server');
        }
    } catch (error) {
        console.error('Error sending message:', error);
        // Update the placeholder with error info
        messages.value[assistantMsgIndex].text = '**系统错误：** ' + (error.message || '无法连接到后端服务器');
        messages.value[assistantMsgIndex].isError = true;
    } finally {
        isTyping.value = false;
    }
};

const handleRenameSession = async (session) => {
    const newTitle = prompt('请输入新的会话标题：', session.title);
    if (newTitle === null || newTitle.trim() === '' || newTitle === session.title) return;

    try {
        const headers = { 'Content-Type': 'application/json' };
        if (effectiveWorkspacePath.value) {
            headers['x-workspace-path'] = effectiveWorkspacePath.value;
            headers['x-workspace-id'] = effectiveWorkspaceId.value;
        }
        
        const response = await apiFetch(`/api/sessions/${session.id}`, {
            method: 'PATCH',
            headers: headers,
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
        const headers = {};
        if (effectiveWorkspacePath.value) {
            headers['x-workspace-path'] = effectiveWorkspacePath.value;
            headers['x-workspace-id'] = effectiveWorkspaceId.value;
        }

        
        const response = await apiFetch(`/api/sessions/${session.id}?username=${encodeURIComponent(currentUser.value.username)}`, {
            method: 'DELETE',
            headers: headers
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
        }),
        {
            breaks: true
        }
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
            white-space: pre-wrap;
        }
        .assistant .message-content p {
            margin-bottom: 8px;
        }
        .assistant .message-content p:last-child {
            margin-bottom: 0;
        }
        .error .message-content {
            border-color: #f87171;
            background-color: #fef2f2;
            color: #991b1b;
        }
        .error-indicator {
            color: #ef4444;
            font-weight: 600;
            font-size: 0.75rem;
            margin-right: 8px;
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
        const errorIndicator = msg.isError 
            ? `<span class="error-indicator">⚠️ 服务异常</span>` 
            : '';
        
        htmlContent += `
        <div class="message ${msg.sender} ${msg.isError ? 'error' : ''}">
            <div class="message-content">${msg.sender === 'assistant' ? content : msg.text}</div>
            <div class="meta">
                ${errorIndicator}
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

onMounted(async () => {
    document.title = appConfig.app.title;
    currentUser.value = authService.getCurrentUser();
    
    if (currentUser.value) {
        // 先加载工作区和配置
        await loadWorkspaces();
        // 然后再执行新对话，确保欢迎语是基于当前工作区配置的
        handleNewChat();
        loadHistory();
        loadConfig();
        setupEventSource();
    } else {
        handleNewChat();
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
      ref="sidebarRef"
      :sessions="sessions" 
      :currentSessionId="currentSessionId"
      :isCollapsed="isHistoryCollapsed"
      :systemWorkspaces="systemWorkspaces"
      :userWorkspaces="userWorkspaces"
      :currentWorkspacePath="effectiveWorkspacePath"
      @new-chat="handleNewChat"
      @select-session="handleSelectSession"
      @toggle-history="isHistoryCollapsed = !isHistoryCollapsed"
      @rename-session="handleRenameSession"
      @delete-session="handleDeleteSession"
      @select-workspace="handleSelectWorkspace"
      @create-workspace="handleCreateWorkspace"
      @delete-workspace="handleDeleteWorkspace"
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
        v-if="effectiveWorkspacePath && providers.length"
        v-model="modelConfig"
        :providers="providers"
      />
      
      <template v-if="effectiveWorkspacePath">
        <ChatBox :messages="messages" :isTyping="isTyping" />
        <ChatInput @send="handleSendMessage" />
      </template>

      <div v-else class="no-workspace-container">
        <div class="no-workspace-card animate-fade-in">
          <div class="no-workspace-icon">
            <i class="fa-solid fa-folder-tree"></i>
          </div>
          <h2>尚未进入工作区</h2>
          <p v-if="allWorkspaces.length === 0">您还没有定义任何工作区。请在左侧侧边栏点击 "+" 按钮开设新工作区。</p>
          <p v-else>请从左侧列表中选择一个工作区以开始使用。</p>
          <div v-if="allWorkspaces.length === 0" class="no-workspace-action">
            <button class="primary-btn" @click="handlePromptCreate">
              <i class="fa-solid fa-plus"></i> 开设第一个工作区
            </button>
          </div>
        </div>
      </div>
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

.no-workspace-container {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;
  background-image: radial-gradient(circle at 50% 50%, rgba(3, 105, 161, 0.05) 0%, transparent 70%);
}

.no-workspace-card {
  max-width: 500px;
  width: 100%;
  padding: 48px;
  background: var(--surface);
  border-radius: 24px;
  box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.05), 0 8px 10px -6px rgba(0, 0, 0, 0.05);
  border: 1px solid var(--border);
  text-align: center;
}

.no-workspace-icon {
  width: 80px;
  height: 80px;
  background: rgba(3, 105, 161, 0.1);
  color: var(--accent);
  border-radius: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 32px;
  margin: 0 auto 24px;
}

.no-workspace-card h2 {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--primary);
  margin-bottom: 12px;
}

.no-workspace-card p {
  color: var(--text-secondary);
  line-height: 1.6;
  margin-bottom: 32px;
}

.primary-btn {
  background: var(--accent);
  color: white;
  border: none;
  padding: 12px 24px;
  border-radius: 12px;
  font-weight: 600;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  transition: all 0.2s;
  box-shadow: 0 4px 6px -1px rgba(3, 105, 161, 0.2);
}

.primary-btn:hover {
  filter: brightness(1.1);
  transform: translateY(-1px);
  box-shadow: 0 10px 15px -3px rgba(3, 105, 161, 0.3);
}

.primary-btn:active {
  transform: translateY(0);
}
</style>
