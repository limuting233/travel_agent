<script setup lang="ts">
import { onBeforeUnmount, onMounted } from 'vue'

const props = defineProps<{
  open: boolean
}>()

const emit = defineEmits<{
  'update:open': [value: boolean]
}>()

function close() {
  emit('update:open', false)
}

function handleKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape' && props.open) {
    close()
  }
}

onMounted(() => {
  window.addEventListener('keydown', handleKeydown)
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', handleKeydown)
})
</script>

<template>
  <Teleport to="body">
    <Transition
      enter-active-class="duration-150 ease-out"
      enter-from-class="opacity-0"
      enter-to-class="opacity-100"
      leave-active-class="duration-120 ease-in"
      leave-from-class="opacity-100"
      leave-to-class="opacity-0"
    >
      <div v-if="open" class="fixed inset-0 z-50 bg-black/45" @click="close"></div>
    </Transition>

    <Transition
      enter-active-class="duration-150 ease-out"
      enter-from-class="translate-y-3 scale-95 opacity-0"
      enter-to-class="translate-y-0 scale-100 opacity-100"
      leave-active-class="duration-120 ease-in"
      leave-from-class="translate-y-0 scale-100 opacity-100"
      leave-to-class="translate-y-3 scale-95 opacity-0"
    >
      <div
        v-if="open"
        class="fixed inset-0 z-50 flex items-center justify-center px-5"
        @click="close"
      >
        <section
          class="w-full max-w-[360px] rounded-2xl border border-border bg-background p-5 text-foreground shadow-lg"
          role="alertdialog"
          aria-modal="true"
          @click.stop
        >
          <slot />
        </section>
      </div>
    </Transition>
  </Teleport>
</template>
