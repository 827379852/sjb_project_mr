<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useResearchStore, useUIStore, useAuthStore } from '@/stores'
import { useResearchApi } from '@/composables'
import type { StudyListItem } from '@/types'

const router = useRouter()
const researchStore = useResearchStore()
const uiStore = useUIStore()
const authStore = useAuthStore()
const { listStudies, getStudy, deleteStudy, loadStudy } = useResearchApi()

const studies = ref<StudyListItem[]>([])
const loading = ref(false)
const showApiKeyModal = ref(false)
const showCreditsLogModal = ref(false)
const isResetting = ref(false)
const copied = ref(false)
const creditsLog = ref<any[]>([])
const creditsLogLoading = ref(false)
const creditsLogTotal = ref(0)
const creditsLogPage = ref(1)

// 是否已登录
const isLoggedIn = computed(() => authStore.isAuthenticated)

// 用户首字母
const userInitial = computed(() => {
  const name = authStore.user?.name || ''
  return name.charAt(0).toUpperCase() || 'U'
})

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

// 加载研究列表
async function loadStudies() {
  if (!isLoggedIn.value) return
  loading.value = true
  studies.value = await listStudies()
  loading.value = false
}

// 选择研究
async function selectStudy(study: StudyListItem) {
  const detail = await getStudy(study.id)
  if (detail) {
    loadStudy(detail)
    uiStore.hideWelcome()
    uiStore.showProgressBar()
  }
}

// 新建研究
function newStudy() {
  researchStore.reset()
  uiStore.reset()
  // 清空对话框消息
  if (typeof window !== 'undefined' && (window as any).clearMessages) {
    ;(window as any).clearMessages()
  }
}

// 删除研究
async function handleDelete(studyId: string, event: Event) {
  event.stopPropagation()
  if (confirm('确定要删除这个研究吗？')) {
    const success = await deleteStudy(studyId)
    if (success) {
      studies.value = studies.value.filter(s => s.id !== studyId)
      if (researchStore.studyId === studyId) {
        newStudy()
      }
    }
  }
}

// 判断是否是当前选中的研究
function isActive(studyId: string) {
  return researchStore.studyId === studyId
}

// 格式化日期
function formatDate(dateStr: string) {
  const date = new Date(dateStr)
  return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
}

// 退出登录
function logout() {
  authStore.logout()
  router.push('/login')
}

// API Key 相关
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
      alert('重置失败，请稀后重试')
    }
  } catch (err) {
    alert('网络错误，请稍后重试')
  } finally {
    isResetting.value = false
  }
}

// 积分记录相关
async function openCreditsLogModal() {
  showCreditsLogModal.value = true
  await loadCreditsLog()
}

function closeCreditsLogModal() {
  showCreditsLogModal.value = false
}

async function loadCreditsLog() {
  creditsLogLoading.value = true
  try {
    const res = await fetch(`${API_BASE.value}/auth/credit-logs?page=${creditsLogPage.value}&page_size=10`, {
      headers: {
        'Authorization': `Bearer ${authStore.token}`
      }
    })
    if (res.ok) {
      const data = await res.json()
      creditsLog.value = data.data.items || []
      creditsLogTotal.value = data.data.total || 0
    }
  } catch (err) {
    console.error('加载积分记录失败', err)
  } finally {
    creditsLogLoading.value = false
  }
}

function getLogTypeLabel(type: string): string {
  const labels: Record<string, string> = {
    deduct: '扣除',
    refund: '返还',
    reward: '奖励',
    admin_adjust: '管理员调整'
  }
  return labels[type] || type
}

function formatLogDate(dateStr: string): string {
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

// 登录后加载研究列表
onMounted(() => {
  if (isLoggedIn.value) {
    loadStudies()
  }
})
</script>

<template>
  <aside class="sidebar">
    <div class="sidebar-logo">
      <div class="logo-text">ResearchMind</div>
      <div class="logo-sub">AI 定性用户研究平台</div>
    </div>

    <div class="sidebar-section">
      <div class="sidebar-section-title">工作区</div>
      <div class="sidebar-item" :class="{ active: !researchStore.studyId }" @click="newStudy">
        <span class="icon">✦</span>
        <span>新建研究</span>
      </div>
    </div>

    <div class="sidebar-section studies-section">
      <div class="sidebar-section-title">
        我的研究
        <span v-if="studies.length > 0" class="study-count">{{ studies.length }}</span>
      </div>

      <div v-if="loading" class="sidebar-loading">
        <span class="loading-text">加载中...</span>
      </div>

      <div v-else-if="studies.length === 0" class="sidebar-empty">
        <span class="empty-text">暂无研究</span>
      </div>

      <div v-else class="studies-list">
        <div
          v-for="study in studies"
          :key="study.id"
          class="sidebar-item study-item"
          :class="{ active: isActive(study.id) }"
          @click="selectStudy(study)"
        >
          <span class="icon">📄</span>
          <div class="study-info">
            <span class="study-title">{{ study.title }}</span>
            <span class="study-date">{{ formatDate(study.updated_at) }}</span>
          </div>
          <button class="delete-btn" @click="handleDelete(study.id, $event)" title="删除">
            ×
          </button>
        </div>
      </div>
    </div>

    <!-- 用户信息区域 - 固定在底部 -->
    <div class="sidebar-user">
      <!-- 积分显示 - 可点击查看积分记录 -->
      <div class="credits-display" @click="openCreditsLogModal" style="cursor: pointer">
        <span class="credits-icon">💎</span>
        <span class="credits-label">剩余积分</span>
        <span class="credits-value">{{ authStore.credits }}</span>
        <span class="credits-arrow">›</span>
      </div>

      <div class="user-card">
        <div class="user-avatar">{{ userInitial }}</div>
        <div class="user-info">
          <div class="user-name">{{ authStore.user?.name || '用户' }}</div>
          <div class="user-meta">
            <span v-if="authStore.isSuperuser" class="admin-badge">👑 管理员</span>
            <span v-else class="user-email">{{ authStore.user?.email }}</span>
          </div>
        </div>
        <div class="user-actions">
          <button class="action-btn" @click="openApiKeyModal" title="API Key">
            🔑
          </button>
          <button class="action-btn logout" @click="logout" title="退出登录">
            ➡️
          </button>
        </div>
      </div>
    </div>

    <!-- API Key 弹窗 -->
    <Teleport to="body">
      <div v-if="showApiKeyModal" class="sidebar-modal-overlay" @click.self="closeApiKeyModal">
        <div class="sidebar-modal-content">
          <div class="sidebar-modal-header">
            <h3>🔑 我的 API Key</h3>
            <button class="sidebar-modal-close" @click="closeApiKeyModal">×</button>
          </div>
          <div class="sidebar-modal-body">
            <p class="sidebar-api-key-hint">使用此 API Key 调用全自动市场研究 API：</p>
            <div class="sidebar-api-key-box">
              <code class="sidebar-api-key-text">{{ authStore.user?.api_key || '加载中...' }}</code>
              <button class="sidebar-btn-copy" @click="copyApiKey">
                {{ copied ? '✓ 已复制' : '复制' }}
              </button>
            </div>
            <div class="sidebar-api-usage">
              <h4>📖 使用方法</h4>
              <pre class="sidebar-code-block">curl -X POST "{{ API_ORIGIN }}/api/v1/research-flow/auto-research" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: {{ authStore.user?.api_key }}" \
  -d '{"user_request": "我想研究年轻女性对国产美妆品牌的态度"}'</pre>
            </div>
            <div class="sidebar-api-warning">
              ⚠️ 请妥善保管您的 API Key，不要泄露给他人
            </div>
          </div>
          <div class="sidebar-modal-footer">
            <button class="sidebar-modal-btn sidebar-modal-btn-ghost" @click="closeApiKeyModal">关闭</button>
            <button class="sidebar-modal-btn sidebar-modal-btn-danger" @click="resetApiKey" :disabled="isResetting">
              {{ isResetting ? '重置中...' : '重置 Key' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- 积分记录弹窗 -->
    <Teleport to="body">
      <div v-if="showCreditsLogModal" class="sidebar-modal-overlay" @click.self="closeCreditsLogModal">
        <div class="sidebar-modal-content credits-log-modal">
          <div class="sidebar-modal-header">
            <h3>💎 积分使用记录</h3>
            <button class="sidebar-modal-close" @click="closeCreditsLogModal">×</button>
          </div>
          <div class="sidebar-modal-body">
            <div v-if="creditsLogLoading" class="credits-log-loading">加载中...</div>
            <div v-else-if="creditsLog.length === 0" class="credits-log-empty">暂无积分记录</div>
            <div v-else class="credits-log-list">
              <div v-for="log in creditsLog" :key="log.id" class="credits-log-item">
                <div class="log-left">
                  <span :class="['log-type-badge', log.log_type]">{{ getLogTypeLabel(log.log_type) }}</span>
                  <span class="log-desc">{{ log.description || '-' }}</span>
                </div>
                <div class="log-right">
                  <span :class="['log-amount', log.amount >= 0 ? 'positive' : 'negative']">
                    {{ log.amount >= 0 ? '+' : '' }}{{ log.amount }}
                  </span>
                  <span class="log-balance">余额: {{ log.balance_after }}</span>
                </div>
                <div class="log-time">{{ formatLogDate(log.created_at) }}</div>
              </div>
            </div>
          </div>
          <div class="sidebar-modal-footer">
            <button class="sidebar-modal-btn sidebar-modal-btn-ghost" @click="closeCreditsLogModal">关闭</button>
            <div class="pagination-info" v-if="creditsLogTotal > 0">
              共 {{ creditsLogTotal }} 条记录
            </div>
          </div>
        </div>
      </div>
    </Teleport>
  </aside>
</template>

<style scoped>
.studies-section {
  flex: 1;
  overflow-y: auto;
  min-height: 100px;
}

.study-count {
  font-size: 10px;
  background: var(--accent-dim);
  color: var(--accent);
  padding: 1px 6px;
  border-radius: 10px;
  margin-left: auto;
}

.sidebar-loading,
.sidebar-empty {
  padding: 16px;
  text-align: center;
}

.loading-text,
.empty-text {
  font-size: 12px;
  color: var(--text-dim);
}

.studies-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.study-item {
  position: relative;
  padding-right: 32px !important;
}

.study-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  flex: 1;
  min-width: 0;
}

.study-title {
  font-size: 13px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.study-date {
  font-size: 10px;
  color: var(--text-dim);
}

.delete-btn {
  position: absolute;
  right: 8px;
  top: 50%;
  transform: translateY(-50%);
  width: 20px;
  height: 20px;
  border: none;
  background: transparent;
  color: var(--text-dim);
  cursor: pointer;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  opacity: 0;
  transition: all 0.2s;
}

.study-item:hover .delete-btn {
  opacity: 1;
}

.delete-btn:hover {
  background: rgba(248, 113, 113, 0.15);
  color: var(--red);
}

/* 用户信息区域 */
.sidebar-user {
  padding: 12px;
  border-top: 1px solid var(--border);
  background: var(--surface2);
}

/* 积分显示 */
.credits-display {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  background: linear-gradient(135deg, rgba(139, 92, 246, 0.15), rgba(59, 130, 246, 0.15));
  border-radius: 10px;
  margin-bottom: 10px;
  border: 1px solid rgba(139, 92, 246, 0.2);
}

.credits-icon {
  font-size: 16px;
}

.credits-label {
  font-size: 12px;
  color: var(--text-secondary);
}

.credits-value {
  margin-left: auto;
  font-size: 16px;
  font-weight: 600;
  color: var(--accent);
}

.user-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  background: var(--surface1);
  border-radius: 10px;
  transition: all 0.2s;
}

.user-card:hover {
  background: var(--surface3);
}

.user-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--accent), #8b5cf6);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-weight: 600;
  font-size: 14px;
  flex-shrink: 0;
}

.user-info {
  flex: 1;
  min-width: 0;
}

.user-name {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.user-meta {
  margin-top: 2px;
  font-size: 11px;
  color: var(--text-secondary);
}

.admin-badge {
  color: var(--accent);
}

.user-email {
  color: var(--text-dim);
}

.user-actions {
  display: flex;
  gap: 4px;
}

.action-btn {
  width: 28px;
  height: 28px;
  border: none;
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  transition: all 0.2s;
}

.action-btn:hover {
  background: var(--surface2);
  color: var(--text-primary);
}

.action-btn.logout:hover {
  background: rgba(248, 113, 113, 0.1);
  color: var(--red);
}
</style>

<!-- 非 scoped 样式，用于 Teleport 渲染到 body 的 Modal -->
<style>
.sidebar-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.sidebar-modal-content {
  background: #1e1e2e;
  border: 1px solid #3d3d5c;
  border-radius: 16px;
  width: 90%;
  max-width: 560px;
  box-shadow: 0 25px 80px rgba(0, 0, 0, 0.6);
  overflow: hidden;
}

.sidebar-modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 18px 24px;
  border-bottom: 1px solid #3d3d5c;
  background: #252536;
}

.sidebar-modal-header h3 {
  margin: 0;
  font-size: 17px;
  color: #f0f0f0;
  font-weight: 600;
}

.sidebar-modal-close {
  background: none;
  border: none;
  font-size: 26px;
  color: #666;
  cursor: pointer;
  padding: 0;
  line-height: 1;
  transition: color 0.2s;
}

.sidebar-modal-close:hover {
  color: #fff;
}

.sidebar-modal-body {
  padding: 24px;
}

.sidebar-api-key-hint {
  margin: 0 0 14px;
  font-size: 13px;
  color: #888;
}

.sidebar-api-key-box {
  display: flex;
  gap: 10px;
  padding: 14px 16px;
  background: #252536;
  border-radius: 10px;
  border: 1px solid #3d3d5c;
}

.sidebar-api-key-text {
  flex: 1;
  font-family: 'SF Mono', Monaco, Consolas, monospace;
  font-size: 12px;
  color: #a78bfa;
  word-break: break-all;
  background: none;
  padding: 0;
  line-height: 1.5;
}

.sidebar-btn-copy {
  padding: 8px 16px;
  background: #8b5cf6;
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 12px;
  cursor: pointer;
  white-space: nowrap;
  transition: background 0.2s;
}

.sidebar-btn-copy:hover {
  background: #7c3aed;
}

.sidebar-api-usage {
  margin-top: 20px;
}

.sidebar-api-usage h4 {
  margin: 0 0 10px;
  font-size: 13px;
  color: #f0f0f0;
  font-weight: 500;
}

.sidebar-code-block {
  background: #252536;
  border: 1px solid #3d3d5c;
  border-radius: 8px;
  padding: 14px 16px;
  font-family: 'SF Mono', Monaco, Consolas, monospace;
  font-size: 11px;
  color: #aaa;
  overflow-x: auto;
  white-space: pre-wrap;
  word-break: break-all;
  line-height: 1.6;
}

.sidebar-api-warning {
  margin-top: 20px;
  padding: 12px 16px;
  background: rgba(255, 152, 0, 0.12);
  border: 1px solid rgba(255, 152, 0, 0.35);
  border-radius: 8px;
  font-size: 12px;
  color: #ffb74d;
}

.sidebar-modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 18px 24px;
  border-top: 1px solid #3d3d5c;
  background: #252536;
}

.sidebar-modal-btn {
  padding: 10px 20px;
  border-radius: 8px;
  font-size: 13px;
  cursor: pointer;
  border: none;
  transition: all 0.2s;
}

.sidebar-modal-btn-ghost {
  background: transparent;
  color: #aaa;
  border: 1px solid #3d3d5c;
}

.sidebar-modal-btn-ghost:hover {
  background: #2a2a3e;
  color: #fff;
}

.sidebar-modal-btn-danger {
  background: #dc3545;
  color: white;
}

.sidebar-modal-btn-danger:hover:not(:disabled) {
  background: #c82333;
}

.sidebar-modal-btn-danger:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* 积分记录弹窗样式 */
.credits-log-modal {
  max-width: 480px;
}

.credits-log-loading,
.credits-log-empty {
  text-align: center;
  padding: 40px;
  color: #888;
  font-size: 14px;
}

.credits-log-list {
  max-height: 400px;
  overflow-y: auto;
}

.credits-log-item {
  padding: 12px 0;
  border-bottom: 1px solid #3d3d5c;
}

.credits-log-item:last-child {
  border-bottom: none;
}

.log-left {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 6px;
}

.log-type-badge {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 500;
}

.log-type-badge.deduct {
  background: rgba(245, 34, 45, 0.15);
  color: #f5222d;
}

.log-type-badge.refund {
  background: rgba(82, 196, 26, 0.15);
  color: #52c41a;
}

.log-type-badge.reward {
  background: rgba(24, 144, 255, 0.15);
  color: #1890ff;
}

.log-type-badge.admin_adjust {
  background: rgba(250, 173, 20, 0.15);
  color: #faad14;
}

.log-desc {
  font-size: 12px;
  color: #aaa;
}

.log-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.log-amount.positive {
  color: #52c41a;
  font-weight: 600;
  font-size: 14px;
}

.log-amount.negative {
  color: #f5222d;
  font-weight: 600;
  font-size: 14px;
}

.log-balance {
  font-size: 11px;
  color: #666;
}

.log-time {
  font-size: 10px;
  color: #555;
  margin-top: 4px;
}

.pagination-info {
  font-size: 12px;
  color: #888;
}

.credits-arrow {
  font-size: 18px;
  color: var(--text-dim);
  transition: transform 0.2s;
}

.credits-display:hover .credits-arrow {
  transform: translateX(3px);
}

/* 积分记录列表样式 */
.credits-log-item {
  padding: 12px 0;
  border-bottom: 1px solid #3d3d5c;
}

.credits-log-item:last-child {
  border-bottom: none;
}

.log-left {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.log-type-badge {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
}

.log-type-badge.deduct {
  background: rgba(248, 113, 113, 0.15);
  color: #f87171;
}

.log-type-badge.refund {
  background: rgba(82, 196, 26, 0.15);
  color: #52c41a;
}

.log-type-badge.reward {
  background: rgba(33, 150, 243, 0.15);
  color: #2196f3;
}

.log-type-badge.admin_adjust {
  background: rgba(255, 193, 7, 0.15);
  color: #ffc107;
}

.log-desc {
  font-size: 13px;
  color: #ccc;
}

.log-right {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 4px;
}

.log-amount {
  font-weight: 600;
  font-size: 14px;
}

.log-amount.positive {
  color: #52c41a;
}

.log-amount.negative {
  color: #f87171;
}

.log-balance {
  font-size: 12px;
  color: #888;
}

.log-time {
  font-size: 11px;
  color: #666;
}

.pagination-info {
  font-size: 12px;
  color: #888;
}
</style>
