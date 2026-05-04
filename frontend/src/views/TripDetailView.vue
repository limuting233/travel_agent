<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, Clock3, MapPin, Navigation, RefreshCw, Route } from 'lucide-vue-next'
import { motion } from 'motion-v'
import { toast } from 'vue-sonner'
import { getTripDetail, type TripDetail, type TripScheduleItem } from '@/api/trips'
import { goBack } from '@/utils/navigation'

const route = useRoute()
const router = useRouter()
const trip = ref<TripDetail | null>(null)
const isLoading = ref(false)
const errorMessage = ref('')
const activeDay = ref<number | null>(null)

const tripId = computed(() => String(route.params.tripId || ''))
const content = computed(() => trip.value?.latest_version?.content ?? null)
const overview = computed(() => content.value?.trip_overview ?? null)
const dailyItinerary = computed(() => content.value?.daily_itinerary ?? [])
const tags = computed(() => overview.value?.tags?.length ? overview.value.tags : trip.value?.preferences ?? [])
const selectedDay = computed(() => activeDay.value ?? dailyItinerary.value[0]?.day ?? 0)

let scrollFrame = 0

function getErrorMessage(error: unknown) {
  if (error instanceof Error) return error.message
  return '行程详情加载失败'
}

async function fetchTripDetail() {
  if (!tripId.value) {
    router.replace('/')
    return
  }

  isLoading.value = true
  errorMessage.value = ''

  try {
    trip.value = await getTripDetail(tripId.value)
    activeDay.value = trip.value.latest_version?.content.daily_itinerary[0]?.day ?? null
    await nextTick()
    syncActiveDayOnScroll()
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
    toast.error(errorMessage.value)
  } finally {
    isLoading.value = false
  }
}

function leavePage() {
  goBack(router, '/trips', {
    blockedBackPaths: ['/trip/create', '/trip/planning'],
  })
}

function scrollToDay(day: number) {
  activeDay.value = day
  document.getElementById(`trip-day-${day}`)?.scrollIntoView({
    behavior: 'smooth',
    block: 'start',
  })
}

function getPinnedHeaderHeight() {
  const headerHeight = document.querySelector('[data-trip-header]')?.getBoundingClientRect().height ?? 56
  const dayNavHeight = document.querySelector('[data-trip-day-nav]')?.getBoundingClientRect().height ?? 52

  return headerHeight + dayNavHeight
}

function syncActiveDayOnScroll() {
  if (scrollFrame) return

  scrollFrame = window.requestAnimationFrame(() => {
    scrollFrame = 0

    const firstDay = dailyItinerary.value[0]?.day
    if (!firstDay) return

    const offset = getPinnedHeaderHeight() + 8
    let currentDay = firstDay

    for (const day of dailyItinerary.value) {
      const element = document.getElementById(`trip-day-${day.day}`)
      if (!element) continue

      if (element.getBoundingClientRect().top <= offset) {
        currentDay = day.day
      }
    }

    activeDay.value = currentDay
  })
}

function isCommuteItem(item: TripScheduleItem) {
  return item.action === '通勤' || Boolean(item.transport_mode || item.from_poi || item.to_poi)
}

function parseLocation(location?: string) {
  if (!location) return null

  const [longitude, latitude] = location.split(',').map((value) => Number(value.trim()))
  if (!Number.isFinite(longitude) || !Number.isFinite(latitude)) return null

  return { longitude, latitude }
}

function findPreviousPoi(schedule: TripScheduleItem[], itemIndex: number) {
  for (let index = itemIndex - 1; index >= 0; index -= 1) {
    const item = schedule[index]
    if (!item) continue

    if (!isCommuteItem(item) && parseLocation(item.location)) {
      return item
    }
  }

  return null
}

function findNextPoi(schedule: TripScheduleItem[], itemIndex: number) {
  for (let index = itemIndex + 1; index < schedule.length; index += 1) {
    const item = schedule[index]
    if (!item) continue

    if (!isCommuteItem(item) && parseLocation(item.location)) {
      return item
    }
  }

  return null
}

function getAmapNavigationMode(mode?: string) {
  const modeMap: Record<string, string> = {
    walking: 'walk',
    driving: 'car',
    transit: 'bus',
    transit_integrated: 'bus',
    bicycling: 'ride',
  }

  return mode ? modeMap[mode] || 'car' : 'car'
}

function buildNavigationUrl(schedule: TripScheduleItem[], itemIndex: number) {
  const item = schedule[itemIndex]
  if (!item) return ''

  const fromPoi = findPreviousPoi(schedule, itemIndex)
  const toPoi = findNextPoi(schedule, itemIndex)
  const fromLocation = parseLocation(fromPoi?.location)
  const toLocation = parseLocation(toPoi?.location)

  if (!fromPoi || !toPoi || !fromLocation || !toLocation) {
    const keyword = encodeURIComponent(item.to_poi || toPoi?.poi_name || '')
    return keyword ? `https://uri.amap.com/search?keyword=${keyword}&src=travel-agent&callnative=1` : ''
  }

  const fromName = encodeURIComponent(fromPoi.poi_name || item.from_poi || '起点')
  const toName = encodeURIComponent(toPoi.poi_name || item.to_poi || '终点')
  const from = `${fromLocation.longitude},${fromLocation.latitude},${fromName}`
  const to = `${toLocation.longitude},${toLocation.latitude},${toName}`
  const mode = getAmapNavigationMode(item.transport_mode)

  return `https://uri.amap.com/navigation?from=${from}&to=${to}&mode=${mode}&src=travel-agent&coordinate=gaode&callnative=1`
}

function openNavigation(schedule: TripScheduleItem[], itemIndex: number) {
  const url = buildNavigationUrl(schedule, itemIndex)
  if (!url) {
    toast.error('暂无可用导航信息')
    return
  }

  window.open(url, '_blank')
}

function formatTransportMode(mode?: string) {
  const modeMap: Record<string, string> = {
    walking: '步行',
    driving: '打车/驾车',
    transit: '公共交通',
    transit_integrated: '公共交通',
    bicycling: '骑行',
  }

  return mode ? modeMap[mode] || mode : ''
}

function formatCategory(category?: string) {
  const categoryMap: Record<string, string> = {
    CORE_SIGHTSEEING: '核心景点',
    LOCAL_GASTRONOMY: '本地美食',
    CITY_LEISURE: '城市休闲',
    ACCOMMODATION: '住宿',
  }

  return category ? categoryMap[category] || category : ''
}

function formatDistance(distance?: number) {
  if (!distance) return ''
  if (distance >= 1000) return `${(distance / 1000).toFixed(1)} km`
  return `${distance} m`
}

function formatDuration(duration?: number) {
  if (!duration) return ''
  return Number.isInteger(duration) ? `${duration} 小时` : `${duration.toFixed(1)} 小时`
}

function formatCost(cost?: number) {
  if (cost === undefined || cost === null) return ''
  return cost > 0 ? `约 ¥${cost}` : '免费'
}

function formatKilometers(distance?: number) {
  if (distance === undefined || distance === null) return ''
  return distance.toFixed(2)
}

function formatDateLabel(dateValue: string) {
  const [year, month, day] = dateValue.split('-').map((value) => Number(value))

  if (!year || !month || !day) return dateValue

  return `${month}月${day}日`
}

function formatDateRange(startDate: string | null, endDate: string | null) {
  if (!startDate && !endDate) return '未定'
  if (startDate && !endDate) return `${formatDateLabel(startDate)}起`
  if (!startDate && endDate) return `至${formatDateLabel(endDate)}`

  const start = startDate || ''
  const end = endDate || ''

  return `${formatDateLabel(start)} - ${formatDateLabel(end)}`
}

onMounted(() => {
  void fetchTripDetail()
  window.addEventListener('scroll', syncActiveDayOnScroll, { passive: true })
})

onBeforeUnmount(() => {
  window.removeEventListener('scroll', syncActiveDayOnScroll)

  if (scrollFrame) {
    window.cancelAnimationFrame(scrollFrame)
  }
})
</script>

<template>
  <motion.main
    class="mx-auto min-h-screen w-full max-w-[430px] overflow-x-hidden bg-white px-5 pb-10 text-[#222222]"
    :class="dailyItinerary.length ? 'pt-[calc(env(safe-area-inset-top)+108px)]' : 'pt-[calc(env(safe-area-inset-top)+56px)]'"
    :initial="{ opacity: 0, x: 96 }"
    :animate="{ opacity: 1, x: 0 }"
    :transition="{ duration: 0.28, ease: 'easeOut' }"
  >
    <header
      class="fixed left-1/2 top-0 z-40 flex h-[calc(env(safe-area-inset-top)+56px)] w-full max-w-[430px] -translate-x-1/2 items-end justify-between bg-white/95 px-5 pb-3 backdrop-blur"
      data-trip-header
    >
      <button
        class="flex size-9 items-center justify-center rounded-full bg-[#f2f2f2]"
        type="button"
        aria-label="返回上一页"
        @click="leavePage"
      >
        <ArrowLeft class="size-4" />
      </button>
      <p class="pb-2 text-sm font-semibold">行程详情</p>
      <button
        class="flex size-9 items-center justify-center rounded-full bg-[#f2f2f2]"
        type="button"
        aria-label="刷新行程"
        @click="fetchTripDetail"
      >
        <RefreshCw class="size-4" />
      </button>
    </header>

    <nav
      v-if="dailyItinerary.length"
      class="fixed left-1/2 top-[calc(env(safe-area-inset-top)+56px)] z-40 w-full max-w-[430px] -translate-x-1/2 border-b border-[#ebebeb] bg-white/95 px-5 py-2 backdrop-blur"
      aria-label="选择行程天数"
      data-trip-day-nav
    >
      <div class="flex gap-2 overflow-x-auto [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
        <button
          v-for="day in dailyItinerary"
          :key="`tab-${day.day}`"
          class="flex h-9 shrink-0 items-center justify-center rounded-full border px-4 text-sm font-semibold transition"
          :class="selectedDay === day.day
            ? 'border-[#222222] bg-[#222222] text-white'
            : 'border-[#dddddd] bg-white text-[#222222]'"
          type="button"
          @click="scrollToDay(day.day)"
        >
          第 {{ day.day }} 天
        </button>
      </div>
    </nav>

    <section v-if="isLoading" class="flex min-h-[60vh] flex-col items-center justify-center text-center">
      <div class="size-12 rounded-full border-4 border-[#f2f2f2] border-t-[#ff385c] motion-safe:animate-spin"></div>
      <p class="mt-4 text-sm font-medium text-[#6a6a6a]">正在加载行程</p>
    </section>

    <section v-else-if="errorMessage" class="flex min-h-[60vh] flex-col items-center justify-center text-center">
      <h1 class="text-[24px] font-bold leading-tight">加载失败</h1>
      <p class="mt-3 text-sm leading-5 text-[#6a6a6a]">{{ errorMessage }}</p>
      <button
        class="mt-7 flex h-12 w-full max-w-[240px] items-center justify-center rounded-2xl bg-[#ff385c] text-sm font-semibold text-white"
        type="button"
        @click="fetchTripDetail"
      >
        重新加载
      </button>
    </section>

    <template v-else-if="trip">
      <section class="pt-5">
        <p class="flex items-center gap-1 text-sm font-medium text-[#6a6a6a]">
          <MapPin class="size-4 text-[#ff385c]" />
          {{ trip.location }}
        </p>
        <h1 class="mt-3 text-[30px] font-bold leading-tight">{{ overview?.title || trip.title }}</h1>
        <div class="mt-4 flex flex-wrap gap-2">
          <span
            v-for="tag in tags"
            :key="tag"
            class="rounded-full bg-[#f7f7f7] px-3 py-1.5 text-xs font-medium text-[#222222]"
          >
            {{ tag }}
          </span>
        </div>
      </section>

      <section class="mt-7 grid grid-cols-2 border-y border-[#ebebeb] py-4">
        <div>
          <p class="text-xs font-medium text-[#6a6a6a]">天数</p>
          <p class="mt-1 text-base font-semibold">{{ trip.days }} 天</p>
        </div>
        <div>
          <p class="text-xs font-medium text-[#6a6a6a]">日期</p>
          <p class="mt-1 truncate text-base font-semibold">{{ formatDateRange(trip.start_date, trip.end_date) }}</p>
        </div>
      </section>

      <section v-if="overview?.total_distance_km" class="mt-5 flex items-center gap-2 text-sm text-[#6a6a6a]">
        <Route class="size-4 text-[#ff385c]" />
        全程约 {{ formatKilometers(overview.total_distance_km) }} km
      </section>

      <section class="mt-8">
        <h2 class="text-[22px] font-bold leading-tight">每日安排</h2>

        <div v-if="dailyItinerary.length" class="mt-3">
          <section
            v-for="day in dailyItinerary"
            :key="`${day.day}-${day.date || ''}`"
            :id="`trip-day-${day.day}`"
            class="scroll-mt-[calc(env(safe-area-inset-top)+116px)] border-t border-[#ebebeb] py-6 first:border-t-0"
          >
            <div class="flex items-baseline justify-between gap-3">
              <h3 class="text-lg font-bold">第 {{ day.day }} 天</h3>
              <p v-if="day.date" class="shrink-0 text-sm font-medium text-[#6a6a6a]">{{ day.date }}</p>
            </div>

            <div class="mt-5 space-y-5">
              <div
                v-for="(item, itemIndex) in day.schedule"
                :key="`${day.day}-${item.seq}`"
                class="flex gap-3"
              >
                <div class="flex w-14 shrink-0 flex-col items-center">
                  <span class="flex size-8 items-center justify-center rounded-full bg-[#f2f2f2] text-xs font-semibold">
                    {{ item.seq }}
                  </span>
                  <span class="mt-2 h-full w-px flex-1 bg-[#ebebeb]"></span>
                </div>
                <div class="min-w-0 flex-1 pb-1">
                  <p v-if="item.time_window" class="flex items-center gap-1 text-xs font-medium text-[#6a6a6a]">
                    <Clock3 class="size-3.5" />
                    {{ item.time_window }}
                  </p>
                  <template v-if="isCommuteItem(item)">
                    <h4 class="mt-1 text-base font-semibold">
                      {{ item.from_poi || '上一站' }} → {{ item.to_poi || '下一站' }}
                    </h4>
                    <p class="mt-2 flex flex-wrap items-center gap-2 text-xs font-medium text-[#6a6a6a]">
                      <span class="inline-flex items-center gap-1">
                        <Navigation class="size-3.5" />
                        {{ formatTransportMode(item.transport_mode) || '通勤' }}
                      </span>
                      <span v-if="formatDistance(item.distance_meter)">{{ formatDistance(item.distance_meter) }}</span>
                      <span v-if="item.commute_time_min">{{ item.commute_time_min }} 分钟</span>
                    </p>
                    <button
                      class="mt-3 inline-flex h-9 items-center gap-1 rounded-full border border-[#dddddd] px-3 text-xs font-semibold text-[#222222]"
                      type="button"
                      @click="openNavigation(day.schedule, itemIndex)"
                    >
                      <Navigation class="size-3.5" />
                      打开导航
                    </button>
                  </template>

                  <template v-else>
                    <h4 class="mt-1 text-base font-semibold">
                      {{ item.poi_name || item.action }}
                    </h4>
                    <img
                      v-if="item.photo"
                      :src="item.photo"
                      :alt="item.poi_name || item.action"
                      class="mt-3 aspect-[16/10] w-full rounded-2xl object-cover"
                    >
                    <div class="mt-2 flex flex-wrap gap-2 text-xs font-medium text-[#6a6a6a]">
                      <span v-if="formatCategory(item.category)" class="rounded-full bg-[#f7f7f7] px-2 py-1">{{ formatCategory(item.category) }}</span>
                      <span v-if="item.action" class="rounded-full bg-[#f7f7f7] px-2 py-1">{{ item.action }}</span>
                      <span v-if="formatDuration(item.duration_hour)" class="rounded-full bg-[#f7f7f7] px-2 py-1">
                        {{ formatDuration(item.duration_hour) }}
                      </span>
                      <span v-if="formatCost(item.cost)" class="rounded-full bg-[#f7f7f7] px-2 py-1">
                        {{ formatCost(item.cost) }}
                      </span>
                    </div>
                    <p v-if="item.reason" class="mt-2 text-sm leading-5 text-[#6a6a6a]">{{ item.reason }}</p>
                  </template>
                </div>
              </div>
            </div>
          </section>
        </div>

        <p v-else class="mt-4 text-sm leading-5 text-[#6a6a6a]">
          暂时没有可展示的每日安排。
        </p>
      </section>
    </template>
  </motion.main>
</template>
