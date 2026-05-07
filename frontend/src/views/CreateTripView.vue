<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowLeft, CalendarDays, MapPin, Minus, Plus } from 'lucide-vue-next'
import { motion } from 'motion-v'
import { useTravelStore } from '@/stores/travel'
import { goBack } from '@/utils/navigation'

const router = useRouter()
const travel = useTravelStore()
const isLeaving = ref(false)

const preferences = ['经典必玩', '吃吃喝喝', 'Citywalk', '亲子友好', '小众探索', '自然风景', '轻奢度假', '拍照出片', '博物馆', '夜生活', '慢节奏', '购物逛街']

const form = reactive({
    destination: '',
    days: 3,
    startDate: '',
    endDate: '',
    preferences: ['经典必玩', '吃吃喝喝'],
})

const fieldErrors = reactive({
    destination: '',
    days: '',
    dates: '',
})

const canSubmit = computed(() => {
    return Boolean(form.destination.trim() && form.days > 0)
})

function togglePreference(item: string) {
    const index = form.preferences.indexOf(item)

    if (index >= 0) {
        form.preferences.splice(index, 1)
        return
    }

    form.preferences.push(item)
}

function changeDays(step: number) {
    form.days = Math.max(1, form.days + step)

    if (fieldErrors.days) {
        fieldErrors.days = ''
    }
}

function leaveToHome() {
    if (isLeaving.value) return

    isLeaving.value = true
    window.setTimeout(() => {
        goBack(router)
    }, 260)
}

function getTodayValue() {
    const now = new Date()
    const year = now.getFullYear()
    const month = String(now.getMonth() + 1).padStart(2, '0')
    const day = String(now.getDate()).padStart(2, '0')
    return `${year}-${month}-${day}`
}

function getDateRangeDays(startDate: string, endDate: string) {
    const start = new Date(`${startDate}T00:00:00`)
    const end = new Date(`${endDate}T00:00:00`)
    const dayMs = 24 * 60 * 60 * 1000
    return Math.floor((end.getTime() - start.getTime()) / dayMs) + 1
}

function clearDestinationError() {
    if (fieldErrors.destination && form.destination.trim()) {
        fieldErrors.destination = ''
    }
}

function clearDateError() {
    if (fieldErrors.dates) {
        fieldErrors.dates = ''
    }
}

function validateForm() {
    const destination = form.destination.trim()
    const days = Number(form.days)
    const hasStartDate = Boolean(form.startDate)
    const hasEndDate = Boolean(form.endDate)

    fieldErrors.destination = ''
    fieldErrors.days = ''
    fieldErrors.dates = ''

    if (!destination) {
        fieldErrors.destination = '请输入目的地'
    }

    if (!Number.isInteger(days) || days < 1) {
        fieldErrors.days = '天数必须大于等于 1'
    }

    if (hasStartDate !== hasEndDate) {
        fieldErrors.dates = '开始日期和结束日期需要同时填写'
    } else if (hasStartDate && hasEndDate) {
        const rangeDays = getDateRangeDays(form.startDate, form.endDate)

        if (form.startDate < getTodayValue()) {
            fieldErrors.dates = '开始日期不能早于今天'
        } else if (rangeDays < 1) {
            fieldErrors.dates = '结束日期不能早于开始日期'
        } else if (rangeDays !== days) {
            fieldErrors.dates = `日期区间是 ${rangeDays} 天，请和天数保持一致`
        }
    }

    return !fieldErrors.destination && !fieldErrors.days && !fieldErrors.dates
}

function submit() {
    if (!validateForm()) return

    travel.setPendingPlan({
        location: form.destination.trim(),
        days: Number(form.days),
        start_date: form.startDate || null,
        end_date: form.endDate || null,
        preferences: form.preferences.length ? form.preferences.join(',') : null,
    })

    router.replace('/trip/planning')
}
</script>

<template>
    <motion.main
        class="mx-auto min-h-screen w-full max-w-[430px] overflow-x-hidden bg-white px-5 pb-8 pt-[calc(env(safe-area-inset-top)+56px)] text-[#222222]"
        :initial="{ opacity: 0, x: 96 }"
        :animate="isLeaving ? { opacity: 0, x: 96 } : { opacity: 1, x: 0 }"
        :transition="{ duration: isLeaving ? 0.26 : 0.32, ease: 'easeOut' }">
        <header
            class="fixed left-1/2 top-0 z-40 flex h-[calc(env(safe-area-inset-top)+56px)] w-full max-w-[430px] -translate-x-1/2 items-end justify-between bg-white/95 px-5 pb-3 backdrop-blur">
            <button class="flex size-9 items-center justify-center rounded-full bg-[#f2f2f2]" type="button" aria-label="返回上一页" @click="leaveToHome">
                <ArrowLeft class="size-4" />
            </button>
            <p class="pb-2 text-sm font-semibold">创建行程</p>
            <span class="size-9"></span>
        </header>

        <form class="mt-1" @submit.prevent="submit">
            <section class="border-b border-[#dddddd]">
                <div class="py-5">
                    <label for="destination" class="flex items-center gap-2 text-sm font-semibold">
                        <MapPin class="size-4 text-[#ff385c]" />
                        目的地
                    </label>
                    <input
                        id="destination"
                        v-model="form.destination"
                        class="mt-3 h-14 w-full rounded-lg border border-[#dddddd] bg-white px-3 text-base outline-none transition focus:border-[#222222]"
                        placeholder="例如：上海、北京、云南"
                        type="text"
                        @input="clearDestinationError" />
                    <p v-if="fieldErrors.destination" class="mt-2 text-xs font-medium text-[#c13515]">
                        {{ fieldErrors.destination }}
                    </p>
                </div>

                <div class="border-t border-[#ebebeb] py-5">
                    <div class="flex items-center justify-between gap-5">
                        <div>
                            <label for="days" class="text-sm font-semibold">天数</label>
                            <p class="mt-1 text-sm text-[#6a6a6a]">计划玩几天</p>
                        </div>
                        <div class="flex items-center gap-3">
                            <button
                                class="flex size-10 items-center justify-center rounded-full border border-[#dddddd] disabled:text-[#c1c1c1]"
                                :disabled="form.days <= 1"
                                type="button"
                                aria-label="减少天数"
                                @click="changeDays(-1)">
                                <Minus class="size-4" />
                            </button>
                            <input
                                id="days"
                                v-model.number="form.days"
                                class="w-10 bg-transparent text-center text-xl font-semibold outline-none"
                                min="1"
                                type="number"
                                @input="fieldErrors.days = ''" />
                            <button
                                class="flex size-10 items-center justify-center rounded-full border border-[#dddddd]"
                                type="button"
                                aria-label="增加天数"
                                @click="changeDays(1)">
                                <Plus class="size-4" />
                            </button>
                        </div>
                    </div>
                    <p v-if="fieldErrors.days" class="mt-2 text-xs font-medium text-[#c13515]">
                        {{ fieldErrors.days }}
                    </p>
                </div>

                <div class="border-t border-[#ebebeb] py-5">
                    <div class="flex items-center justify-between gap-3">
                        <div class="flex items-center gap-2 text-sm font-semibold">
                            <CalendarDays class="size-4 text-[#ff385c]" />
                            旅游时间
                        </div>
                        <span class="rounded-full bg-[#f7f7f7] px-2 py-1 text-xs font-medium text-[#6a6a6a]">可选</span>
                    </div>
                    <div class="mt-3 grid grid-cols-2 gap-3">
                        <label class="block min-w-0">
                            <span class="text-xs font-medium text-[#6a6a6a]">开始日期</span>
                            <input
                                v-model="form.startDate"
                                class="mt-2 h-14 w-full min-w-0 appearance-none rounded-lg border border-[#dddddd] bg-white px-3 text-sm outline-none transition focus:border-[#222222]"
                                :min="getTodayValue()"
                                type="date"
                                @input="clearDateError" />
                        </label>
                        <label class="block min-w-0">
                            <span class="text-xs font-medium text-[#6a6a6a]">结束日期</span>
                            <input
                                v-model="form.endDate"
                                class="mt-2 h-14 w-full min-w-0 appearance-none rounded-lg border border-[#dddddd] bg-white px-3 text-sm outline-none transition focus:border-[#222222]"
                                :min="form.startDate || undefined"
                                type="date"
                                @input="clearDateError" />
                        </label>
                    </div>
                    <p v-if="fieldErrors.dates" class="mt-2 text-xs font-medium text-[#c13515]">
                        {{ fieldErrors.dates }}
                    </p>
                </div>
            </section>

            <section class="pt-7">
                <div class="flex items-end justify-between gap-4">
                    <div>
                        <h2 class="text-[21px] font-bold leading-tight">旅游偏好</h2>
                    </div>
                    <span class="shrink-0 text-sm font-medium text-[#6a6a6a]">{{ form.preferences.length }} 项</span>
                </div>

                <div class="mt-4 grid grid-cols-4 gap-2">
                    <button
                        v-for="item in preferences"
                        :key="item"
                        class="flex h-11 min-w-0 items-center justify-center rounded-full border px-1 text-[13px] font-medium transition"
                        :class="form.preferences.includes(item) ? 'border-[#ff385c] bg-[#ff385c] text-white' : 'border-[#dddddd] bg-white text-[#222222]'"
                        type="button"
                        @click="togglePreference(item)">
                        {{ item }}
                    </button>
                </div>
            </section>

            <section class="sticky bottom-0 -mx-5 bg-white/95 px-5 pb-[calc(env(safe-area-inset-bottom)+12px)] pt-3 backdrop-blur">
                <button
                    class="flex h-14 w-full items-center justify-center rounded-2xl text-base font-semibold text-white transition"
                    :class="canSubmit ? 'bg-[#ff385c]' : 'bg-[#ffd1da]'"
                    :disabled="!canSubmit"
                    type="submit">
                    生成我的行程
                </button>
            </section>
        </form>
    </motion.main>
</template>
