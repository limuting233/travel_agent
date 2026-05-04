<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { motion } from 'motion-v'
import { toast } from 'vue-sonner'
import { createTravelPlan, type TravelPlanStreamMessage } from '@/api/travel'
import { useTravelStore } from '@/stores/travel'

const router = useRouter()
const travel = useTravelStore()
const isPlanning = ref(false)
const statusText = ref('正在规划中')
const tripId = ref('')
const errorMessage = ref('')
const streamContent = ref('')

let abortController: AbortController | null = null

function getErrorMessage(error: unknown) {
  if (error instanceof Error) return error.message
  return '行程生成失败，请稍后重试'
}

function handlePlanEvent(message: TravelPlanStreamMessage) {
  const data = message.data

  if (message.event === 'start' && 'trip_id' in data && typeof data.trip_id === 'string') {
    tripId.value = data.trip_id
    statusText.value = '已开始规划'
    return
  }

  if ((message.event === 'agent_step' || message.event === 'tool_call') && 'message' in data && typeof data.message === 'string') {
    statusText.value = data.message
    return
  }

  if (message.event === 'message' && 'content' in data && typeof data.content === 'string') {
    streamContent.value += data.content
    return
  }

  if (message.event === 'done' && 'trip_id' in data && typeof data.trip_id === 'string') {
    tripId.value = data.trip_id
    statusText.value = '规划完成'
    return
  }

  if (message.event === 'error' && 'error_message' in data && typeof data.error_message === 'string') {
    throw new Error(data.error_message)
  }
}

async function startPlanning() {
  if (isPlanning.value) return

  const plan = travel.pendingPlan

  if (!plan) {
    toast.error('请先填写行程信息')
    router.replace('/trip/create')
    return
  }

  isPlanning.value = true
  errorMessage.value = ''
  statusText.value = '正在规划中'
  streamContent.value = ''
  tripId.value = ''
  abortController = new AbortController()

  try {
    await createTravelPlan(plan, {
      signal: abortController.signal,
      onEvent: handlePlanEvent,
    })

    if (!tripId.value) {
      throw new Error('规划已结束，但没有返回行程 ID')
    }

    travel.clearPendingPlan()
    router.replace(`/trip/${tripId.value}`)
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') return

    errorMessage.value = getErrorMessage(error)
    toast.error(errorMessage.value)
  } finally {
    isPlanning.value = false
    abortController = null
  }
}

onMounted(() => {
  void startPlanning()
})

onBeforeUnmount(() => {
  abortController?.abort()
})
</script>

<template>
  <motion.main
    class="mx-auto flex min-h-screen w-full max-w-[430px] flex-col overflow-x-hidden bg-white px-5 pb-8 pt-[calc(env(safe-area-inset-top)+56px)] text-[#222222]"
    :initial="{ opacity: 0, x: 96 }"
    :animate="{ opacity: 1, x: 0 }"
    :transition="{ duration: 0.28, ease: 'easeOut' }"
  >
    <header class="fixed left-1/2 top-0 z-40 flex h-[calc(env(safe-area-inset-top)+56px)] w-full max-w-[430px] -translate-x-1/2 items-end justify-center bg-white/95 px-5 pb-3 backdrop-blur">
      <p class="pb-2 text-sm font-semibold">规划行程</p>
    </header>

    <section class="flex flex-1 flex-col items-center justify-center text-center">
      <div class="size-14 rounded-full border-4 border-[#f2f2f2] border-t-[#ff385c] motion-safe:animate-spin"></div>
      <h1 class="mt-7 text-[28px] font-bold leading-tight">正在规划中</h1>
      <p class="mt-3 min-h-5 max-w-[280px] text-sm leading-5 text-[#6a6a6a]">
        {{ errorMessage || statusText }}
      </p>
      <p v-if="tripId" class="mt-3 max-w-[280px] truncate text-xs font-medium text-[#929292]">
        {{ tripId }}
      </p>

      <button
        v-if="errorMessage"
        class="mt-8 flex h-12 w-full max-w-[240px] items-center justify-center rounded-2xl bg-[#ff385c] text-sm font-semibold text-white"
        type="button"
        @click="startPlanning"
      >
        重新生成
      </button>
    </section>
  </motion.main>
</template>
