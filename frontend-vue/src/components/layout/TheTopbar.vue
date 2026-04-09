<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useResearchStore, useAuthStore } from '@/stores'

const router = useRouter()
const researchStore = useResearchStore()
const authStore = useAuthStore()

const showApiKeyModal = ref(false)
const isResetting = ref(false)
const copied = ref(false)

// API 基础 URL
const API_BASE = computed(() => {
  if (typeof window === 'undefined') return 'http://localhost:8000/api/v1'
  return window.location.hostname === 'localhost'
    ? 'http://localhost:8000/api/v1'
    : `${window.location.origin}/api/v1`
})

const API_ORIGIN = computed(() => {
  if (typeof window === 'undefined') return 'http://localhost:8000'
  return window.location.hostname === 'localhost'
    ? 'http://localhost:8000'
    : window.location.origin
})

function clearChat() {
  researchStore.reset()
}

function exportReport() {
  if (!researchStore.reportContent) {
    alert('暂无报告内容，请先生成报告')
    return
  }
  const blob = new Blob([researchStore.reportContent], { type: 'text/markdown' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `research-report-${researchStore.studyId || Date.now()}.md`
  a.click()
  URL.revokeObjectURL(url)
}

function goAdmin() {
  router.push('/admin')
}

function logout() {
  authStore.logout()
  router.push('/login')
}

function openApiKeyModal() {
  showApiKeyModal.value = true
  copied.value = false
}

function closeApiKeyModal() {
  showApiKeyModal.value = false
}

async function copyApiKey() {
  const apiKey = authStore.user?.api_key || ''
  try {
    await navigator.clipboard.writeText(apiKey)
    copied.value = true
    setTimeout(() => { copied.value = false }, 2000)
  } catch (err) {
    // Fallback for older browsers
    const textArea = document.createElement('textarea')
    textArea.value = apiKey
    document.body.appendChild(textArea)
    textArea.select()
    document.execCommand('copy')
    document.body.removeChild(textArea)
    copied.value = true
    setTimeout(() => { copied.value = false }, 2000)
  }
}

async function resetApiKey() {
  if (!confirm('确定要重置 API Key 吗？重置后旧的 Key 将立即失效！')) {
    return
  }

  isResetting.value = true
  try {
    const res = await fetch(`${API_BASE.value}/auth/reset-api-key`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${authStore.token}`
      }
    })

    if (res.ok) {
      const data = await res.json()
      if (authStore.user) {
        authStore.user.api_key = data.data.api_key
      }
      alert('API Key 已重置！')
    } else {
      alert('重置失败，请稍后重试')
    }
  } catch (err) {
    alert('网络错误，请稍后重试')
  } finally {
    isResetting.value = false
  }
}
</script>

<template>
  <div class="topbar">
    <span class="topbar-title">{{ researchStore.studyTitle }}</span>
    <div v-if="researchStore.studyId" class="study-badge">
      <div class="dot"></div>
      <span>研究 #{{ researchStore.studyId }}</span>
    </div>
    <div class="topbar-actions">
      <!-- 积分显示 -->
      <div class="credits-badge" v-if="authStore.user && !authStore.isSuperuser">
        <span class="credits-icon">💎</span>
        <span class="credits-value">{{ authStore.credits }}</span>
        <span class="credits-label">积分</span>
      </div>
      <div class="superuser-badge" v-if="authStore.isSuperuser">
        <span>👑 管理员</span>
      </div>
      <!-- API Key 按钮 -->
      <button class="btn btn-ghost" @click="openApiKeyModal">🔑 API Key</button>
      <!-- 管理员入口 -->
      <button v-if="authStore.isSuperuser" class="btn btn-ghost" @click="goAdmin">管理后台</button>
      <button class="btn btn-ghost" @click="clearChat">清空</button>
      <button class="btn btn-primary" @click="exportReport">导出报告</button>
      <button class="btn btn-ghost" @click="logout">退出</button>
    </div>

    <!-- API Key 弹窗 -->
    <Teleport to="body">
      <div v-if="showApiKeyModal" class="modal-overlay" @click.self="closeApiKeyModal">
        <div class="modal-content">
          <div class="modal-header">
            <h3>🔑 我的 API Key</h3>
            <button class="modal-close" @click="closeApiKeyModal">×</button>
          </div>
          <div class="modal-body">
            <p class="api-key-hint">使用此 API Key 调用全自动市场研究 API：</p>
            <div class="api-key-box">
              <code class="api-key-text">{{ authStore.user?.api_key || '加载中...' }}</code>
              <button class="btn-copy" @click="copyApiKey">
                {{ copied ? '✓ 已复制' : '复制' }}
              </button>
            </div>
            <div class="api-usage">
              <h4>📖 使用方法</h4>
              <pre class="code-block">curl -X POST "{{ API_ORIGIN }}/api/v1/research-flow/auto-research" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: {{ authStore.user?.api_key }}" \
  -d '{"user_request": "我想研究年轻女性对国产美妆品牌的态度"}'</pre>
            </div>
            <div class="api-warning">
              ⚠️ 请妥善保管您的 API Key，不要泄露给他人
            </div>
          </div>
          <div class="modal-footer">
            <button class="btn btn-ghost" @click="closeApiKeyModal">关闭</button>
            <button class="btn btn-danger" @click="resetApiKey" :disabled="isResetting">
              {{ isResetting ? '重置中...' : '重置 Key' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.credits-badge {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 12px;
  background: linear-gradient(135deg, #ffd700, #ffaa00);
  border-radius: 16px;
  color: #1a1a1a;
  font-size: 13px;
  font-weight: 600;
}

.credits-icon {
  font-size: 14px;
}

.credits-value {
  font-weight: 700;
}

.credits-label {
  font-weight: 400;
  opacity: 0.8;
}

.superuser-badge {
  display: flex;
  align-items: center;
  padding: 4px 12px;
  background: linear-gradient(135deg, #667eea, #764ba2);
  border-radius: 16px;
  color: white;
  font-size: 13px;
  font-weight: 600;
}

/* Modal styles */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: var(--surface1);
  border-radius: 12px;
  width: 90%;
  max-width: 560px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border);
}

.modal-header h3 {
  margin: 0;
  font-size: 16px;
  color: var(--text-primary);
}

.modal-close {
  background: none;
  border: none;
  font-size: 24px;
  color: var(--text-secondary);
  cursor: pointer;
  padding: 0;
  line-height: 1;
}

.modal-close:hover {
  color: var(--text-primary);
}

.modal-body {
  padding: 20px;
}

.api-key-hint {
  margin: 0 0 12px;
  font-size: 13px;
  color: var(--text-secondary);
}

.api-key-box {
  display: flex;
  gap: 8px;
  padding: 12px;
  background: var(--surface2);
  border-radius: 8px;
  border: 1px solid var(--border);
}

.api-key-text {
  flex: 1;
  font-family: 'SF Mono', Monaco, monospace;
  font-size: 12px;
  color: var(--accent);
  word-break: break-all;
  background: none;
  padding: 0;
}

.btn-copy {
  padding: 6px 12px;
  background: var(--accent);
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 12px;
  cursor: pointer;
  white-space: nowrap;
}

.btn-copy:hover {
  opacity: 0.9;
}

.api-usage {
  margin-top: 16px;
}

.api-usage h4 {
  margin: 0 0 8px;
  font-size: 13px;
  color: var(--text-primary);
}

.code-block {
  background: var(--surface2);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 12px;
  font-family: 'SF Mono', Monaco, monospace;
  font-size: 11px;
  color: var(--text-secondary);
  overflow-x: auto;
  white-space: pre-wrap;
  word-break: break-all;
}

.api-warning {
  margin-top: 16px;
  padding: 10px 12px;
  background: rgba(255, 152, 0, 0.1);
  border: 1px solid rgba(255, 152, 0, 0.3);
  border-radius: 6px;
  font-size: 12px;
  color: #ff9800;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 16px 20px;
  border-top: 1px solid var(--border);
}

.btn-danger {
  background: #dc3545;
  color: white;
  padding: 8px 16px;
  border: none;
  border-radius: 6px;
  font-size: 13px;
  cursor: pointer;
}

.btn-danger:hover:not(:disabled) {
  background: #c82333;
}

.btn-danger:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
