import { createRouter, createWebHashHistory } from 'vue-router'
import { useUserStore } from '@/stores/user'

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    {
      path: '/',
      name: 'home',
      component: () => import('@/views/HomeView.vue'),
      meta: {
        title: '首页',
      },
    },
    {
      path: '/profile',
      name: 'profile',
      component: () => import('@/views/ProfileView.vue'),
      meta: {
        title: '我的',
      },
    },
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/LoginView.vue'),
      meta: {
        title: '登录',
      },
    },
    {
      path: '/register',
      name: 'register',
      component: () => import('@/views/RegisterView.vue'),
      meta: {
        title: '注册',
      },
    },
    {
      path: '/trip/create',
      name: 'trip-create',
      component: () => import('@/views/CreateTripView.vue'),
      meta: {
        title: '创建行程',
        requiresAuth: true,
      },
    },
    {
      path: '/trips',
      name: 'trip-list',
      component: () => import('@/views/TripListView.vue'),
      meta: {
        title: '我的行程',
        requiresAuth: true,
      },
    },
    {
      path: '/trip/planning',
      name: 'trip-planning',
      component: () => import('@/views/PlanningView.vue'),
      meta: {
        title: '规划行程',
        requiresAuth: true,
      },
    },
    {
      path: '/trip/:tripId',
      name: 'trip-detail',
      component: () => import('@/views/TripDetailView.vue'),
      meta: {
        title: '行程详情',
        requiresAuth: true,
      },
    },
    {
      path: '/:pathMatch(.*)*',
      redirect: '/',
    },
  ],
})

router.beforeEach(async (to, from) => {
  if (!to.meta.requiresAuth) return true

  const user = useUserStore()

  if (user.accessToken && !user.hasFetchedMe) {
    await user.restoreSession()
  }

  if (user.isLoggedIn) return true

  return {
    path: '/login',
    query: {
      redirect: to.fullPath,
    },
    replace: from.matched.length === 0,
  }
})

router.afterEach((to) => {
  document.title = `${String(to.meta.title || '旅行助手')} - Travel Agent`
})

export default router
