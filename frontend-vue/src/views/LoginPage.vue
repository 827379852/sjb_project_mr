<script setup lang="ts">
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthApi } from '@/composables'

const router = useRouter()
const route = useRoute()
const { login } = useAuthApi()

const email = ref('')
const password = ref('')
const loading = ref(false)
const errorMsg = ref('')

async function handleLogin() {
  if (!email.value || !password.value) {
    errorMsg.value = '请填写邮箱和密码'
    return
  }

  loading.value = true
  errorMsg.value = ''

  const result = await login(email.value, password.value)

  if (result.success) {
    const redirect = route.query.redirect as string || '/'
    router.push(redirect)
  } else {
    errorMsg.value = result.message
  }

  loading.value = false
}

function goToRegister() {
  router.push('/register')
}
</script>

<template>
  <div class="auth-page">
    <div class="auth-container">
      <div class="auth-logo">
        <span class="logo-icon">🔬</span>
        <span class="logo-text">ResearchMind</span>
      </div>

      <h1 class="auth-title">登录</h1>

      <form class="auth-form" @submit.prevent="handleLogin">
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
            placeholder="请输入密码"
            :disabled="loading"
          />
        </div>

        <div v-if="errorMsg" class="error-msg">{{ errorMsg }}</div>

        <button type="submit" class="auth-btn" :disabled="loading">
          {{ loading ? '登录中...' : '登录' }}
        </button>
      </form>

      <div class="auth-footer">
        <span>还没有账号？</span>
        <a @click="goToRegister">立即注册</a>
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
