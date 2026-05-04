import type { Router } from 'vue-router'

interface GoBackOptions {
  blockedBackPaths?: string[]
}

function getInAppBackPath() {
  const state = window.history.state as { back?: unknown } | null

  return typeof state?.back === 'string' ? state.back : null
}

function isBlockedBackPath(backPath: string, blockedBackPaths: string[]) {
  return blockedBackPaths.some((path) => (
    backPath === path
    || backPath.startsWith(`${path}?`)
    || backPath.startsWith(`${path}#`)
  ))
}

export function goBack(router: Router, fallback = '/', options: GoBackOptions = {}) {
  const backPath = getInAppBackPath()

  if (
    backPath
    && backPath !== router.currentRoute.value.fullPath
    && !isBlockedBackPath(backPath, options.blockedBackPaths ?? [])
  ) {
    router.back()
    return
  }

  router.replace(fallback)
}
