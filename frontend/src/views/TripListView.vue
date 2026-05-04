<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { ArrowLeft, CalendarDays, ChevronRight, MapPin, Plus, RefreshCw } from 'lucide-vue-next'
import { motion } from 'motion-v'
import { toast } from 'vue-sonner'
import { getTripList, type TripListItem, type TripStatus } from '@/api/trips'
import { goBack as navigateBack } from '@/utils/navigation'

const router = useRouter()
const isLoading = ref(false)
const trips = ref<TripListItem[]>([])

function getErrorMessage(error: unknown) {
  if (error instanceof Error) return error.message
  return '行程列表加载失败'
}

function formatDateLabel(dateValue: string) {
  const [year, month, day] = dateValue.split('-').map((value) => Number(value))

  if (!year || !month || !day) return dateValue

  return `${year}年${month}月${day}日`
}

function formatDateRange(startDate: string | null, endDate: string | null) {
  if (!startDate && !endDate) return '时间未定'
  if (startDate && !endDate) return `${formatDateLabel(startDate)}起`
  if (!startDate && endDate) return `至${formatDateLabel(endDate)}`

  return `${formatDateLabel(startDate || '')} - ${formatDateLabel(endDate || '')}`
}

function formatStatus(status: TripStatus) {
  const statusMap: Record<TripStatus, string> = {
    planning: '规划中',
    completed: '已完成',
    failed: '失败',
  }

  return statusMap[status]
}

function getStatusClass(status: TripStatus) {
  if (status === 'completed') return 'bg-[#eef8ee] text-[#008a05]'
  if (status === 'planning') return 'bg-[#fff4e6] text-[#a15c00]'
  return 'bg-[#fff0f0] text-[#c13515]'
}

async function fetchTrips() {
  isLoading.value = true

  try {
    const result = await getTripList({
      page: 1,
      page_size: 20,
    })

    trips.value = result.items
  } catch (error) {
    toast.error(getErrorMessage(error))
  } finally {
    isLoading.value = false
  }
}

function leavePage() {
  navigateBack(router, '/profile', {
    blockedBackPaths: ['/trip/create', '/trip/planning'],
  })
}

onMounted(() => {
  void fetchTrips()
})
</script>

<template>
  <motion.main
    class="mx-auto min-h-screen w-full max-w-[430px] overflow-x-hidden bg-white px-5 pb-10 pt-[calc(env(safe-area-inset-top)+72px)] text-[#222222]"
    :initial="{ opacity: 0, x: 96 }"
    :animate="{ opacity: 1, x: 0 }"
    :transition="{ duration: 0.28, ease: 'easeOut' }"
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
      <p class="pb-2 text-sm font-semibold">我的行程</p>
      <RouterLink
        to="/trip/create"
        class="flex size-9 items-center justify-center rounded-full bg-[#ff385c] text-white"
        aria-label="创建行程"
      >
        <Plus class="size-4" />
      </RouterLink>
    </header>

    <section v-if="isLoading" class="flex min-h-[55vh] flex-col items-center justify-center text-center">
      <div class="size-12 rounded-full border-4 border-[#f2f2f2] border-t-[#ff385c] motion-safe:animate-spin"></div>
      <p class="mt-4 text-sm font-medium text-[#6a6a6a]">正在加载行程</p>
    </section>

    <section v-else-if="!trips.length" class="flex min-h-[55vh] flex-col items-center justify-center text-center">
      <h1 class="text-[24px] font-bold leading-tight">还没有行程</h1>
      <RouterLink
        to="/trip/create"
        class="mt-7 flex h-12 w-full max-w-[240px] items-center justify-center rounded-2xl bg-[#ff385c] text-sm font-semibold text-white"
      >
        创建行程
      </RouterLink>
    </section>

    <section v-else>
      <div class="flex items-center justify-between">
        <h1 class="text-[28px] font-bold leading-tight">我的行程</h1>
        <button
          class="flex size-9 items-center justify-center rounded-full bg-[#f2f2f2]"
          type="button"
          aria-label="刷新行程列表"
          @click="fetchTrips"
        >
          <RefreshCw class="size-4" />
        </button>
      </div>

      <div class="mt-5 divide-y divide-[#ebebeb] border-y border-[#ebebeb]">
        <RouterLink
          v-for="trip in trips"
          :key="trip.id"
          :to="`/trip/${trip.id}`"
          class="flex gap-3 py-5"
        >
          <span class="mt-1 flex size-10 shrink-0 items-center justify-center rounded-full bg-[#f2f2f2]">
            <MapPin class="size-5 text-[#ff385c]" />
          </span>
          <span class="min-w-0 flex-1">
            <span class="flex items-start justify-between gap-3">
              <span class="min-w-0">
                <span class="block truncate text-lg font-semibold">{{ trip.title }}</span>
                <span class="mt-1 block text-sm text-[#6a6a6a]">{{ trip.location }} · {{ trip.days }} 天</span>
              </span>
              <span class="shrink-0 rounded-full px-2 py-1 text-xs font-semibold" :class="getStatusClass(trip.status)">
                {{ formatStatus(trip.status) }}
              </span>
            </span>
            <span class="mt-3 flex items-center gap-1 text-sm text-[#6a6a6a]">
              <CalendarDays class="size-4" />
              {{ formatDateRange(trip.start_date, trip.end_date) }}
            </span>
          </span>
          <ChevronRight class="mt-3 size-5 shrink-0 text-[#929292]" />
        </RouterLink>
      </div>
    </section>
  </motion.main>
</template>
