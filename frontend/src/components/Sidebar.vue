<script setup>
import { appConfig } from '../config/appConfig';

const props = defineProps({
  sessions: Array,
  currentSessionId: String,
  isCollapsed: Boolean,
  workspaces: Array,
  currentWorkspacePath: String
});

const emit = defineEmits(['new-chat', 'select-session', 'toggle-history', 'rename-session', 'delete-session', 'select-workspace', 'create-workspace']);

const handleNewWorkspace = () => {
  const path = prompt('请输入新工作区的绝对路径：');
  if (path && path.trim()) {
    emit('create-workspace', path.trim());
  }
};
</script>

<template>
  <aside class="sidebar">
    <div class="sidebar-header">
      <div class="logo">
        <i :class="appConfig.ui.logoIcon" :style="{ fontSize: '24px', color: appConfig.ui.logoColor }"></i>
        <span>{{ appConfig.app.title }}</span>
      </div>
    </div>
    
    <div class="sidebar-content">
      <div class="nav-group">
        <div class="nav-header">
          <span class="nav-label">工作区</span>
          <button class="add-btn" title="新建工作区" @click="handleNewWorkspace">
            <i class="fa-solid fa-plus"></i>
          </button>
        </div>
        <div class="workspace-list">
          <button 
            v-for="ws in workspaces" 
            :key="ws.path"
            class="nav-item workspace-item" 
            :class="{ active: ws.path === currentWorkspacePath }"
            @click="emit('select-workspace', ws.path)"
          >
            <i class="fa-solid fa-folder-open"></i>
            <span class="workspace-name" :title="ws.path">
              {{ ws.name || ws.path.split('/').pop() || ws.path }}
              <span v-if="ws.path === appConfig.app.default_directory" class="default-tag">(默认)</span>
            </span>
          </button>
          <div v-if="workspaces.length === 0" class="empty-hint">
            点击 + 开设新工作区
          </div>
        </div>
      </div>

      <div class="nav-group">
        <span class="nav-label">常规</span>
        <button 
          class="nav-item" 
          :class="{ active: !currentSessionId }"
          @click="emit('new-chat')"
        >
          <i class="fa-solid fa-message"></i>
          <span>新对话</span>
        </button>
      </div>
      
      <div class="nav-group" :class="{ collapsed: isCollapsed }">
        <div class="nav-header" @click="emit('toggle-history')">
          <span class="nav-label">历史记录</span>
          <i class="fa-solid fa-chevron-down toggle-icon" style="font-size: 14px;"></i>
        </div>
        
        <div v-if="!isCollapsed" class="history-list">
          <button 
            v-for="session in sessions" 
            :key="session.id"
            class="history-item"
            :class="{ active: session.id === currentSessionId }"
            @click="emit('select-session', session.id)"
          >
            <i class="fa-solid fa-message" style="font-size: 16px;"></i>
            <span class="session-title">{{ session.title || '无标题会话' }}</span>
            <div class="item-actions">
              <button class="action-btn rename" @click.stop="emit('rename-session', session)">
                <i class="fa-solid fa-pen-to-square" style="font-size: 14px;"></i>
              </button>
              <button class="action-btn delete" @click.stop="emit('delete-session', session)">
                <i class="fa-solid fa-trash-can" style="font-size: 14px;"></i>
              </button>
            </div>
          </button>
        </div>
      </div>
      
      <div class="nav-group">
        <span class="nav-label">设置</span>
        <button class="nav-item">
          <i class="fa-solid fa-gear"></i>
          <span>偏好设置</span>
        </button>
        <a 
          :href="appConfig.links.helpDocUrl" 
          target="_blank" 
          rel="noopener noreferrer"
          class="nav-item"
        >
          <i class="fa-solid fa-circle-question"></i>
          <span>帮助文档</span>
        </a>
      </div>
    </div>
    
    <div class="sidebar-footer">
      <a 
        :href="appConfig.links.githubRepo" 
        target="_blank" 
        rel="noopener noreferrer"
        class="github-link"
        title="GitHub Repository"
      >
        <i class="fa-brands fa-github" style="font-size: 16px;"></i>
      </a>
      <span>{{ appConfig.app.shortCopyright }}</span>
      <span>All Rights Reserved</span>
    </div>
  </aside>
</template>

<style scoped>
.sidebar {
  width: 280px;
  background-color: var(--primary);
  color: white;
  display: flex;
  flex-direction: column;
  transition: all 0.3s ease;
}

.sidebar-header {
  padding: 24px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.logo {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 1.25rem;
  font-weight: 600;
  font-family: 'Poppins', sans-serif;
}

.sidebar-content {
  flex: 1;
  padding: 20px 16px;
  overflow-y: auto;
}

.nav-group {
  margin-bottom: 24px;
}

.nav-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-right: 12px;
  margin-bottom: 12px;
}

.add-btn {
  background: transparent;
  border: none;
  color: rgba(255, 255, 255, 0.5);
  cursor: pointer;
  padding: 4px;
  border-radius: 4px;
  transition: all 0.2s;
}

.add-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  color: white;
}

.workspace-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.workspace-item {
  padding: 8px 12px;
}

.workspace-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  display: flex;
  align-items: center;
  gap: 4px;
}

.default-tag {
  font-size: 0.7rem;
  opacity: 0.6;
  font-weight: normal;
}

.empty-hint {
  font-size: 0.75rem;
  color: rgba(255, 255, 255, 0.3);
  padding-left: 12px;
  font-style: italic;
}

.nav-label {
  display: block;
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: rgba(255, 255, 255, 0.5);
  padding-left: 12px;
}

.toggle-icon {
  color: rgba(255, 255, 255, 0.5);
  transition: transform 0.3s ease;
}

.collapsed .toggle-icon {
  transform: rotate(-90deg);
}

.nav-item {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: transparent;
  border: none;
  color: rgba(255, 255, 255, 0.7);
  border-radius: 8px;
  cursor: pointer;
  font-size: 0.9375rem;
  transition: all 0.2s;
  text-align: left;
  text-decoration: none;
}

.nav-item:hover {
  background: rgba(255, 255, 255, 0.1);
  color: white;
}

.nav-item.active {
  background: var(--accent);
  color: white;
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-top: 8px;
  max-height: 400px;
  overflow-y: auto;
}

.history-item {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  background: transparent;
  border: none;
  color: rgba(255, 255, 255, 0.7);
  border-radius: 8px;
  cursor: pointer;
  font-size: 0.875rem;
  transition: all 0.2s;
  text-align: left;
  white-space: nowrap;
  overflow: hidden;
  position: relative;
}

.history-item:hover {
  background: rgba(255, 255, 255, 0.1);
  color: white;
  padding-right: 60px;
}

.history-item.active {
  background: rgba(255, 255, 255, 0.15);
  color: white;
  border-left: 3px solid var(--accent);
  border-radius: 4px 8px 8px 4px;
}

.session-title {
  overflow: hidden;
  text-overflow: ellipsis;
}

.item-actions {
  position: absolute;
  right: 8px;
  display: none;
  gap: 4px;
}

.history-item:hover .item-actions {
  display: flex;
}

.action-btn {
  padding: 4px;
  background: transparent;
  border: none;
  color: rgba(255, 255, 255, 0.5);
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
}

.action-btn:hover {
  background: rgba(255, 255, 255, 0.2);
  color: white;
}

.action-btn.delete:hover {
  color: #EF4444;
}

.sidebar-footer {
  padding: 20px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 0.75rem;
  color: rgba(255, 255, 255, 0.4);
  text-align: center;
  align-items: center;
}

.github-link {
  color: rgba(255, 255, 255, 0.4);
  transition: color 0.2s;
  margin-bottom: 4px;
}

.github-link:hover {
  color: white;
}
</style>
