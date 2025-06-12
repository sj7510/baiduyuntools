<template>
  <main>
    <el-container>
      <el-header>
        <div class="header-content">
          <h1>百度云工具</h1>
          <nav>
            <router-link to="/" class="nav-link">首页</router-link>
            <router-link to="/about" class="nav-link">关于</router-link>
          </nav>
        </div>
      </el-header>

      <el-main>
        <div class="upload-section">
          <el-upload
            action="/api/v1/upload-db"
            :show-file-list="false"
            :on-success="handleUploadSuccess"
            :on-error="handleUploadError"
            :before-upload="beforeUpload"
            accept=".db"
          >
            <el-button type="primary" size="large">上传数据库</el-button>
          </el-upload>
          
          <el-button 
            v-if="currentDbPath" 
            type="danger" 
            size="large" 
            @click="handleDeleteDb"
          >
            <el-icon class="el-icon--left"><Delete /></el-icon>
            删除数据库
          </el-button>
          <router-link to="/about" class="help-link">
            <el-link type="primary">
              <el-icon class="el-icon--left"><QuestionFilled /></el-icon>
              使用方法见关于页面
            </el-link>
          </router-link>
        </div>

        <el-container class="content-container">
          <el-aside width="300px" class="resizable-aside">
            <div class="resize-handle"></div>
            <el-card class="file-tree-card">
              <template #header>
                <div class="card-header">
                  <span>文件树</span>
                </div>
              </template>
              <file-tree ref="fileTree" @node-click="handleNodeClick" />
            </el-card>
          </el-aside>
          
          <el-main class="chart-main">
            <el-card class="chart-card">
              <template #header>
                <div class="card-header">
                  <el-tabs v-model="activeTab" class="header-tabs">
                    <el-tab-pane label="大小分布" name="size" />
                    <el-tab-pane label="大文件" name="large" />
                    <el-tab-pane label="重复文件" name="duplicate" />
                  </el-tabs>
                </div>
              </template>
              
              <!-- Tab content -->
              <div class="tab-content">
                <!-- Size distribution -->
                <div v-show="activeTab === 'size'" class="tab-pane">
                  <pie-chart 
                    ref="pieChart" 
                    :data="pieChartData"
                    :current-folder="currentFolder"
                    @slice-click="handleSliceClick" 
                    @slice-double-click="handleSliceDoubleClick" 
                  />
                </div>
                
                <!-- Large files -->
                <div v-show="activeTab === 'large'" class="tab-pane">
                  <div class="empty-tab">
                    <el-empty description="大文件列表功能开发中..." />
                  </div>
                </div>
                
                <!-- Duplicate files -->
                <div v-show="activeTab === 'duplicate'" class="tab-pane">
                  <div class="empty-tab">
                    <el-empty description="重复文件功能开发中..." />
                  </div>
                </div>
              </div>
            </el-card>
          </el-main>
        </el-container>
      </el-main>
      
      <el-footer height="30px">
        <status-bar ref="statusBar" />
      </el-footer>
    </el-container>
  </main>
</template>

<script lang="ts">
import { defineComponent, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { QuestionFilled, Delete } from '@element-plus/icons-vue'
import FileTree from '@/components/FileTree.vue'
import PieChart from '@/components/PieChart.vue'
import StatusBar from '@/components/StatusBar.vue'
import axios from 'axios'
import { formatSize } from '@/utils/format'

export default defineComponent({
  name: 'HomeView',
  components: {
    FileTree,
    PieChart,
    StatusBar,
    QuestionFilled,
    Delete
  },
  setup() {
    const fileTree = ref()
    const pieChart = ref()
    const statusBar = ref()
    const currentPath = ref('')
    const pieChartData = ref<any[]>([])
    const statusMessage = ref('')
    const currentFolder = ref({ name: '根目录', id: '0' })
    const activeTab = ref('size')  // 默认显示大小分布tab
    const currentDbPath = ref('')  // 添加当前数据库路径的引用

    const beforeUpload = (file: File) => {
      if (file.name !== 'BaiduYunCacheFileV0.db') {
        ElMessage.error('只能上传 BaiduYunCacheFileV0.db 文件')
        return false
      }
      return true
    }

    const handleUploadSuccess = async (response: any) => {
      console.log('文件上传成功:', response)
      const dbPath = response.db_path
      currentDbPath.value = dbPath  // 保存数据库路径
      
      try {
        // 加载文件树
        await fileTree.value?.loadDatabase(dbPath)
        
        // 手动触发根节点的数据加载
        const { data } = await axios.get(`/api/v1/directory-tree/0`)
        console.log('获取到根节点数据:', data)
        
        // 更新饼图数据
        pieChartData.value = data.children || []
        if (pieChart.value) {
          pieChart.value.updateChart(data.children || [])
        }
        
        // 更新当前文件夹信息
        currentFolder.value = { name: data.name, id: '0' }
        
        // 更新状态栏
        statusMessage.value = `数据库加载成功，总大小: ${formatSize(data.value || 0)}`
      } catch (error) {
        console.error('加载根节点数据失败:', error)
        ElMessage.error('加载根节点数据失败')
      }
    }

    const handleUploadError = (error: any) => {
      console.error('文件上传失败:', error)
      ElMessage.error('数据库上传失败')
    }

    const handleDeleteDb = async () => {
      try {
        // 显示确认对话框
        await ElMessageBox.confirm(
          '确定要删除当前数据库吗？删除后需要重新上传数据库文件。',
          '警告',
          {
            confirmButtonText: '确定',
            cancelButtonText: '取消',
            type: 'warning',
          }
        )

        // 获取文件名
        const dbFileName = currentDbPath.value.split('/').pop()
        
        // 发送删除请求
        await axios.delete(`/api/v1/delete-db/${dbFileName}`)
        
        // 重置状态
        currentDbPath.value = ''
        pieChartData.value = []
        if (pieChart.value) {
          pieChart.value.updateChart([])
        }
        if (fileTree.value) {
          fileTree.value.clearTree()
        }
        statusMessage.value = '数据库已删除'
        
        ElMessage.success('数据库删除成功')
      } catch (error: any) {
        if (error === 'cancel') {
          return
        }
        console.error('删除数据库失败:', error)
        ElMessage.error(error.response?.data?.detail || '删除数据库失败')
      }
    }

    const handleNodeClick = async (node: TreeNode) => {
      try {
        console.log('点击节点:', node)
        currentFolder.value = { name: node.name, id: node.id || '0' }
        const nodeId = node.id || '0'
        const { data } = await axios.get(`/api/v1/directory-tree/${nodeId}`)
        console.log('获取目录树数据:', data)
        
        // 更新饼图数据
        pieChartData.value = data.children || []
        if (pieChart.value) {
          pieChart.value.updateChart(data.children || [])
        }
        statusMessage.value = `总大小: ${formatSize(data.value || 0)}`
      } catch (error) {
        console.error('获取目录树失败:', error)
        ElMessage.error('获取目录树失败')
      }
    }

    const handleSliceClick = (item: any) => {
      console.log('饼图切片点击:', item)
      if (item.isdir) {
        fileTree.value?.selectNode(item.id)
        statusMessage.value = `选中: ${item.name} (${formatSize(item.value)})`
      }
    }

    const handleSliceDoubleClick = async (item: any) => {
      console.log('饼图切片双击:', item)
      if (item.isdir) {
        currentPath.value = item.id
        // 暂时注释掉双击扇区的数据加载逻辑
        // await fileTree.value?.selectNode(item.id)
        // handleNodeClick(item)
      }
    }

    return {
      fileTree,
      pieChart,
      statusBar,
      currentPath,
      pieChartData,
      statusMessage,
      currentFolder,
      activeTab,
      currentDbPath,
      beforeUpload,
      handleUploadSuccess,
      handleUploadError,
      handleNodeClick,
      handleSliceClick,
      handleSliceDoubleClick,
      handleDeleteDb
    }
  }
})
</script>

<style scoped>
.el-header {
  background-color: #409EFF;
  color: white;
  padding: 0 20px;
  height: auto !important;
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 0;
}

.upload-section {
  margin: 20px 0;
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 15px;
}

h1 {
  margin: 0;
  font-size: 24px;
}

nav {
  display: flex;
  gap: 20px;
}

.nav-link {
  color: white;
  text-decoration: none;
  font-size: 16px;
}

.nav-link:hover {
  text-decoration: underline;
}

.router-link-active {
  font-weight: bold;
}

.content-container {
  height: calc(100vh - 200px);
  min-height: 400px;
}

.chart-main {
  padding: 5px 20px !important;
}

.resizable-aside {
  position: relative;
  min-width: 200px;
  max-width: 800px;
  resize: horizontal;
  overflow: hidden;
  padding: 0 20px 0 0;
}

.resize-handle {
  position: absolute;
  right: 0;
  top: 0;
  bottom: 0;
  width: 5px;
  background-color: #e6e6e6;
  cursor: col-resize;
  transition: background-color 0.3s;
}

.resize-handle:hover {
  background-color: #409EFF;
}

.file-tree-card {
  height: 100%;
  display: flex;
  flex-direction: column;
}

:deep(.file-tree-card .el-card__body) {
  flex: 1;
  overflow: hidden;
  padding: 10px;
  display: flex;
  flex-direction: column;
}

:deep(.file-tree) {
  flex: 1;
  overflow: auto;
}

:deep(.el-tree) {
  height: 100%;
}

.chart-card {
  height: 100%;
}

.card-header {
  padding: 0;
}

:deep(.header-tabs > .el-tabs__header) {
  margin: 0;
}

:deep(.header-tabs .el-tabs__nav-wrap::after) {
  display: none;
}

.tab-content {
  height: 100%;
}

.tab-pane {
  height: 100%;
}

.empty-tab {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.el-footer {
  border-top: 1px solid #e6e6e6;
  padding: 0 20px;
  display: flex;
  align-items: center;
}

.help-link {
  text-decoration: none;
}

:deep(.el-icon--left) {
  margin-right: 5px;
}
</style> 