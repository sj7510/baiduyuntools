<script setup lang="ts">
import { ElConfigProvider } from 'element-plus'
</script>

<template>
  <el-config-provider>
    <router-view />
  </el-config-provider>
</template>

<style>
#app {
  width: 100%;
  height: 100vh;
  margin: 0;
  padding: 0;
}
</style>
