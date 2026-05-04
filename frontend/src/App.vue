<script setup lang="ts">
import { onMounted } from 'vue'
import { Toaster } from '@/components/ui/sonner'
import { useUserStore } from '@/stores/user'

const user = useUserStore()

onMounted(() => {
  void user.restoreSession()
})
</script>

<template>
  <RouterView />
  <Toaster position="top-center" rich-colors />
</template>
