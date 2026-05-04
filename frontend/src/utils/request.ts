import axios, { type AxiosRequestConfig } from 'axios'
import { isMockApiEnabled, mockHttpRequest, mockStreamRequest } from '@/mocks/api'

const DEFAULT_BASE_URL = '/api/v1'
const ACCESS_TOKEN_KEY = 'travel_agent_access_token'

export interface ApiResponse<T = unknown> {
  code: number
  message: string
  error_message: string | null
  data: T | null
}

export class ApiError<T = unknown> extends Error {
  code: number
  status?: number
  data: T | null

  constructor(message: string, options: { code?: number, status?: number, data?: T | null } = {}) {
    super(message)
    this.name = 'ApiError'
    this.code = options.code ?? 500
    this.status = options.status
    this.data = options.data ?? null
  }
}

export interface SseMessage<T = unknown> {
  event: string
  data: T
  id?: string
  retry?: number
}

export interface StreamRequestConfig<TBody = unknown, TData = unknown> {
  url: string
  method?: 'GET' | 'POST'
  data?: TBody
  headers?: Record<string, string>
  signal?: AbortSignal
  onEvent?: (message: SseMessage<TData>) => void
}

function getBaseURL() {
  const baseURL = import.meta.env.VITE_API_BASE_URL || DEFAULT_BASE_URL
  return baseURL.replace(/\/+$/, '')
}

function resolveURL(url: string) {
  if (/^https?:\/\//i.test(url)) return url

  const baseURL = getBaseURL()
  const path = url.replace(/^\/+/, '')
  return `${baseURL}/${path}`
}

function isApiResponse(value: unknown): value is ApiResponse {
  if (!value || typeof value !== 'object') return false

  const record = value as Record<string, unknown>
  return typeof record.code === 'number'
    && typeof record.message === 'string'
    && 'error_message' in record
    && 'data' in record
}

function readStoredToken() {
  if (typeof window === 'undefined') return null
  return window.localStorage.getItem(ACCESS_TOKEN_KEY)
}

export function getAccessToken() {
  return readStoredToken()
}

export function setAccessToken(token: string) {
  if (typeof window === 'undefined') return
  window.localStorage.setItem(ACCESS_TOKEN_KEY, token)
}

export function clearAccessToken() {
  if (typeof window === 'undefined') return
  window.localStorage.removeItem(ACCESS_TOKEN_KEY)
}

function createApiError(error: unknown) {
  if (!axios.isAxiosError(error)) {
    return new ApiError(error instanceof Error ? error.message : '请求失败')
  }

  const status = error.response?.status
  const responseData = error.response?.data

  if (isApiResponse(responseData)) {
    if (responseData.code === 401) clearAccessToken()

    return new ApiError(responseData.error_message || responseData.message || '请求失败', {
      code: responseData.code,
      status,
      data: responseData.data,
    })
  }

  if (status === 401) clearAccessToken()

  return new ApiError(error.message || '网络异常，请稍后重试', {
    code: status ?? 500,
    status,
    data: responseData ?? null,
  })
}

export const requestClient = axios.create({
  baseURL: getBaseURL(),
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
  },
})

requestClient.interceptors.request.use((config) => {
  const token = getAccessToken()

  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }

  return config
})

requestClient.interceptors.response.use(
  (response) => {
    const responseData = response.data

    if (!isApiResponse(responseData)) return responseData

    if (responseData.code === 200) return responseData.data

    if (responseData.code === 401) clearAccessToken()

    throw new ApiError(responseData.error_message || responseData.message || '请求失败', {
      code: responseData.code,
      status: response.status,
      data: responseData.data,
    })
  },
  (error) => Promise.reject(createApiError(error)),
)

export const http = {
  get<T = unknown>(url: string, config?: AxiosRequestConfig) {
    if (isMockApiEnabled()) return mockHttpRequest<T>('GET', url, undefined)

    return requestClient.get<ApiResponse<T>, T>(url, config)
  },

  post<T = unknown, TBody = unknown>(url: string, data?: TBody, config?: AxiosRequestConfig) {
    if (isMockApiEnabled()) return mockHttpRequest<T>('POST', url, data)

    return requestClient.post<ApiResponse<T>, T>(url, data, config)
  },

  put<T = unknown, TBody = unknown>(url: string, data?: TBody, config?: AxiosRequestConfig) {
    if (isMockApiEnabled()) return mockHttpRequest<T>('PUT', url, data)

    return requestClient.put<ApiResponse<T>, T>(url, data, config)
  },

  patch<T = unknown, TBody = unknown>(url: string, data?: TBody, config?: AxiosRequestConfig) {
    if (isMockApiEnabled()) return mockHttpRequest<T>('PATCH', url, data)

    return requestClient.patch<ApiResponse<T>, T>(url, data, config)
  },

  delete<T = unknown>(url: string, config?: AxiosRequestConfig) {
    if (isMockApiEnabled()) return mockHttpRequest<T>('DELETE', url, undefined)

    return requestClient.delete<ApiResponse<T>, T>(url, config)
  },
}

function parseSseMessage<TData>(chunk: string): SseMessage<TData> | null {
  let event = 'message'
  let id: string | undefined
  let retry: number | undefined
  const dataLines: string[] = []

  for (const rawLine of chunk.split(/\r?\n/)) {
    if (!rawLine || rawLine.startsWith(':')) continue

    const separatorIndex = rawLine.indexOf(':')
    const field = separatorIndex >= 0 ? rawLine.slice(0, separatorIndex) : rawLine
    let value = separatorIndex >= 0 ? rawLine.slice(separatorIndex + 1) : ''

    if (value.startsWith(' ')) value = value.slice(1)

    if (field === 'event') event = value
    if (field === 'data') dataLines.push(value)
    if (field === 'id') id = value
    if (field === 'retry') retry = Number(value)
  }

  if (!dataLines.length) return null

  const rawData = dataLines.join('\n')
  let data: TData

  try {
    data = JSON.parse(rawData) as TData
  } catch {
    data = rawData as TData
  }

  return {
    event,
    data,
    id,
    retry,
  }
}

async function parseErrorResponse(response: Response) {
  const text = await response.text()

  if (!text) {
    return new ApiError(response.statusText || '请求失败', {
      code: response.status,
      status: response.status,
    })
  }

  try {
    const data = JSON.parse(text) as unknown

    if (isApiResponse(data)) {
      if (data.code === 401) clearAccessToken()

      return new ApiError(data.error_message || data.message || '请求失败', {
        code: data.code,
        status: response.status,
        data: data.data,
      })
    }
  } catch {
    // 非 JSON 错误响应直接使用原始文本。
  }

  return new ApiError(text || response.statusText || '请求失败', {
    code: response.status,
    status: response.status,
  })
}

export async function streamRequest<TData = unknown, TBody = unknown>(
  config: StreamRequestConfig<TBody, TData>,
) {
  if (isMockApiEnabled()) {
    return mockStreamRequest<TData, TBody>(config)
  }

  const token = getAccessToken()
  const headers: Record<string, string> = {
    Accept: 'text/event-stream',
    ...config.headers,
  }

  if (config.data !== undefined) {
    headers['Content-Type'] = 'application/json'
  }

  if (token) {
    headers.Authorization = `Bearer ${token}`
  }

  const response = await fetch(resolveURL(config.url), {
    method: config.method ?? 'POST',
    headers,
    body: config.data === undefined ? undefined : JSON.stringify(config.data),
    signal: config.signal,
  })

  if (!response.ok) {
    throw await parseErrorResponse(response)
  }

  if (!response.body) {
    throw new ApiError('当前浏览器不支持流式响应')
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()

    if (done) break

    buffer += decoder.decode(value, { stream: true })

    const chunks = buffer.split(/\r?\n\r?\n/)
    buffer = chunks.pop() ?? ''

    for (const chunk of chunks) {
      const message = parseSseMessage<TData>(chunk)
      if (message) config.onEvent?.(message)
    }
  }

  buffer += decoder.decode()

  if (buffer.trim()) {
    const message = parseSseMessage<TData>(buffer)
    if (message) config.onEvent?.(message)
  }
}
