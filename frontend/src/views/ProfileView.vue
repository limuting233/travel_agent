<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowDown, Bell, ChevronRight, LogIn, LogOut, MapPinned, MessageCircle, Settings, ShieldCheck } from 'lucide-vue-next'
import { motion } from 'motion-v'
import { toast } from 'vue-sonner'
import { AlertDialog } from '@/components/ui/alert-dialog'
import { useUserStore } from '@/stores/user'
import { goBack } from '@/utils/navigation'

const router = useRouter()
const user = useUserStore()
const isLeaving = ref(false)
const isLogoutDialogOpen = ref(false)

const menu = [
  {
    label: '我的行程',
    desc: '查看已生成的方案',
    icon: MapPinned,
    path: '/trips',
  },
  {
    label: '消息通知',
    desc: '行程提醒和客服消息',
    icon: Bell,
    path: '',
  },
  {
    label: '安全与隐私',
    desc: '账号安全、授权和数据管理',
    icon: ShieldCheck,
    path: '',
  },
]

function leaveToHome() {
  if (isLeaving.value) return

  isLeaving.value = true
  window.setTimeout(() => {
    goBack(router)
  }, 260)
}

function openMenu(path: string) {
  if (!path) return
  router.push(path)
}

function confirmLogout() {
  user.logout()
  isLogoutDialogOpen.value = false
  toast.success('已退出登录')
  router.replace('/')
}
</script>

<template>
  <motion.main
    class="mx-auto min-h-screen max-w-[430px] bg-white px-5 pb-28 pt-[calc(env(safe-area-inset-top)+72px)] text-[#222222]"
    :initial="{ opacity: 0, y: 96 }"
    :animate="isLeaving ? { opacity: 0, y: 96 } : { opacity: 1, y: 0 }"
    :transition="{ duration: isLeaving ? 0.26 : 0.32, ease: 'easeOut' }"
  >
    <header class="fixed left-1/2 top-0 z-40 flex h-[calc(env(safe-area-inset-top)+56px)] w-full max-w-[430px] -translate-x-1/2 items-end justify-between bg-white/95 px-5 pb-3 backdrop-blur">
      <button
        class="flex size-9 items-center justify-center rounded-full bg-[#f2f2f2]"
        type="button"
        aria-label="返回上一页"
        @click="leaveToHome"
      >
        <ArrowDown class="size-4" />
      </button>
      <p class="pb-2 text-sm font-semibold">我的</p>
      <button class="flex size-9 items-center justify-center rounded-full bg-[#f2f2f2]" aria-label="设置">
        <Settings class="size-5" />
      </button>
    </header>

    <section class="rounded-[24px] border border-[#ebebeb] bg-white p-5 shadow-[0_4px_18px_rgba(0,0,0,0.06)]">
      <div class="flex items-center gap-4">
        <div class="flex size-16 items-center justify-center rounded-full bg-[#ff385c] text-xl font-bold text-white">
          旅
        </div>
        <div class="min-w-0 flex-1">
          <h2 class="truncate text-xl font-semibold">{{ user.nickname || '未登录用户' }}</h2>
          <p v-if="user.isLoggedIn && user.username" class="mt-1 truncate text-sm text-[#6a6a6a]">{{ user.username }}</p>
        </div>
      </div>

      <RouterLink
        v-if="!user.isLoggedIn"
        to="/login"
        class="mt-5 flex h-12 w-full items-center justify-center gap-2 rounded-xl bg-[#ff385c] text-base font-medium text-white"
      >
        <LogIn class="size-5" />
        登录后同步行程
      </RouterLink>
      <p v-else class="mt-4 text-sm font-medium text-[#008a05]">已登录，行程会自动同步</p>
    </section>

    <section class="mt-8">
      <h2 class="text-[21px] font-bold leading-tight">常用功能</h2>
      <div class="mt-4 overflow-hidden rounded-[20px] border border-[#ebebeb]">
        <button
          v-for="item in menu"
          :key="item.label"
          class="flex w-full items-center gap-3 border-b border-[#ebebeb] bg-white p-4 text-left last:border-b-0"
          type="button"
          @click="openMenu(item.path)"
        >
          <span class="flex size-10 shrink-0 items-center justify-center rounded-full bg-[#f2f2f2]">
            <component :is="item.icon" class="size-5" />
          </span>
          <span class="min-w-0 flex-1">
            <span class="block text-base font-semibold">{{ item.label }}</span>
            <span class="mt-0.5 block truncate text-sm text-[#6a6a6a]">{{ item.desc }}</span>
          </span>
          <ChevronRight class="size-5 shrink-0 text-[#929292]" />
        </button>
      </div>
    </section>

    <button class="mt-6 flex w-full items-center justify-center gap-2 rounded-full border border-[#dddddd] py-3 text-sm font-medium">
      <MessageCircle class="size-4" />
      联系客服
    </button>

    <button
      v-if="user.isLoggedIn"
      class="mt-3 flex w-full items-center justify-center gap-2 rounded-full border border-[#dddddd] py-3 text-sm font-semibold text-[#c13515]"
      type="button"
      @click="isLogoutDialogOpen = true"
    >
      <LogOut class="size-4" />
      退出登录
    </button>

    <AlertDialog v-model:open="isLogoutDialogOpen">
      <div>
        <h2 class="text-lg font-semibold leading-7">退出登录？</h2>
        <p class="mt-2 text-sm leading-6 text-[#6a6a6a]">
          你将退出当前账号。
        </p>
      </div>

      <div class="mt-6 flex gap-3">
        <button
          class="flex h-11 flex-1 items-center justify-center rounded-xl border border-[#dddddd] text-sm font-semibold text-[#222222]"
          type="button"
          @click="isLogoutDialogOpen = false"
        >
          取消
        </button>
        <button
          class="flex h-11 flex-1 items-center justify-center rounded-xl bg-[#c13515] text-sm font-semibold text-white"
          type="button"
          @click="confirmLogout"
        >
          退出
        </button>
      </div>
    </AlertDialog>
  </motion.main>
</template>
