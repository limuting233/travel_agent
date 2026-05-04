<script setup lang="ts">
import { ArrowRight, CalendarDays, Sparkles, Star } from 'lucide-vue-next'

const inspirations = [
  {
    city: '京都',
    note: '樱花老街 · 寺院巡游',
    tags: ['经典必玩', 'Citywalk'],
    days: '推荐 3 天',
    image: 'https://images.unsplash.com/photo-1493976040374-85c8e12f0c0e?auto=format&fit=crop&w=640&q=80',
  },
  {
    city: '大理',
    note: '洱海松弛感 · 自然风景',
    tags: ['自然风景', '慢节奏'],
    days: '推荐 4 天',
    image: 'https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?auto=format&fit=crop&w=640&q=80',
  },
  {
    city: '新加坡',
    note: '城市探索 · 亲子友好',
    tags: ['亲子友好', '吃吃喝喝'],
    days: '推荐 3-4 天',
    image: 'https://images.unsplash.com/photo-1525625293386-3f8f99389edd?auto=format&fit=crop&w=640&q=80',
  },
]

const quickNeeds = ['周末短途', '亲子旅行', '蜜月海岛', '小众城市']
</script>

<template>
  <main
    class="mx-auto min-h-screen max-w-[430px] bg-white px-5 pb-10 pt-[calc(env(safe-area-inset-top)+62px)] text-[#222222]"
  >
    <header class="fixed left-1/2 top-0 z-40 flex h-[calc(env(safe-area-inset-top)+56px)] w-full max-w-[430px] -translate-x-1/2 items-end justify-between bg-white/95 px-5 pb-3 backdrop-blur">
      <div>
        <h1 class="pb-1 text-[24px] font-bold leading-tight tracking-normal">想去哪玩？</h1>
      </div>
      <RouterLink
        to="/profile"
        class="flex size-8 items-center justify-center rounded-full bg-[#ff385c] text-xs font-bold text-white shadow-[0_3px_10px_rgba(255,56,92,0.24)]"
        aria-label="进入我的页面"
      >
        旅
      </RouterLink>
    </header>

    <section class="mt-6 overflow-hidden rounded-[28px] bg-[#f7f7f7]">
      <div class="relative h-56">
        <img
          class="h-full w-full object-cover"
          src="https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&w=900&q=85"
          alt="海边旅行目的地"
        >
        <div class="absolute inset-0 bg-gradient-to-t from-black/55 via-black/10 to-transparent"></div>
        <div class="absolute bottom-0 left-0 right-0 p-5 text-white">
          <div class="mb-3 inline-flex items-center gap-1 rounded-full bg-white/90 px-3 py-1 text-xs font-semibold text-[#222222]">
            <Sparkles class="size-3.5 text-[#ff385c]" />
            AI 旅游规划
          </div>
          <h2 class="text-[24px] font-semibold leading-tight">创建你的旅行方案</h2>
          <p class="mt-2 text-sm leading-5 text-white/90">选好目的地和偏好，生成路线。</p>
        </div>
      </div>
    </section>

    <section class="mt-5 rounded-full border border-[#dddddd] bg-white p-2 shadow-[0_2px_12px_rgba(0,0,0,0.08)]">
      <RouterLink to="/trip/create" class="flex h-14 w-full items-center justify-between rounded-full pl-5 pr-2 text-left">
        <span>
          <span class="block text-sm font-semibold">你想怎么旅行？</span>
          <span class="block text-xs text-[#6a6a6a]">例如：想去上海，玩 4 天，打卡网红美食</span>
        </span>
        <span class="flex size-11 shrink-0 items-center justify-center rounded-full bg-[#ff385c] text-white">
          <ArrowRight class="size-5" />
        </span>
      </RouterLink>
    </section>

    <section class="mt-6">
      <div class="flex gap-2 overflow-x-auto pb-1 [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
        <button
          v-for="item in quickNeeds"
          :key="item"
          class="h-10 shrink-0 rounded-full border border-[#dddddd] px-4 text-sm font-medium text-[#222222]"
        >
          {{ item }}
        </button>
      </div>
    </section>

    <section class="mt-8">
      <div class="mb-4 flex items-end justify-between">
        <div>
          <h2 class="text-[21px] font-bold leading-tight">灵感目的地</h2>
        </div>
        <button class="text-sm font-medium text-[#222222]">全部</button>
      </div>

      <div class="space-y-4">
        <article
          v-for="item in inspirations"
          :key="item.city"
          class="flex gap-3"
        >
          <img class="size-24 rounded-[14px] object-cover" :src="item.image" :alt="item.city">
          <div class="flex min-w-0 flex-1 flex-col justify-center border-b border-[#ebebeb] pb-4">
            <div class="flex items-center justify-between gap-3">
              <h3 class="truncate text-base font-semibold">{{ item.city }}</h3>
              <span class="inline-flex items-center gap-1 text-sm font-medium">
                <Star class="size-3.5 fill-[#222222]" />
                4.9
              </span>
            </div>
            <p class="mt-1 text-sm text-[#6a6a6a]">{{ item.note }}</p>
            <div class="mt-3 flex items-center gap-3 text-xs text-[#6a6a6a]">
              <span class="inline-flex items-center gap-1">
                <Sparkles class="size-3.5" />
                {{ item.tags.join(' / ') }}
              </span>
              <span class="inline-flex items-center gap-1">
                <CalendarDays class="size-3.5" />
                {{ item.days }}
              </span>
            </div>
          </div>
        </article>
      </div>
    </section>
  </main>
</template>
