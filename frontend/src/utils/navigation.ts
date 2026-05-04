import type { Router } from 'vue-router'

export function goBack(router: Router, fallback = '/') {
  if (window.history.length > 1) {
    router.back()
    return
  }

  router.push(fallback)
}
