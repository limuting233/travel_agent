<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, Eye, EyeOff, LockKeyhole, UserRound } from 'lucide-vue-next'
import { motion } from 'motion-v'
import { toast } from 'vue-sonner'
import { register } from '@/api/auth'
import { goBack } from '@/utils/navigation'

const router = useRouter()
const route = useRoute()
const showPassword = ref(false)
const showConfirmPassword = ref(false)
const isSubmitting = ref(false)

const form = reactive({
  username: '',
  password: '',
  confirmPassword: '',
})

const fieldErrors = reactive({
  username: '',
  password: '',
  confirmPassword: '',
})

function removeChinese(value: string) {
  return value.replace(/[\u3400-\u9fff]/g, '')
}

function getErrorMessage(error: unknown) {
  if (error instanceof Error) return error.message
  return '注册失败，请稍后重试'
}

function handleUsernameInput(event: Event) {
  const target = event.target as HTMLInputElement
  form.username = removeChinese(target.value).replace(/[^A-Za-z0-9_]/g, '')
  target.value = form.username

  if (fieldErrors.username) {
    fieldErrors.username = ''
  }
}

function handlePasswordInput(event: Event) {
  const target = event.target as HTMLInputElement
  form.password = removeChinese(target.value)
  target.value = form.password

  if (fieldErrors.password) {
    fieldErrors.password = ''
  }
}

function handleConfirmPasswordInput(event: Event) {
  const target = event.target as HTMLInputElement
  form.confirmPassword = removeChinese(target.value)
  target.value = form.confirmPassword

  if (fieldErrors.confirmPassword) {
    fieldErrors.confirmPassword = ''
  }
}

function validateForm() {
  const username = form.username.trim()
  const hasLetter = /[A-Za-z]/.test(form.password)
  const hasNumber = /\d/.test(form.password)
  const hasSpecial = /[!@#$%^&*()_+\-=[\]{};':"\\|,.<>/?`~]/.test(form.password)

  fieldErrors.username = ''
  fieldErrors.password = ''
  fieldErrors.confirmPassword = ''

  if (!username) {
    fieldErrors.username = '请输入用户名'
  } else if (!/^[A-Za-z0-9_]{5,20}$/.test(username)) {
    fieldErrors.username = '用户名需为 5-20 位字母、数字或下划线'
  }

  if (!form.password) {
    fieldErrors.password = '请输入密码'
  } else if (form.password.length < 8 || form.password.length > 32) {
    fieldErrors.password = '密码需为 8-32 位'
  } else if (!hasLetter || !hasNumber || !hasSpecial) {
    fieldErrors.password = '密码需包含字母、数字和特殊字符'
  }

  if (!form.confirmPassword) {
    fieldErrors.confirmPassword = '请再次输入密码'
  } else if (form.password !== form.confirmPassword) {
    fieldErrors.confirmPassword = '两次输入的密码不一致'
  }

  return !fieldErrors.username && !fieldErrors.password && !fieldErrors.confirmPassword
}

function getRedirectQuery() {
  const redirect = route.query.redirect

  return typeof redirect === 'string' && redirect.startsWith('/') && !redirect.startsWith('//')
    ? { redirect }
    : undefined
}

async function submit() {
  if (isSubmitting.value) return
  if (!validateForm()) return

  isSubmitting.value = true

  try {
    await register({
      username: form.username.trim(),
      password: form.password,
    })
    toast.success('注册成功，请登录')
    router.replace({
      path: '/login',
      query: getRedirectQuery(),
    })
  } catch (error) {
    toast.error(getErrorMessage(error))
  } finally {
    isSubmitting.value = false
  }
}

function leavePage() {
  goBack(router, '/login')
}

function goLogin() {
  router.replace({
    path: '/login',
    query: getRedirectQuery(),
  })
}
</script>

<template>
  <motion.main
    class="mx-auto min-h-screen w-full max-w-[430px] overflow-x-hidden bg-white px-5 pb-8 pt-[calc(env(safe-area-inset-top)+74px)] text-[#222222]"
    :initial="{ opacity: 0, y: 16 }"
    :animate="{ opacity: 1, y: 0 }"
    :transition="{ duration: 0.35, ease: 'easeOut' }"
  >
    <header class="fixed left-1/2 top-0 z-40 flex h-[calc(env(safe-area-inset-top)+56px)] w-full max-w-[430px] -translate-x-1/2 items-end justify-between bg-white/95 px-5 pb-3 backdrop-blur">
      <button
        class="flex size-9 items-center justify-center rounded-full bg-[#f2f2f2]"
        type="button"
        aria-label="返回上一页"
        @click="leavePage"
      >
        <ArrowLeft class="size-4" />
      </button>
      <p class="pb-2 text-sm font-semibold">注册</p>
      <span class="size-9"></span>
    </header>

    <section>
      <h1 class="text-[30px] font-bold leading-tight tracking-normal">创建账号</h1>
    </section>

    <form class="mt-9" @submit.prevent="submit">
      <section>
        <label class="flex items-start gap-3 border-b border-[#ebebeb] py-4">
          <UserRound class="mt-4 size-5 shrink-0 text-[#6a6a6a]" />
          <span class="min-w-0 flex-1">
            <span class="block text-xs font-medium text-[#6a6a6a]">用户名</span>
            <input
              v-model="form.username"
              class="mt-1 h-8 w-full bg-transparent text-base outline-none"
              autocomplete="username"
              placeholder="请输入用户名"
              type="text"
              @input="handleUsernameInput"
            >
            <span v-if="fieldErrors.username" class="mt-1 block text-xs font-medium text-[#c13515]">
              {{ fieldErrors.username }}
            </span>
          </span>
        </label>

        <label class="flex items-start gap-3 border-b border-[#ebebeb] py-4">
          <LockKeyhole class="mt-4 size-5 shrink-0 text-[#6a6a6a]" />
          <span class="min-w-0 flex-1">
            <span class="block text-xs font-medium text-[#6a6a6a]">密码</span>
            <input
              v-model="form.password"
              class="mt-1 h-8 w-full bg-transparent text-base outline-none"
              autocomplete="new-password"
              placeholder="请输入密码"
              :type="showPassword ? 'text' : 'password'"
              @input="handlePasswordInput"
            >
            <span v-if="fieldErrors.password" class="mt-1 block text-xs font-medium text-[#c13515]">
              {{ fieldErrors.password }}
            </span>
          </span>
          <button
            class="mt-2 flex size-9 shrink-0 items-center justify-center rounded-full text-[#6a6a6a]"
            type="button"
            :aria-label="showPassword ? '隐藏密码' : '显示密码'"
            @click="showPassword = !showPassword"
          >
            <EyeOff v-if="showPassword" class="size-5" />
            <Eye v-else class="size-5" />
          </button>
        </label>

        <label class="flex items-start gap-3 py-4">
          <LockKeyhole class="mt-4 size-5 shrink-0 text-[#6a6a6a]" />
          <span class="min-w-0 flex-1">
            <span class="block text-xs font-medium text-[#6a6a6a]">确认密码</span>
            <input
              v-model="form.confirmPassword"
              class="mt-1 h-8 w-full bg-transparent text-base outline-none"
              autocomplete="new-password"
              placeholder="请再次输入密码"
              :type="showConfirmPassword ? 'text' : 'password'"
              @input="handleConfirmPasswordInput"
            >
            <span v-if="fieldErrors.confirmPassword" class="mt-1 block text-xs font-medium text-[#c13515]">
              {{ fieldErrors.confirmPassword }}
            </span>
          </span>
          <button
            class="mt-2 flex size-9 shrink-0 items-center justify-center rounded-full text-[#6a6a6a]"
            type="button"
            :aria-label="showConfirmPassword ? '隐藏确认密码' : '显示确认密码'"
            @click="showConfirmPassword = !showConfirmPassword"
          >
            <EyeOff v-if="showConfirmPassword" class="size-5" />
            <Eye v-else class="size-5" />
          </button>
        </label>
      </section>

      <button
        class="mt-7 flex h-14 w-full items-center justify-center rounded-2xl text-base font-semibold text-white transition"
        :class="isSubmitting ? 'bg-[#ffd1da]' : 'bg-[#ff385c]'"
        :disabled="isSubmitting"
        type="submit"
      >
        {{ isSubmitting ? '注册中...' : '创建账号' }}
      </button>

      <div class="mt-5 flex items-center justify-center gap-1 text-sm">
        <span class="text-[#6a6a6a]">已有账号？</span>
        <button
          class="font-semibold text-[#222222] underline underline-offset-4"
          type="button"
          @click="goLogin"
        >
          去登录
        </button>
      </div>
    </form>
  </motion.main>
</template>
