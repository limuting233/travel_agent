import type { Router } from 'vue-router'

function getInAppBackPath() {
  const state = window.history.state as { back?: unknown } | null

  return typeof state?.back === 'string' ? state.back : null
}

export function goBack(router: Router, fallback = '/') {
  const backPath = getInAppBackPath()

  if (backPath && backPath !== router.currentRoute.value.fullPath) {
    router.back()
    return
  }

  router.replace(fallback)
}
