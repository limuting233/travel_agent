import { defineStore } from 'pinia'
import type { CreateTravelPlanParams } from '@/api/travel'

const PENDING_PLAN_KEY = 'travel_agent_pending_plan'

function readPendingPlan() {
  if (typeof window === 'undefined') return null

  const rawValue = window.sessionStorage.getItem(PENDING_PLAN_KEY)
  if (!rawValue) return null

  try {
    return JSON.parse(rawValue) as CreateTravelPlanParams
  } catch {
    window.sessionStorage.removeItem(PENDING_PLAN_KEY)
    return null
  }
}

export const useTravelStore = defineStore('travel', {
  state: () => ({
    pendingPlan: readPendingPlan() as CreateTravelPlanParams | null,
  }),
  actions: {
    setPendingPlan(plan: CreateTravelPlanParams) {
      this.pendingPlan = plan

      if (typeof window !== 'undefined') {
        window.sessionStorage.setItem(PENDING_PLAN_KEY, JSON.stringify(plan))
      }
    },

    clearPendingPlan() {
      this.pendingPlan = null

      if (typeof window !== 'undefined') {
        window.sessionStorage.removeItem(PENDING_PLAN_KEY)
      }
    },
  },
})
