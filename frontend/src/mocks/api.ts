const MOCK_TRIPS_KEY = 'travel_agent_mock_trips'
const MOCK_ACCESS_TOKEN_KEY = 'travel_agent_access_token'

type HttpMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'

interface MockStreamMessage<TData = unknown> {
  event: string
  data: TData
}

interface MockStreamConfig<TBody = unknown, TData = unknown> {
  url: string
  method?: 'GET' | 'POST'
  data?: TBody
  signal?: AbortSignal
  onEvent?: (message: MockStreamMessage<TData>) => void
}

interface MockPlanParams {
  location: string
  days: number
  start_date: string | null
  end_date: string | null
  preferences: string | null
}

interface MockTripScheduleItem {
  seq: number
  time_window?: string
  poi_id?: string
  poi_name?: string
  category?: string
  action: string
  duration_hour?: number
  cost?: number
  reason?: string
  photo?: string
  location?: string
  transport_mode?: string
  distance_meter?: number
  commute_time_min?: number
  from_poi?: string
  to_poi?: string
}

interface MockDailyItinerary {
  day: number
  date?: string
  weather_label?: string
  schedule: MockTripScheduleItem[]
}

interface MockTrip {
  id: string
  title: string
  location: string
  days: number
  start_date: string | null
  end_date: string | null
  preferences: string[]
  status: 'planning' | 'completed' | 'failed'
  latest_version: {
    version_no: number
    source: string
    content: {
      trip_overview: {
        title: string
        total_distance_km: number
        tags: string[]
      }
      daily_itinerary: MockDailyItinerary[]
    }
    created_at: number
  }
  created_at: number
  updated_at: number
}

const mockUser = {
  id: 'usr_mock_001',
  username: 'demo',
  nickname: '旅行者',
}

const fallbackTrip = buildMockTrip({
  location: '上海市',
  days: 3,
  start_date: '2026-05-01',
  end_date: '2026-05-03',
  preferences: '经典必玩,吃吃喝喝,Citywalk',
}, 'trip_mock_demo')

export function isMockApiEnabled() {
  return import.meta.env.VITE_USE_MOCK === 'true'
}

export async function mockHttpRequest<T>(method: HttpMethod, url: string, data?: unknown): Promise<T> {
  await delay(300)

  const path = normalizePath(url)
  const searchParams = getSearchParams(url)

  if (method === 'POST' && path === '/auth/login') {
    return {
      access_token: 'mock_access_token',
      token_type: 'bearer',
      expires_at: Math.floor(Date.now() / 1000) + 7 * 24 * 60 * 60,
    } as T
  }

  if (method === 'POST' && path === '/auth/register') {
    return null as T
  }

  if (method === 'GET' && path === '/auth/me') {
    if (!readMockToken()) {
      throw new Error('请先登录')
    }

    return mockUser as T
  }

  if (method === 'GET' && path === '/trips') {
    const page = Math.max(1, Number(searchParams.get('page') || 1))
    const pageSize = Math.min(100, Math.max(1, Number(searchParams.get('page_size') || 20)))
    const status = searchParams.get('status')
    const allTrips = Object.values(readMockTrips())
      .filter((trip) => !status || trip.status === status)
      .sort((prev, next) => next.updated_at - prev.updated_at)
    const start = (page - 1) * pageSize
    const items = allTrips.slice(start, start + pageSize).map((trip) => ({
      id: trip.id,
      title: trip.title,
      location: trip.location,
      days: trip.days,
      start_date: trip.start_date,
      end_date: trip.end_date,
      status: trip.status,
      latest_version_no: trip.latest_version.version_no,
      created_at: trip.created_at,
      updated_at: trip.updated_at,
    }))

    return {
      items,
      page,
      page_size: pageSize,
      total: allTrips.length,
    } as T
  }

  if (method === 'GET' && path.startsWith('/trips/')) {
    const tripId = decodeURIComponent(path.replace('/trips/', ''))
    const trip = readMockTrips()[tripId] || fallbackTrip

    return trip as T
  }

  throw new Error(`Mock API 未实现：${method} ${path}`)
}

export async function mockStreamRequest<TData = unknown, TBody = unknown>(
  config: MockStreamConfig<TBody, TData>,
) {
  const path = normalizePath(config.url)

  if ((config.method ?? 'POST') !== 'POST' || path !== '/travel/plan') {
    throw new Error(`Mock Stream API 未实现：${config.method ?? 'POST'} ${path}`)
  }

  const plan = config.data as MockPlanParams
  const tripId = `trip_mock_${Date.now()}`
  const threadId = `thread_mock_${Date.now()}`
  const now = Math.floor(Date.now() / 1000)
  const trip = buildMockTrip(plan, tripId)
  const trips = readMockTrips()

  trips[tripId] = trip
  writeMockTrips(trips)

  await emit(config, {
    event: 'start',
    data: {
      thread_id: threadId,
      trip_id: tripId,
      start_at: now,
    },
  })

  await emit(config, {
    event: 'agent_step',
    data: {
      agent: 'resource_agent',
      status: 'running',
      message: '正在筛选景点、美食和通勤路线',
    },
  })

  await emit(config, {
    event: 'tool_call',
    data: {
      agent: 'planner_agent',
      tool_name: 'mock_trip_planner',
      status: 'completed',
      message: '已生成每日路线草案',
      latency_ms: 420,
    },
  })

  await emitJsonChunks(config, trip.latest_version.content)

  await emit(config, {
    event: 'done',
    data: {
      trip_id: tripId,
      thread_id: threadId,
      version_no: 1,
      end_at: Math.floor(Date.now() / 1000),
    },
  })
}

function normalizePath(url: string) {
  if (/^https?:\/\//i.test(url)) {
    return new URL(url).pathname.replace(/^\/api\/v1/, '') || '/'
  }

  const path = url.split('?')[0] || ''

  return `/${path.replace(/^\/+/, '').replace(/^api\/v1\/?/, '')}`.replace(/\/+$/, '')
}

function getSearchParams(url: string) {
  if (/^https?:\/\//i.test(url)) {
    return new URL(url).searchParams
  }

  return new URL(url, window.location.origin).searchParams
}

function readMockToken() {
  if (typeof window === 'undefined') return null
  return window.localStorage.getItem(MOCK_ACCESS_TOKEN_KEY)
}

function readMockTrips() {
  if (typeof window === 'undefined') return { [fallbackTrip.id]: fallbackTrip }

  const rawValue = window.sessionStorage.getItem(MOCK_TRIPS_KEY)
  if (!rawValue) return { [fallbackTrip.id]: fallbackTrip }

  try {
    return {
      [fallbackTrip.id]: fallbackTrip,
      ...(JSON.parse(rawValue) as Record<string, MockTrip>),
    }
  } catch {
    window.sessionStorage.removeItem(MOCK_TRIPS_KEY)
    return { [fallbackTrip.id]: fallbackTrip }
  }
}

function writeMockTrips(trips: Record<string, MockTrip>) {
  if (typeof window === 'undefined') return
  window.sessionStorage.setItem(MOCK_TRIPS_KEY, JSON.stringify(trips))
}

function buildMockTrip(plan: MockPlanParams, tripId: string): MockTrip {
  const preferences = plan.preferences?.split(',').map((item) => item.trim()).filter(Boolean) ?? []
  const tags = preferences.length ? preferences : ['经典必玩', '吃吃喝喝', 'Citywalk']
  const title = `${plan.location}${plan.days}日旅行方案`
  const now = Math.floor(Date.now() / 1000)

  return {
    id: tripId,
    title,
    location: plan.location,
    days: plan.days,
    start_date: plan.start_date,
    end_date: plan.end_date,
    preferences: tags,
    status: 'completed',
    latest_version: {
      version_no: 1,
      source: 'initial',
      content: {
        trip_overview: {
          title,
          total_distance_km: plan.days * 13.8,
          tags,
        },
        daily_itinerary: Array.from({ length: plan.days }, (_, index) => buildMockDay(plan, index + 1)),
      },
      created_at: now,
    },
    created_at: now,
    updated_at: now,
  }
}

function buildMockDay(plan: MockPlanParams, day: number): MockDailyItinerary {
  const date = plan.start_date ? addDays(plan.start_date, day - 1) : undefined
  const locationPrefix = plan.location.replace(/市$/, '')

  return {
    day,
    date,
    weather_label: day % 2 === 0 ? 'INDOOR_PREFERRED' : 'OUTDOOR_PREFERRED',
    schedule: [
      {
        seq: 1,
        time_window: '09:00-11:00',
        poi_id: `mock_poi_${day}_1`,
        poi_name: `${locationPrefix}城市地标`,
        category: 'CORE_SIGHTSEEING',
        action: '浏览',
        duration_hour: 2,
        cost: 0,
        reason: '作为当天第一站，适合快速建立城市印象，路线也便于向后续区域延展。',
        photo: 'https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?auto=format&fit=crop&w=900&q=80',
        location: '121.490317,31.241701',
      },
      {
        seq: 2,
        time_window: '11:00-11:25',
        action: '通勤',
        transport_mode: 'walking',
        distance_meter: 900,
        commute_time_min: 25,
        from_poi: `${locationPrefix}城市地标`,
        to_poi: `${locationPrefix}本地餐厅`,
      },
      {
        seq: 3,
        time_window: '11:25-12:50',
        poi_id: `mock_poi_${day}_2`,
        poi_name: `${locationPrefix}本地餐厅`,
        category: 'LOCAL_GASTRONOMY',
        action: '午餐',
        duration_hour: 1.4,
        cost: 120,
        reason: '餐厅靠近上午路线，减少绕路，同时符合吃吃喝喝偏好。',
        photo: 'https://images.unsplash.com/photo-1555396273-367ea4eb4db5?auto=format&fit=crop&w=900&q=80',
        location: '121.485685,31.238177',
      },
      {
        seq: 4,
        time_window: '12:50-13:20',
        action: '通勤',
        transport_mode: 'transit_integrated',
        distance_meter: 5200,
        commute_time_min: 30,
        from_poi: `${locationPrefix}本地餐厅`,
        to_poi: `${locationPrefix}文化街区`,
      },
      {
        seq: 5,
        time_window: '13:20-17:00',
        poi_id: `mock_poi_${day}_3`,
        poi_name: `${locationPrefix}文化街区`,
        category: 'CITY_LEISURE',
        action: 'Citywalk',
        duration_hour: 3.5,
        cost: 60,
        reason: '下午安排步行街区，节奏更松，也方便根据体力删减或延长。',
        photo: 'https://images.unsplash.com/photo-1500534314209-a25ddb2bd429?auto=format&fit=crop&w=900&q=80',
        location: '121.470972,31.228809',
      },
    ],
  }
}

function addDays(dateValue: string, days: number) {
  const date = new Date(`${dateValue}T00:00:00`)
  date.setDate(date.getDate() + days)

  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')

  return `${year}-${month}-${day}`
}

async function emit<TBody, TData>(
  config: MockStreamConfig<TBody, TData>,
  message: MockStreamMessage<unknown>,
) {
  await delay(650, config.signal)
  config.onEvent?.(message as MockStreamMessage<TData>)
}

async function emitJsonChunks<TBody, TData>(
  config: MockStreamConfig<TBody, TData>,
  value: unknown,
) {
  const jsonValue = JSON.stringify(value)
  const chunkSize = Math.ceil(jsonValue.length / 6)

  for (let index = 0; index < jsonValue.length; index += chunkSize) {
    await emit(config, {
      event: 'message',
      data: {
        content: jsonValue.slice(index, index + chunkSize),
      },
    })
  }
}

function delay(ms: number, signal?: AbortSignal) {
  if (signal?.aborted) {
    return Promise.reject(new DOMException('请求已取消', 'AbortError'))
  }

  return new Promise<void>((resolve, reject) => {
    const timer = window.setTimeout(resolve, ms)

    signal?.addEventListener('abort', () => {
      window.clearTimeout(timer)
      reject(new DOMException('请求已取消', 'AbortError'))
    }, { once: true })
  })
}
