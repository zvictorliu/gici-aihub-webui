<script setup>
import { computed, ref } from 'vue';
import { Marked } from 'marked';
import { markedHighlight } from "marked-highlight";
import hljs from 'highlight.js';
import 'highlight.js/styles/github-dark.css';

const props = defineProps({
  message: Object
});

// Track collapsed state of reasoning parts
const expandedParts = ref({});

const toggleReasoning = (partId) => {
  expandedParts.value[partId] = !expandedParts.value[partId];
};

const isExpanded = (partId) => {
  // Default to expanded for new parts to show streaming
  return expandedParts.value[partId] !== false;
};

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

const renderedParts = computed(() => {
  if (props.message.sender === 'assistant' && props.message.parts && props.message.parts.length > 0) {
    return props.message.parts.map(p => ({
      ...p,
      html: p.type === 'text' ? marked.parse(p.content) : p.content
    }));
  }
  return null;
});

const renderedContent = computed(() => {
  if (props.message.sender === 'assistant' && !renderedParts.value) {
    return marked.parse(props.message.text);
  }
  return props.message.text;
});

const formattedTime = computed(() => {
  const date = new Date(props.message.timestamp);
  return date.getHours() + ':' + date.getMinutes().toString().padStart(2, '0');
});

const copyContent = computed(() => {
  if (props.message.parts && props.message.parts.length > 0) {
    return props.message.parts
      .filter(p => p.type === 'text')
      .map(p => p.content)
      .join('');
  }
  return props.message.text;
});

const isCopied = ref(false);
const copyToClipboard = async () => {
  try {
    await navigator.clipboard.writeText(copyContent.value);
    isCopied.value = true;
    setTimeout(() => {
      isCopied.value = false;
    }, 2000);
  } catch (err) {
    console.error('Failed to copy: ', err);
  }
};
</script>

<template>
  <div class="message animate-fade-in" :class="[message.sender, { 'error-msg': message.isError }]">
    <div 
      class="message-content" 
      v-if="message.sender === 'assistant'"
    >
      <template v-if="renderedParts">
        <div v-for="part in renderedParts" :key="part.id" :class="['message-part', part.type]">
          <div v-if="part.type === 'reasoning'" class="reasoning-container" :class="{ collapsed: !isExpanded(part.id) }">
            <div class="reasoning-header" @click="toggleReasoning(part.id)" title="点击展开/折叠思考过程">
              <span class="header-left">
                <i class="fa-solid fa-brain"></i> 思考过程
              </span>
              <i class="fa-solid" :class="isExpanded(part.id) ? 'fa-chevron-up' : 'fa-chevron-down'"></i>
            </div>
            <div v-show="isExpanded(part.id)" class="reasoning-content">{{ part.content }}</div>
          </div>
          <div v-else-if="part.type === 'text'" v-html="part.html"></div>
          <div v-else class="part-content">{{ part.content }}</div>
        </div>
      </template>
      <div v-else v-html="renderedContent"></div>
    </div>
    <div 
      class="message-content" 
      v-else
    >{{ message.text }}</div>
    <div class="message-meta">
      <span v-if="message.isError" class="error-indicator">
        <i class="fa-solid fa-triangle-exclamation"></i> 服务异常
      </span>
      <span v-if="message.sender === 'assistant' && message.modelID" class="model-info">
        <i class="fa-solid fa-robot"></i> {{ message.providerID ? message.providerID + ' / ' : '' }}{{ message.modelID }}
      </span>
      <button 
        v-if="message.sender === 'assistant' && !message.isError && copyContent" 
        class="copy-btn" 
        @click="copyToClipboard" 
        :title="isCopied ? '已复制' : '复制回答内容'"
      >
        <i class="fa-solid" :class="isCopied ? 'fa-check' : 'fa-copy'"></i>
        {{ isCopied ? '已复制' : '复制' }}
      </button>
      <span class="time">{{ formattedTime }}</span>
    </div>
  </div>
</template>

<style scoped>
.message {
  max-width: 85%;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.message-content {
  padding: 16px 20px;
  border-radius: 16px;
  font-size: 1rem;
  line-height: 1.6;
  box-shadow: 0 2px 4px rgba(0,0,0,0.02);
}

.message.assistant {
  align-self: flex-start;
}

.message.assistant .message-content {
  background-color: var(--message-assistant);
  color: var(--text-primary);
  border-bottom-left-radius: 4px;
  border: 1px solid var(--border);
}

.message.assistant .message-content :deep(p) {
  margin-bottom: 8px;
}

.message.assistant .message-content :deep(p:last-child) {
  margin-bottom: 0;
}

.message.assistant .message-content :deep(ul),
.message.assistant .message-content :deep(ol) {
  margin-bottom: 8px;
}

.message-part {
  margin-bottom: 8px;
}

.reasoning-container {
  background: rgba(0, 0, 0, 0.03);
  border-radius: 8px;
  padding: 12px;
  margin: 8px 0;
  border-left: 3px solid var(--text-secondary);
}

.reasoning-header {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 6px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  cursor: pointer;
  user-select: none;
  transition: opacity 0.2s;
}

.reasoning-header:hover {
  opacity: 0.8;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 6px;
}

.reasoning-container.collapsed {
  padding-bottom: 8px;
}

.reasoning-container.collapsed .reasoning-header {
  margin-bottom: 0;
}

.reasoning-content {
  font-size: 0.9rem;
  color: #64748b; /* Gray font for reasoning */
  white-space: pre-wrap;
  font-style: italic;
}

.part-content {
  white-space: pre-wrap;
}

.message.error-msg .message-content {
  border-color: #f87171;
  background-color: #fef2f2;
  color: #991b1b;
}

.error-indicator {
  color: #ef4444;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 4px;
}

.message.user {
  align-self: flex-end;
}

.message.user .message-content {
  background-color: var(--message-user);
  color: white;
  border-bottom-right-radius: 4px;
  white-space: pre-wrap;
}

.message-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.75rem;
  color: var(--text-secondary);
  margin: 0 4px;
}

.message.user .message-meta {
  justify-content: flex-end;
}

.model-info {
  background: rgba(0, 0, 0, 0.05);
  padding: 2px 8px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  gap: 4px;
}

.copy-btn {
  background: transparent;
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 0.75rem;
  color: var(--text-secondary);
  padding: 2px 6px;
  border-radius: 4px;
  transition: all 0.2s ease;
  opacity: 0.8;
  min-width: 50px;
}

.copy-btn:hover {
  background: rgba(0, 0, 0, 0.05);
  opacity: 1;
}

.copy-btn i {
  font-size: 0.7rem;
}

:deep(pre) {
  margin: 12px 0;
}

:deep(pre code.hljs) {
  padding: 16px;
  border-radius: 8px;
  display: block;
  overflow-x: auto;
  font-family: 'Fira Code', monospace;
  font-size: 0.9em;
}

:deep(code:not(.hljs)) {
  background: #f1f5f9;
  color: #0369a1;
  padding: 2px 4px;
  border-radius: 4px;
  font-family: 'Fira Code', monospace;
  font-size: 0.9em;
}

:deep(p) {
  margin-bottom: 8px;
}

:deep(p:last-child) {
  margin-bottom: 0;
}
</style>
