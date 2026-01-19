<script setup>
import { ref, onMounted } from 'vue';
import Sidebar from './components/Sidebar.vue';
import ChatBox from './components/ChatBox.vue';
import ChatInput from './components/ChatInput.vue';
import { Satellite, Activity, User } from 'lucide-vue-next';

const currentSessionId = ref(null);
const messages = ref([]);
const sessions = ref([]);
const isHistoryCollapsed = ref(false);

const appendMessage = (text, sender, timestamp) => {
    messages.value.push({
        text,
        sender,
        timestamp: timestamp || new Date().toISOString()
    });
};

const handleNewChat = () => {
    currentSessionId.value = null;
    messages.value = [{
        text: '您好！我是您的 **GICI-lib 助手**。我专注于 GNSS/INS 组合导航、RTK 定位以及传感器融合技术。今天有什么我可以帮您的吗？',
        sender: 'assistant',
        timestamp: new Date().toISOString()
    }];
};

const handleSelectSession = (sessionId) => {
    currentSessionId.value = sessionId;
    // Mock loading messages for now
    messages.value = [];
};

const handleSendMessage = (message) => {
    appendMessage(message, 'user');
    // Mock assistant response
    setTimeout(() => {
        appendMessage('收到！这是 Vue 重构后的模拟回复。', 'assistant');
    }, 1000);
};

onMounted(() => {
    handleNewChat();
});
</script>

<template>
  <div class="app-layout">
    <Sidebar 
      :sessions="sessions" 
      :currentSessionId="currentSessionId"
      :isCollapsed="isHistoryCollapsed"
      @new-chat="handleNewChat"
      @select-session="handleSelectSession"
      @toggle-history="isHistoryCollapsed = !isHistoryCollapsed"
    />
    
    <main class="main-container">
      <header class="app-header">
        <div class="header-info">
          <h1>组合导航技术专家</h1>
          <p>由 GICI-lib 提供技术支持 (Vue 版)</p>
        </div>
        <div class="header-actions">
          <button class="icon-btn" title="系统状态">
            <Activity :size="20" />
          </button>
          <button class="icon-btn" title="个人资料">
            <User :size="20" />
          </button>
        </div>
      </header>
      
      <ChatBox :messages="messages" />
      
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
