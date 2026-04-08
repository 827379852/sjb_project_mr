<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthApi } from '@/composables'

const router = useRouter()
const { register } = useAuthApi()

const email = ref('')
const password = ref('')
const confirmPassword = ref('')
const name = ref('')
const loading = ref(false)
const errorMsg = ref('')
const successMsg = ref('')

async function handleRegister() {
  if (!email.value || !password.value || !name.value) {
    errorMsg.value = '请填写所有必填项'
    return
  }

  if (password.value !== confirmPassword.value) {
    errorMsg.value = '两次输入的密码不一致'
    return
  }

  if (password.value.length < 6) {
    errorMsg.value = '密码至少需要 6 个字符'
    return
  }

  loading.value = true
  errorMsg.value = ''
  successMsg.value = ''

  const result = await register(email.value, password.value, name.value)

  if (result.success) {
    successMsg.value = result.message
    setTimeout(() => {
      router.push('/login')
    }, 1500)
  } else {
    errorMsg.value = result.message
  }

  loading.value = false
}

function goToLogin() {
  router.push('/login')
}
</script>

<template>
  <div class="auth-page">
    <div class="auth-container">
      <div class="auth-logo">
        <span class="logo-icon">🔬</span>
        <span class="logo-text">ResearchMind</span>
      </div>

      <h1 class="auth-title">注册</h1>

      <form class="auth-form" @submit.prevent="handleRegister">
        <div class="form-group">
          <label for="name">用户名</label>
          <input
            id="name"
            v-model="name"
            type="text"
            placeholder="请输入用户名"
            :disabled="loading"
          />
        </div>

        <div class="form-group">
          <label for="email">邮箱</label>
          <input
            id="email"
            v-model="email"
            type="email"
            placeholder="请输入邮箱"
            :disabled="loading"
          />
        </div>

        <div class="form-group">
          <label for="password">密码</label>
          <input
            id="password"
            v-model="password"
            type="password"
            placeholder="请输入密码（至少 6 位）"
            :disabled="loading"
          />
        </div>

        <div class="form-group">
          <label for="confirmPassword">确认密码</label>
          <input
            id="confirmPassword"
            v-model="confirmPassword"
            type="password"
            placeholder="请再次输入密码"
            :disabled="loading"
          />
        </div>

        <div v-if="errorMsg" class="error-msg">{{ errorMsg }}</div>
        <div v-if="successMsg" class="success-msg">{{ successMsg }}</div>

        <button type="submit" class="auth-btn" :disabled="loading">
          {{ loading ? '注册中...' : '注册' }}
        </button>
      </form>

      <div class="auth-footer">
        <span>已有账号？</span>
        <a @click="goToLogin">立即登录</a>
      </div>
    </div>
  </div>
</template>

<style scoped>
.auth-page {
  width: 100%;
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.auth-container {
  width: 100%;
  max-width: 400px;
  padding: 40px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.15);
}

.auth-logo {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  margin-bottom: 30px;
}

.logo-icon {
  font-size: 32px;
}

.logo-text {
  font-size: 24px;
  font-weight: 600;
  color: #333;
}

.auth-title {
  text-align: center;
  font-size: 20px;
  color: #333;
  margin-bottom: 24px;
}

.auth-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-group label {
  font-size: 14px;
  color: #555;
}

.form-group input {
  padding: 12px 14px;
  border: 1px solid #ddd;
  border-radius: 8px;
  font-size: 14px;
  transition: border-color 0.2s;
}

.form-group input:focus {
  outline: none;
  border-color: #667eea;
}

.form-group input:disabled {
  background: #f5f5f5;
}

.error-msg {
  color: #e74c3c;
  font-size: 13px;
  text-align: center;
}

.success-msg {
  color: #27ae60;
  font-size: 13px;
  text-align: center;
}

.auth-btn {
  padding: 12px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 15px;
  font-weight: 500;
  cursor: pointer;
  transition: opacity 0.2s;
}

.auth-btn:hover:not(:disabled) {
  opacity: 0.9;
}

.auth-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.auth-footer {
  margin-top: 20px;
  text-align: center;
  font-size: 14px;
  color: #666;
}

.auth-footer a {
  color: #667eea;
  cursor: pointer;
  margin-left: 4px;
}

.auth-footer a:hover {
  text-decoration: underline;
}
</style>
