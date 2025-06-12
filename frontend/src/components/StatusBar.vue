<template>
  <div class="status-bar">
    {{ status }}
  </div>
</template>

<script lang="ts">
import { defineComponent, ref } from 'vue'

export default defineComponent({
  name: 'StatusBar',
  setup() {
    const status = ref('就绪')

    const updateStatus = (message: string) => {
      status.value = message
    }

    return {
      status,
      updateStatus
    }
  }
})
</script>

<style scoped>
.status-bar {
  font-size: 12px;
  color: #606266;
  height: 100%;
  display: flex;
  align-items: center;
}
</style> 