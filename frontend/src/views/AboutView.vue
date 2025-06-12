<template>
  <main class="about">
    <el-card class="about-card">
      <template #header>
        <div class="card-header">
          <h2>关于百度云工具</h2>
          <el-button type="primary" @click="$router.push('/')" plain>
            <el-icon><ArrowLeft /></el-icon>
            返回主页
          </el-button>
        </div>
      </template>
      
      <div class="about-content">
        <section>
          <h3>功能介绍</h3>
          <p>这是一个用于分析百度网盘数据的工具，可以帮助你：</p>
          <ul>
            <li>可视化展示文件夹大小分布</li>
            <li>快速浏览文件结构</li>
            <li>分析存储空间占用</li>
            <li>定位大文件和文件夹</li>
          </ul>
        </section>

        <section>
          <h3>使用说明</h3>
          <ol>
            <li>查找缓存文件</li>
            <li>使用工具</li>
          </ol>
        </section>

        <section>
          <h3>技术说明</h3>
          <ul>
            <li>前端使用 Vue 3 + TypeScript + Element Plus 开发</li>
            <li>后端使用 FastAPI + SQLite 开发</li>
            <li>使用 ECharts 实现数据可视化</li>
          </ul>
        </section>

        <section>
          <h3>注意事项</h3>
          <ul>
            <li>支持的数据库文件为百度网盘客户端的缓存数据库文件（*.db）</li>
            <li>大文件夹的大小计算可能需要一些时间，请耐心等待</li>
            <li>文件树支持展开/折叠操作，可以逐级浏览文件结构</li>
            <li>饼图支持单击（选中）和双击（进入）操作</li>
          </ul>
        </section>
      </div>
    </el-card>

    <el-card class="instruction-card">
      <template #header>
        <div class="card-header">
          <h2>使用说明</h2>
        </div>
      </template>
      
      <div class="instruction-content">
        <h3>1. 查找缓存文件</h3>
        <p>在使用本工具之前，需要先找到百度网盘的缓存文件 <code>BaiduYunCacheFileV0.db</code>：</p>
        
        <el-alert
          title="注意"
          type="warning"
          description="请确保缓存文件大小不再增加后再使用，这表示文件缓存已完成。"
          show-icon
          :closable="false"
          class="notice-alert"
        />
        
        <h4>方法一：通过快捷方式（推荐）</h4>
        <ol>
          <li>在百度网盘快捷方式上右键，选择"打开文件位置"（注：Windows XP 系统不适用此方法）</li>
          <li>找到并进入类似这样的目录：<br/>
            <code>C:\Users\[用户名]\AppData\Roaming\baidu\BaiduYunGuanjia\users</code>
          </li>
          <li>打开文件名较长的目录（通常以数字和字母组合命名）</li>
          <li>在该目录下找到 <code>BaiduYunCacheFileV0.db</code> 文件</li>
        </ol>

        <h4>方法二：通过快捷方式属性</h4>
        <ol>
          <li>右键点击百度网盘快捷方式，选择"属性"</li>
          <li>查看"快捷方式目标"字段</li>
          <li>按照类似路径：<code>AppData\Roaming\baidu\BaiduYunGuanjia\users</code> 找到缓存文件</li>
        </ol>

        <div class="tips">
          <h4>注意事项：</h4>
          <ul>
            <li>缓存文件位置取决于你的百度网盘安装位置</li>
            <li>users 目录下可能有多个文件夹，以不同的网盘账号命名</li>
            <li>请等待文件大小稳定后再使用，这表示缓存已完成</li>
          </ul>
        </div>

        <h3>2. 使用工具</h3>
        <ol>
          <li>点击首页的"上传数据库"按钮</li>
          <li>选择找到的 <code>BaiduYunCacheFileV0.db</code> 文件</li>
          <li>等待文件分析完成</li>
          <li>使用左侧文件树浏览目录结构</li>
          <li>使用右侧标签页查看：
            <ul>
              <li>大小分布：以饼图形式展示文件大小分布</li>
              <li>大文件：查看占用空间较大的文件</li>
              <li>重复文件：查找重复的文件</li>
            </ul>
          </li>
        </ol>
      </div>
    </el-card>
  </main>
</template>

<script lang="ts">
import { defineComponent } from 'vue'
import { ArrowLeft } from '@element-plus/icons-vue'

export default defineComponent({
  name: 'AboutView',
  components: {
    ArrowLeft
  }
})
</script>

<style scoped>
.about {
  max-width: 800px;
  margin: 20px auto;
  padding: 0 20px;
}

.about-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

h2 {
  margin: 0;
  color: #409EFF;
}

.about-content {
  color: #333;
}

section {
  margin-bottom: 30px;
}

h3 {
  color: #409EFF;
  margin: 0 0 15px 0;
}

ul, ol {
  padding-left: 20px;
  margin: 10px 0;
}

li {
  margin: 8px 0;
  line-height: 1.5;
}

p {
  margin: 10px 0;
  line-height: 1.5;
}

.el-button {
  display: flex;
  align-items: center;
  gap: 5px;
}

.el-icon {
  margin-right: 2px;
}

.instruction-card {
  margin-bottom: 20px;
}

.instruction-content {
  line-height: 1.6;
}

h4 {
  color: #606266;
  margin-top: 20px;
  margin-bottom: 10px;
}

code {
  background-color: #f5f7fa;
  padding: 2px 6px;
  border-radius: 4px;
  color: #e6a23c;
  font-family: monospace;
}

.notice-alert {
  margin: 16px 0;
}

.tips {
  background-color: #f5f7fa;
  padding: 15px 20px;
  border-radius: 4px;
  margin: 20px 0;
}

.tips h4 {
  margin-top: 0;
  color: #f56c6c;
}
</style> 