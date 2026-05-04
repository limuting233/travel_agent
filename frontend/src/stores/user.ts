import { defineStore } from 'pinia'
import { getCurrentUser, login, type CurrentUser } from '@/api/auth'
import { clearAccessToken, getAccessToken, setAccessToken } from '@/utils/request'

const storedAccessToken = getAccessToken()

export const useUserStore = defineStore('user', {
  state: () => ({
    isLoggedIn: Boolean(storedAccessToken),
    username: '',
    nickname: '',
    accessToken: storedAccessToken || '',
    tokenType: '',
    expiresAt: 0,
    isFetchingMe: false,
    hasFetchedMe: false,
  }),
  actions: {
    setCurrentUser(currentUser: CurrentUser) {
      this.username = currentUser.username
      this.nickname = currentUser.nickname
      this.isLoggedIn = true
      this.hasFetchedMe = true
    },

    async fetchMe(options: { silent?: boolean } = {}) {
      if (!this.accessToken) return null
      if (this.isFetchingMe) return null

      this.isFetchingMe = true

      try {
        const currentUser = await getCurrentUser()
        this.setCurrentUser(currentUser)
        return currentUser
      } catch (error) {
        this.logout()

        if (!options.silent) {
          throw error
        }

        return null
      } finally {
        this.isFetchingMe = false
      }
    },

    async restoreSession() {
      const accessToken = getAccessToken()

      if (!accessToken || this.hasFetchedMe) return

      this.accessToken = accessToken
      this.isLoggedIn = true
      await this.fetchMe({ silent: true })
    },

    async loginWithPassword(username: string, password: string) {
      const result = await login({
        username,
        password,
      })

      setAccessToken(result.access_token)

      this.accessToken = result.access_token
      this.tokenType = result.token_type
      this.expiresAt = result.expires_at
      await this.fetchMe()
    },

    logout() {
      clearAccessToken()

      this.isLoggedIn = false
      this.username = ''
      this.nickname = ''
      this.accessToken = ''
      this.tokenType = ''
      this.expiresAt = 0
      this.hasFetchedMe = false
    },
  },
})
