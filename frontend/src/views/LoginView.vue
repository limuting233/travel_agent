<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, Eye, EyeOff, LockKeyhole, MessageCircle, Smartphone, UserRound } from 'lucide-vue-next'
import { motion } from 'motion-v'
import { toast } from 'vue-sonner'
import { useUserStore } from '@/stores/user'
import { goBack } from '@/utils/navigation'

const router = useRouter()
const route = useRoute()
const user = useUserStore()
const showPassword = ref(false)
const isSubmitting = ref(false)
const form = reactive({
  username: '',
  password: '',
})

const fieldErrors = reactive({
  username: '',
  password: '',
})

function getErrorMessage(error: unknown) {
  if (error instanceof Error) return error.message
  return '登录失败，请稍后重试'
}

function removeChinese(value: string) {
  return value.replace(/[\u3400-\u9fff]/g, '')
}

function validateForm() {
  fieldErrors.username = form.username.trim() ? '' : '请输入用户名'
  fieldErrors.password = form.password ? '' : '请输入密码'

  return !fieldErrors.username && !fieldErrors.password
}

function getRedirectPath() {
  const redirect = route.query.redirect

  if (typeof redirect === 'string' && redirect.startsWith('/') && !redirect.startsWith('//')) {
    return redirect
  }

  return '/profile'
}

function handleUsernameInput(event: Event) {
  const target = event.target as HTMLInputElement
  form.username = removeChinese(target.value)
  target.value = form.username

  if (fieldErrors.username && form.username.trim()) {
    fieldErrors.username = ''
  }
}

function handlePasswordInput(event: Event) {
  const target = event.target as HTMLInputElement
  form.password = removeChinese(target.value)
  target.value = form.password

  if (fieldErrors.password && form.password) {
    fieldErrors.password = ''
  }
}

async function submit() {
  if (isSubmitting.value) return
  if (!validateForm()) return

  isSubmitting.value = true

  try {
    await user.loginWithPassword(form.username.trim(), form.password)
    router.replace(getRedirectPath())
  } catch (error) {
    toast.error(getErrorMessage(error))
  } finally {
    isSubmitting.value = false
  }
}

function leavePage() {
  goBack(router, '/profile')
}

function goRegister() {
  router.replace({
    path: '/register',
    query: route.query.redirect ? { redirect: route.query.redirect } : undefined,
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
      <p class="pb-2 text-sm font-semibold">登录</p>
      <span class="size-9"></span>
    </header>

    <section>
      <h1 class="text-[30px] font-bold leading-tight tracking-normal">欢迎回来</h1>
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

        <label class="flex items-start gap-3 py-4">
          <LockKeyhole class="mt-4 size-5 shrink-0 text-[#6a6a6a]" />
          <span class="min-w-0 flex-1">
            <span class="block text-xs font-medium text-[#6a6a6a]">密码</span>
            <input
              v-model="form.password"
              class="mt-1 h-8 w-full bg-transparent text-base outline-none"
              autocomplete="current-password"
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
      </section>

      <button
        class="mt-7 flex h-14 w-full items-center justify-center rounded-2xl text-base font-semibold text-white transition"
        :class="isSubmitting ? 'bg-[#ffd1da]' : 'bg-[#ff385c]'"
        :disabled="isSubmitting"
        type="submit"
      >
        {{ isSubmitting ? '登录中...' : '登录' }}
      </button>

      <div class="mt-5 flex items-center justify-center gap-1 text-sm">
        <span class="text-[#6a6a6a]">还没有账号？</span>
        <button
          class="font-semibold text-[#222222] underline underline-offset-4"
          type="button"
          @click="goRegister"
        >
          去注册
        </button>
      </div>
    </form>

    <section class="mt-7">
      <div class="flex items-center gap-3">
        <span class="h-px flex-1 bg-[#ebebeb]"></span>
        <span class="text-xs font-medium text-[#6a6a6a]">其他登录方式</span>
        <span class="h-px flex-1 bg-[#ebebeb]"></span>
      </div>

      <div class="mt-5 space-y-3">
        <button
          class="flex h-[52px] w-full items-center justify-between rounded-2xl border border-[#dddddd] px-4 text-left opacity-60"
          disabled
          type="button"
        >
          <span class="flex items-center gap-3">
            <Smartphone class="size-5" />
            <span class="text-sm font-semibold">短信验证码登录</span>
          </span>
          <span class="text-xs font-medium text-[#6a6a6a]">即将支持</span>
        </button>

        <button
          class="flex h-[52px] w-full items-center justify-between rounded-2xl border border-[#dddddd] px-4 text-left opacity-60"
          disabled
          type="button"
        >
          <span class="flex items-center gap-3">
            <MessageCircle class="size-5" />
            <span class="text-sm font-semibold">微信登录</span>
          </span>
          <span class="text-xs font-medium text-[#6a6a6a]">即将支持</span>
        </button>
      </div>
    </section>
  </motion.main>
</template>
