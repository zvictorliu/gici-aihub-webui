<script setup>
import { computed } from 'vue';
import { marked } from 'marked';

const props = defineProps({
  message: Object
});

const renderedContent = computed(() => {
  if (props.message.sender === 'assistant') {
    return marked.parse(props.message.text);
  }
  return props.message.text;
});

const formattedTime = computed(() => {
  const date = new Date(props.message.timestamp);
  return date.getHours() + ':' + date.getMinutes().toString().padStart(2, '0');
});
</script>

<template>
  <div class="message animate-fade-in" :class="message.sender">
    <div 
      class="message-content" 
      v-if="message.sender === 'assistant'" 
      v-html="renderedContent"
    ></div>
    <div 
      class="message-content" 
      v-else
    >{{ message.text }}</div>
    <div class="message-meta">{{ formattedTime }}</div>
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

.message.user {
  align-self: flex-end;
}

.message.user .message-content {
  background-color: var(--message-user);
  color: white;
  border-bottom-right-radius: 4px;
}

.message-meta {
  font-size: 0.75rem;
  color: var(--text-secondary);
  margin: 0 4px;
}

.message.user .message-meta {
  text-align: right;
}

:deep(pre) {
  background: #1e293b;
  color: #e2e8f0;
  padding: 16px;
  border-radius: 8px;
  overflow-x: auto;
  margin: 12px 0;
}

:deep(code) {
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
