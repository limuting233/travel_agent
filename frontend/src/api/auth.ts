import { http } from '@/utils/request'

export interface LoginParams {
  username: string
  password: string
}

export interface RegisterParams {
  username: string
  password: string
}

export interface LoginResult {
  access_token: string
  token_type: string
  expires_at: number
}

export interface CurrentUser {
  id: string
  username: string
  nickname: string
}

export function register(params: RegisterParams) {
  return http.post<null, RegisterParams>('/auth/register', params)
}

export function login(params: LoginParams) {
  return http.post<LoginResult, LoginParams>('/auth/login', params)
}

export function getCurrentUser() {
  return http.get<CurrentUser>('/auth/me')
}
