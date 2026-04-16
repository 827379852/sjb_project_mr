<template>
  <div class="admin-page">
    <!-- 顶部导航 -->
    <header class="admin-header">
      <div class="header-left">
        <h1>管理后台</h1>
      </div>
      <div class="header-right">
        <router-link to="/" class="back-link">返回首页</router-link>
      </div>
    </header>

    <!-- Tab 切换 -->
    <div class="tabs">
      <button :class="['tab', activeTab === 'users' ? 'active' : '']" @click="activeTab = 'users'">用户管理</button>
      <button :class="['tab', activeTab === 'credits' ? 'active' : '']" @click="activeTab = 'credits'">积分记录</button>
      <button :class="['tab', activeTab === 'system' ? 'active' : '']" @click="activeTab = 'system'">系统配置</button>
    </div>

    <!-- 用户管理 Tab -->
    <div v-show="activeTab === 'users'">
      <!-- 统计卡片 -->
      <div class="stats-cards">
        <div class="stat-card">
          <div class="stat-value">{{ stats.total_users }}</div>
          <div class="stat-label">总用户数</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">{{ stats.active_users }}</div>
          <div class="stat-label">活跃用户</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">{{ stats.total_credits }}</div>
          <div class="stat-label">总积分</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">{{ stats.default_credits }}</div>
          <div class="stat-label">注册赠送积分</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">{{ stats.task_cost_credits }}</div>
          <div class="stat-label">任务消耗积分</div>
        </div>
      </div>

      <!-- 用户列表 -->
      <div class="users-section">
        <h2>用户管理</h2>

        <!-- 加载中 -->
        <div v-if="loading" class="loading">加载中...</div>

        <!-- 用户表格 -->
        <div v-else class="users-table-wrapper">
          <table class="users-table">
            <thead>
              <tr>
                <th>邮箱</th>
                <th>用户名</th>
                <th>积分</th>
                <th>状态</th>
                <th>角色</th>
                <th>注册时间</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="user in users" :key="user.id" :class="{ 'is-superuser': user.is_superuser }">
                <td>{{ user.email }}</td>
                <td>{{ user.name }}</td>
                <td>
                  <span class="credits">{{ user.credits }}</span>
                </td>
                <td>
                  <span :class="['status', user.is_active ? 'active' : 'inactive']">
                    {{ user.is_active ? '正常' : '已禁用' }}
                  </span>
                </td>
                <td>
                  <span :class="['role', user.is_superuser ? 'superuser' : 'user']">
                    {{ user.is_superuser ? '超级管理员' : '普通用户' }}
                  </span>
                </td>
                <td>{{ formatDate(user.created_at) }}</td>
                <td class="actions">
                  <template v-if="!user.is_superuser">
                    <button @click="openEditModal(user)" class="btn-edit">编辑</button>
                    <button @click="openCreditsModal(user)" class="btn-credits">充值</button>
                    <button @click="resetPassword(user)" class="btn-reset">重置密码</button>
                    <button @click="toggleUserStatus(user)" :class="user.is_active ? 'btn-disable' : 'btn-enable'">
                      {{ user.is_active ? '禁用' : '启用' }}
                    </button>
                    <button @click="deleteUserConfirm(user)" class="btn-delete">删除</button>
                  </template>
                  <span v-else class="superuser-badge">超级管理员</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- 分页 -->
        <div class="pagination">
          <button :disabled="page === 1" @click="changePage(page - 1)">上一页</button>
          <span>第 {{ page }} 页 / 共 {{ totalPages }} 页 (共 {{ total }} 条)</span>
          <button :disabled="page >= totalPages" @click="changePage(page + 1)">下一页</button>
        </div>
      </div>

      <!-- 编辑用户弹窗 -->
      <div v-if="showEditModal" class="modal-overlay" @click.self="closeEditModal">
        <div class="modal">
          <h3>编辑用户</h3>
          <div class="form-group">
            <label>用户名</label>
            <input v-model="editForm.name" type="text" />
          </div>
          <div class="form-group">
            <label>积分</label>
            <input v-model.number="editForm.credits" type="number" min="0" />
          </div>
          <div class="form-group">
            <label>
              <input v-model="editForm.is_active" type="checkbox" />
              账号激活
            </label>
          </div>
          <div class="modal-actions">
            <button @click="saveEdit" class="btn-primary">保存</button>
            <button @click="closeEditModal" class="btn-secondary">取消</button>
          </div>
        </div>
      </div>

      <!-- 充值积分弹窗 -->
      <div v-if="showCreditsModal" class="modal-overlay" @click.self="closeCreditsModal">
        <div class="modal">
          <h3>为 {{ creditsTarget?.name }} 充值积分</h3>
          <div class="form-group">
            <label>充值数量</label>
            <input v-model.number="creditsAmount" type="number" min="1" />
          </div>
          <div class="quick-buttons">
            <button @click="creditsAmount = 10">+10</button>
            <button @click="creditsAmount = 50">+50</button>
            <button @click="creditsAmount = 100">+100</button>
            <button @click="creditsAmount = 500">+500</button>
          </div>
          <div class="modal-actions">
            <button @click="addCredits" class="btn-primary">确认充值</button>
            <button @click="closeCreditsModal" class="btn-secondary">取消</button>
          </div>
        </div>
      </div>
    </div>

    <!-- 积分记录 Tab -->
    <div v-show="activeTab === 'credits'" class="credits-section">
      <h2>积分使用记录</h2>

      <!-- 筛选 -->
      <div class="filters">
        <select v-model="creditLogType" @change="loadCreditLogs">
          <option value="">全部类型</option>
          <option value="deduct">扣除</option>
          <option value="refund">返还</option>
          <option value="reward">奖励</option>
          <option value="admin_adjust">管理员调整</option>
        </select>
      </div>

      <!-- 加载中 -->
      <div v-if="creditLogsLoading" class="loading">加载中...</div>

      <!-- 积分记录表格 -->
      <div v-else class="users-table-wrapper">
        <table class="users-table">
          <thead>
            <tr>
              <th>用户</th>
              <th>邮箱</th>
              <th>类型</th>
              <th>积分变化</th>
              <th>余额</th>
              <th>描述</th>
              <th>时间</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="log in creditLogs" :key="log.id">
              <td>{{ log.user_name || '-' }}</td>
              <td>{{ log.user_email || '-' }}</td>
              <td>
                <span :class="['log-type', log.log_type]">
                  {{ getLogTypeLabel(log.log_type) }}
                </span>
              </td>
              <td>
                <span :class="['amount', log.amount >= 0 ? 'positive' : 'negative']">
                  {{ log.amount >= 0 ? '+' : '' }}{{ log.amount }}
                </span>
              </td>
              <td>{{ log.balance_after }}</td>
              <td>{{ log.description || '-' }}</td>
              <td>{{ formatDate(log.created_at) }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- 分页 -->
      <div class="pagination">
        <button :disabled="creditLogPage === 1" @click="changeCreditLogPage(creditLogPage - 1)">上一页</button>
        <span>第 {{ creditLogPage }} 页 / 共 {{ creditLogTotalPages }} 页 (共 {{ creditLogTotal }} 条)</span>
        <button :disabled="creditLogPage >= creditLogTotalPages" @click="changeCreditLogPage(creditLogPage + 1)">下一页</button>
      </div>
    </div>

    <!-- 系统配置 Tab -->
    <div v-show="activeTab === 'system'" class="system-section">
      <h2>系统配置</h2>

      <!-- 队列状态卡片 -->
      <div class="queue-status-card">
        <div class="card-header">
          <h3>任务队列状态</h3>
        </div>
        <div class="queue-stats">
          <div class="queue-stat">
            <div class="stat-value">{{ queueStatus.running || 0 }}</div>
            <div class="stat-label">执行中</div>
          </div>
          <div class="queue-stat">
            <div class="stat-value">{{ queueStatus.queued || 0 }}</div>
            <div class="stat-label">排队中</div>
          </div>
          <div class="queue-stat">
            <div class="stat-value">{{ queueStatus.max_concurrent || 4 }}</div>
            <div class="stat-label">最大并行</div>
          </div>
        </div>
        <button @click="loadQueueStatus" class="btn-refresh">刷新状态</button>
      </div>

      <!-- 配置卡片 -->
      <div class="config-cards">
        <div class="config-card" v-for="config in systemConfigs" :key="config.key">
          <div class="config-header">
            <div class="config-title">{{ getConfigLabel(config.key) }}</div>
            <div class="config-desc">{{ config.description }}</div>
          </div>
          <div class="config-body">
            <input
              :type="config.config_type === 'int' ? 'number' : 'text'"
              v-model="config.value"
              :min="config.key === 'max_concurrent_users' ? 1 : undefined"
              :max="config.key === 'max_concurrent_users' ? 10 : undefined"
              @change="updateConfig(config.key, config.value)"
            />
          </div>
          <div class="config-footer">
            <span class="config-updated">更新于 {{ formatDate(config.updated_at) }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useAdminApi } from '@/composables/useAdminApi'
import { useAuthStore } from '@/stores/authStore'
import { useRouter } from 'vue-router'

const router = useRouter()
const authStore = useAuthStore()
const adminApi = useAdminApi()

// 检查权限
if (!authStore.isSuperuser) {
  router.push('/')
}

// 状态
const loading = ref(false)
const users = ref<any[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)

const stats = ref({
  total_users: 0,
  active_users: 0,
  total_credits: 0,
  default_credits: 100,
  task_cost_credits: 10,
})

// 编辑弹窗
const showEditModal = ref(false)
const editForm = ref({ name: '', credits: 0, is_active: true })
const editingUser = ref<any>(null)

// 充值弹窗
const showCreditsModal = ref(false)
const creditsTarget = ref<any>(null)
const creditsAmount = ref(100)

// Tab 切换
const activeTab = ref('users')

// 积分记录
const creditLogs = ref<any[]>([])
const creditLogTotal = ref(0)
const creditLogPage = ref(1)
const creditLogType = ref('')
const creditLogsLoading = ref(false)

// 系统配置
const systemConfigs = ref<any[]>([])
const queueStatus = ref({
  running: 0,
  queued: 0,
  max_concurrent: 4,
})

// 计算属性
const totalPages = computed(() => Math.ceil(total.value / pageSize.value))
const creditLogTotalPages = computed(() => Math.ceil(creditLogTotal.value / pageSize.value))

// 加载数据
async function loadStats() {
  try {
    stats.value = await adminApi.getStats()
  } catch (e) {
    console.error('加载统计失败', e)
  }
}

async function loadUsers() {
  loading.value = true
  try {
    const res = await adminApi.listUsers(page.value, pageSize.value)
    users.value = res.items
    total.value = res.total
  } catch (e) {
    console.error('加载用户失败', e)
  } finally {
    loading.value = false
  }
}

function changePage(newPage: number) {
  page.value = newPage
  loadUsers()
}

// 格式化日期
function formatDate(dateStr: string) {
  return new Date(dateStr).toLocaleString('zh-CN')
}

// 编辑用户
function openEditModal(user: any) {
  editingUser.value = user
  editForm.value = {
    name: user.name,
    credits: user.credits,
    is_active: user.is_active,
  }
  showEditModal.value = true
}

function closeEditModal() {
  showEditModal.value = false
  editingUser.value = null
}

async function saveEdit() {
  if (!editingUser.value) return
  try {
    const updated = await adminApi.updateUser(editingUser.value.id, editForm.value)
    Object.assign(editingUser.value, updated)
    closeEditModal()
    loadStats()
  } catch (e: any) {
    alert('保存失败: ' + e.message)
  }
}

// 充值积分
function openCreditsModal(user: any) {
  creditsTarget.value = user
  creditsAmount.value = 100
  showCreditsModal.value = true
}

function closeCreditsModal() {
  showCreditsModal.value = false
  creditsTarget.value = null
}

// 积分记录
async function loadCreditLogs() {
  creditLogsLoading.value = true
  try {
    const res = await adminApi.listCreditLogs(creditLogPage.value, pageSize.value, undefined, creditLogType.value || undefined)
    creditLogs.value = res.items
    creditLogTotal.value = res.total
  } catch (e) {
    console.error('加载积分记录失败', e)
  } finally {
    creditLogsLoading.value = false
  }
}

function changeCreditLogPage(newPage: number) {
  creditLogPage.value = newPage
  loadCreditLogs()
}

function getLogTypeLabel(type: string): string {
  const labels: Record<string, string> = {
    deduct: '扣除',
    refund: '返还',
    reward: '奖励',
    admin_adjust: '管理员调整',
  }
  return labels[type] || type
}

// 监听 Tab 切换
watch(activeTab, (newTab) => {
  if (newTab === 'credits') {
    loadCreditLogs()
  } else if (newTab === 'system') {
    loadSystemConfigs()
    loadQueueStatus()
  }
})

async function addCredits() {
  if (!creditsTarget.value || creditsAmount.value <= 0) return
  try {
    const updated = await adminApi.addCredits(creditsTarget.value.id, creditsAmount.value)
    Object.assign(creditsTarget.value, updated)
    closeCreditsModal()
    loadStats()
  } catch (e: any) {
    alert('充值失败: ' + e.message)
  }
}

// 重置密码
async function resetPassword(user: any) {
  if (!confirm(`确定要重置用户 ${user.name} 的密码为 123456 吗？`)) return
  try {
    await adminApi.resetPassword(user.id)
    alert('密码已重置为 123456')
  } catch (e: any) {
    alert('重置失败: ' + e.message)
  }
}

// 切换用户状态
async function toggleUserStatus(user: any) {
  const action = user.is_active ? '禁用' : '启用'
  if (!confirm(`确定要${action}用户 ${user.name} 吗？`)) return
  try {
    const updated = await adminApi.updateUser(user.id, { is_active: !user.is_active })
    Object.assign(user, updated)
    loadStats()
  } catch (e: any) {
    alert(`${action}失败: ` + e.message)
  }
}

// 删除用户
async function deleteUserConfirm(user: any) {
  if (!confirm(`确定要删除用户 ${user.name} 吗？此操作不可恢复！`)) return
  try {
    await adminApi.deleteUser(user.id)
    loadUsers()
    loadStats()
  } catch (e: any) {
    alert('删除失败: ' + e.message)
  }
}

// 系统配置相关
async function loadSystemConfigs() {
  try {
    systemConfigs.value = await adminApi.getSystemConfigs()
  } catch (e) {
    console.error('加载系统配置失败', e)
  }
}

async function loadQueueStatus() {
  try {
    queueStatus.value = await adminApi.getQueueStatus()
  } catch (e) {
    console.error('加载队列状态失败', e)
  }
}

async function updateConfig(key: string, value: any) {
  try {
    await adminApi.updateSystemConfig(key, String(value))
    // 更新成功，重新加载
    await loadSystemConfigs()
    if (key === 'max_concurrent_users') {
      await loadQueueStatus()
    }
  } catch (e: any) {
    console.error('更新配置失败', e)
    alert('更新配置失败: ' + (e.message || JSON.stringify(e)))
  }
}

function getConfigLabel(key: string): string {
  const labels: Record<string, string> = {
    'max_concurrent_users': '最大并行用户数',
    'xhs_max_posts_per_persona': '每个人设最大帖子数',
    'xhs_max_comments_per_post': '每篇帖子最大评论数',
  }
  return labels[key] || key
}

// 初始化
onMounted(() => {
  loadStats()
  loadUsers()
  loadCreditLogs()
})
</script>

<style scoped>
.admin-page {
  min-height: 100vh;
  background: #f5f7fa;
  padding: 20px;
}

.admin-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  padding: 16px 24px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.admin-header h1 {
  font-size: 24px;
  font-weight: 600;
  color: #1a1a1a;
  margin: 0;
}

.back-link {
  color: #409eff;
  text-decoration: none;
}

.back-link:hover {
  text-decoration: underline;
}

.stats-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}

.stat-card {
  background: white;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  text-align: center;
}

.stat-value {
  font-size: 32px;
  font-weight: 700;
  color: #409eff;
}

.stat-label {
  font-size: 14px;
  color: #666;
  margin-top: 8px;
}

.users-section {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  padding: 24px;
}

.users-section h2 {
  font-size: 18px;
  font-weight: 600;
  margin: 0 0 20px 0;
  color: #1a1a1a;
}

.loading {
  text-align: center;
  padding: 40px;
  color: #999;
}

.users-table-wrapper {
  overflow-x: auto;
}

.users-table {
  width: 100%;
  border-collapse: collapse;
}

.users-table th,
.users-table td {
  padding: 12px 16px;
  text-align: left;
  border-bottom: 1px solid #eee;
}

.users-table th {
  background: #f9fafb;
  font-weight: 600;
  color: #666;
  font-size: 13px;
}

.users-table tr:hover {
  background: #f9fafb;
}

.users-table tr.is-superuser {
  background: #fffbe6;
}

.credits {
  font-weight: 600;
  color: #e6a23c;
}

.status {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
}

.status.active {
  background: #e6f7e6;
  color: #52c41a;
}

.status.inactive {
  background: #fff1f0;
  color: #f5222d;
}

.role {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
}

.role.superuser {
  background: #e6f7ff;
  color: #1890ff;
}

.role.user {
  background: #f5f5f5;
  color: #666;
}

.actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.actions button {
  padding: 4px 10px;
  border: none;
  border-radius: 4px;
  font-size: 12px;
  cursor: pointer;
  transition: opacity 0.2s;
}

.actions button:hover {
  opacity: 0.8;
}

.btn-edit {
  background: #409eff;
  color: white;
}

.btn-credits {
  background: #e6a23c;
  color: white;
}

.btn-reset {
  background: #909399;
  color: white;
}

.btn-disable {
  background: #f56c6c;
  color: white;
}

.btn-enable {
  background: #67c23a;
  color: white;
}

.btn-delete {
  background: #f56c6c;
  color: white;
}

.superuser-badge {
  color: #999;
  font-size: 12px;
}

.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 16px;
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid #eee;
}

.pagination button {
  padding: 8px 16px;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  background: white;
  cursor: pointer;
}

.pagination button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.pagination span {
  color: #666;
}

/* Modal */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal {
  background: white;
  border-radius: 8px;
  padding: 24px;
  width: 400px;
  max-width: 90%;
}

.modal h3 {
  margin: 0 0 20px 0;
  font-size: 18px;
  font-weight: 600;
}

.form-group {
  margin-bottom: 16px;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  font-weight: 500;
  color: #333;
}

.form-group input[type="text"],
.form-group input[type="number"] {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  font-size: 14px;
}

.form-group input[type="checkbox"] {
  margin-right: 8px;
}

.quick-buttons {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
}

.quick-buttons button {
  flex: 1;
  padding: 8px;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  background: #f5f5f5;
  cursor: pointer;
}

.quick-buttons button:hover {
  background: #e6e6e6;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

.btn-primary {
  padding: 8px 20px;
  border: none;
  border-radius: 4px;
  background: #409eff;
  color: white;
  cursor: pointer;
}

.btn-secondary {
  padding: 8px 20px;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  background: white;
  cursor: pointer;
}

/* Tab 切换 */
.tabs {
  display: flex;
  gap: 12px;
  margin-bottom: 24px;
  background: white;
  padding: 12px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.tab {
  padding: 10px 24px;
  border: none;
  border-radius: 6px;
  background: #f5f5f5;
  color: #666;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.2s;
}

.tab.active {
  background: #409eff;
  color: white;
}

.tab:hover:not(.active) {
  background: #e6e6e6;
}

/* 积分记录 */
.credits-section {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  padding: 24px;
}

.credits-section h2 {
  font-size: 18px;
  font-weight: 600;
  margin: 0 0 20px 0;
  color: #1a1a1a;
}

.filters {
  margin-bottom: 16px;
}

.filters select {
  padding: 8px 12px;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  font-size: 14px;
}

.log-type {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
}

.log-type.deduct {
  background: #fff1f0;
  color: #f5222d;
}

.log-type.refund {
  background: #e6f7e6;
  color: #52c41a;
}

.log-type.reward {
  background: #e6f7ff;
  color: #1890ff;
}

.log-type.admin_adjust {
  background: #fffbe6;
  color: #faad14;
}

.amount.positive {
  color: #52c41a;
  font-weight: 600;
}

.amount.negative {
  color: #f5222d;
  font-weight: 600;
}

/* 系统配置 */
.system-section {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  padding: 24px;
}

.system-section h2 {
  font-size: 18px;
  font-weight: 600;
  margin: 0 0 20px 0;
  color: #1a1a1a;
}

.queue-status-card {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 12px;
  padding: 24px;
  color: white;
  margin-bottom: 24px;
}

.queue-status-card .card-header h3 {
  margin: 0 0 20px 0;
  font-size: 16px;
  font-weight: 600;
}

.queue-stats {
  display: flex;
  gap: 40px;
}

.queue-stat {
  text-align: center;
}

.queue-stat .stat-value {
  font-size: 36px;
  font-weight: 700;
}

.queue-stat .stat-label {
  font-size: 14px;
  opacity: 0.9;
  margin-top: 4px;
}

.btn-refresh {
  margin-top: 16px;
  padding: 8px 16px;
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.1);
  color: white;
  cursor: pointer;
  font-size: 13px;
}

.btn-refresh:hover {
  background: rgba(255, 255, 255, 0.2);
}

.config-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 16px;
}

.config-card {
  background: #f9fafb;
  border-radius: 8px;
  padding: 20px;
  border: 1px solid #eee;
}

.config-header {
  margin-bottom: 12px;
}

.config-title {
  font-size: 16px;
  font-weight: 600;
  color: #1a1a1a;
}

.config-desc {
  font-size: 13px;
  color: #666;
  margin-top: 4px;
}

.config-body input {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #d9d9d9;
  border-radius: 6px;
  font-size: 16px;
  font-weight: 600;
}

.config-footer {
  margin-top: 8px;
}

.config-updated {
  font-size: 12px;
  color: #999;
}
</style>
