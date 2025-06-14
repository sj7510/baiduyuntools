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
                  <div class="table-header">
                    <el-button 
                      type="primary" 
                      size="small" 
                      @click="exportToCsv"
                      :disabled="!largeFiles.length"
                    >
                      <el-icon class="el-icon--left"><Download /></el-icon>
                      导出CSV
                    </el-button>
                  </div>
                  <el-table
                    v-if="!largeFilesLoading && largeFiles.length > 0"
                    :data="largeFiles"
                    style="width: 100%"
                    size="small"
                    :default-sort="{ prop: 'size', order: 'descending' }"
                  >
                    <el-table-column prop="name" label="文件名" min-width="200" />
                    <el-table-column prop="size" label="大小" min-width="120">
                      <template #default="scope">
                        {{ formatSize(scope.row.size) }}
                      </template>
                    </el-table-column>
                    <el-table-column prop="parent_path" label="父路径" min-width="200" />
                  </el-table>
                  <el-empty v-else-if="!largeFilesLoading && largeFiles.length === 0" description="没有超过100M的大文件" />
                  <el-empty v-else description="正在加载大文件列表..." />
                </div>
                
                <!-- Duplicate files -->
                <div v-show="activeTab === 'duplicate'" class="tab-pane">
                  <div class="table-header">
                    <el-button 
                      type="primary" 
                      size="small" 
                      @click="exportDuplicateToCsv"
                      :disabled="!duplicateFiles.length"
                    >
                      <el-icon class="el-icon--left"><Download /></el-icon>
                      导出CSV
                    </el-button>
                  </div>
                  <div v-if="!duplicateFilesLoading && duplicateFiles.length > 0" class="duplicate-files-container">
                    <div v-for="group in duplicateFiles" :key="group.md5" class="duplicate-group">
                      <div class="group-header">
                        <span class="group-info">
                          重复文件组 (共{{ group.count }}个文件，总大小: {{ formatSize(group.total_size) }})
                        </span>
                        <span class="group-md5">MD5: {{ group.md5 }}</span>
                      </div>
                      <el-table
                        :data="group.files"
                        style="width: 100%"
                        size="small"
                        :default-sort="{ prop: 'size', order: 'descending' }"
                      >
                        <el-table-column prop="name" label="文件名" min-width="200" />
                        <el-table-column prop="size" label="大小" min-width="120">
                          <template #default="scope">
                            {{ formatSize(scope.row.size) }}
                          </template>
                        </el-table-column>
                        <el-table-column prop="parent_path" label="父路径" min-width="200" />
                      </el-table>
                    </div>
                  </div>
                  <el-empty v-else-if="!duplicateFilesLoading && duplicateFiles.length === 0" description="没有发现重复文件" />
                  <el-empty v-else description="正在检查重复文件..." />
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
import { defineComponent, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { QuestionFilled, Delete, Download } from '@element-plus/icons-vue'
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
    Delete,
    Download
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
    const largeFiles = ref<any[]>([])
    const largeFilesLoading = ref(false)
    const duplicateFiles = ref<any[]>([])
    const duplicateFilesLoading = ref(false)

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
        const targetDb = dbFileName || 'BaiduYunCacheFileV0.db'
        await axios.delete(`/api/v1/delete-db/${targetDb}`)
        
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

    // 监听tab切换和当前节点变化，自动加载大文件
    watch([activeTab, currentFolder], async ([tab, folder]) => {
      if (tab === 'large' && folder && folder.id) {
        largeFilesLoading.value = true
        try {
          const { data } = await axios.get(`/api/v1/large-files/${folder.id}`)
          largeFiles.value = data
        } catch (e) {
          largeFiles.value = []
          ElMessage.error('获取大文件列表失败')
        } finally {
          largeFilesLoading.value = false
        }
      }
    }, { immediate: true })

    // 监听tab切换和当前节点变化，自动加载重复文件
    watch([activeTab, currentFolder], async ([tab, folder]) => {
      if (tab === 'duplicate' && folder && folder.id) {
        duplicateFilesLoading.value = true
        try {
          const { data } = await axios.get(`/api/v1/duplicate-files/${folder.id}`)
          duplicateFiles.value = data
        } catch (e) {
          duplicateFiles.value = []
          ElMessage.error('获取重复文件列表失败')
        } finally {
          duplicateFilesLoading.value = false
        }
      }
    }, { immediate: true })

    const exportToCsv = () => {
      try {
        // 准备CSV数据
        const headers = ['文件名', '大小', '父路径']
        const rows = largeFiles.value.map(file => [
          file.name,
          formatSize(file.size),
          file.parent_path
        ])
        
        // 添加表头
        const csvContent = [
          headers.join(','),
          ...rows.map(row => row.join(','))
        ].join('\n')
        
        // 创建Blob对象
        const blob = new Blob(['\ufeff' + csvContent], { type: 'text/csv;charset=utf-8;' })
        
        // 创建下载链接
        const link = document.createElement('a')
        const url = URL.createObjectURL(blob)
        link.setAttribute('href', url)
        link.setAttribute('download', `大文件列表_${currentFolder.value.name}_${new Date().toLocaleDateString()}.csv`)
        link.style.visibility = 'hidden'
        
        // 触发下载
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
        
        ElMessage.success('导出成功')
      } catch (error) {
        console.error('导出失败:', error)
        ElMessage.error('导出失败')
      }
    }

    const exportDuplicateToCsv = () => {
      try {
        // 准备CSV数据
        const headers = ['MD5', '重复数量', '总大小', '文件名', '文件大小', '父路径']
        const rows: string[][] = []
        
        // 处理每个重复文件组
        duplicateFiles.value.forEach(group => {
          group.files.forEach(file => {
            rows.push([
              group.md5,
              group.count.toString(),
              formatSize(group.total_size),
              file.name,
              formatSize(file.size),
              file.parent_path
            ])
          })
        })
        
        // 添加表头
        const csvContent = [
          headers.join(','),
          ...rows.map(row => row.join(','))
        ].join('\n')
        
        // 创建Blob对象
        const blob = new Blob(['\ufeff' + csvContent], { type: 'text/csv;charset=utf-8;' })
        
        // 创建下载链接
        const link = document.createElement('a')
        const url = URL.createObjectURL(blob)
        link.setAttribute('href', url)
        link.setAttribute('download', `重复文件列表_${currentFolder.value.name}_${new Date().toLocaleDateString()}.csv`)
        link.style.visibility = 'hidden'
        
        // 触发下载
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
        
        ElMessage.success('导出成功')
      } catch (error) {
        console.error('导出失败:', error)
        ElMessage.error('导出失败')
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
      handleDeleteDb,
      largeFiles,
      largeFilesLoading,
      formatSize,
      exportToCsv,
      duplicateFiles,
      duplicateFilesLoading,
      exportDuplicateToCsv
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
  display: flex;
  flex: 1;
  overflow: hidden;
}

.chart-main {
  padding: 5px 20px !important;
  display: flex;
  flex: 1;
  flex-direction: column;
  min-width: 0;
  overflow: hidden;
}

.resizable-aside {
  position: relative;
  min-width: 200px;
  max-width: 800px;
  resize: horizontal;
  overflow: hidden;
  padding: 0 20px 0 0;
  flex-shrink: 0; /* 防止侧边栏被压缩 */
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
  z-index: 1; /* 确保调整手柄在最上层 */
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
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

:deep(.chart-card .el-card__body) {
  flex: 1;
  padding: 10px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
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
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.tab-pane {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-height: 0;
}

:deep(.pie-chart-container) {
  flex: 1;
  width: 100%;
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

:deep(.el-table) {
  height: 100%;
  display: flex;
  flex-direction: column;
}

:deep(.el-table__body-wrapper) {
  flex: 1;
  overflow-y: auto !important;
}

:deep(.el-table__header-wrapper) {
  position: sticky;
  top: 0;
  z-index: 1;
  background: white;
}

:deep(.el-table__inner-wrapper) {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.table-header {
  margin-bottom: 10px;
  display: flex;
  justify-content: flex-end;
}

.duplicate-files-container {
  height: 100%;
  overflow-y: auto;
  padding-right: 10px;
}

.duplicate-group {
  margin-bottom: 20px;
  border: 1px solid #ebeef5;
  border-radius: 4px;
  overflow: hidden;
}

.group-header {
  padding: 10px;
  background-color: #f5f7fa;
  border-bottom: 1px solid #ebeef5;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.group-info {
  font-weight: bold;
  color: #409EFF;
}

.group-md5 {
  color: #909399;
  font-size: 12px;
}
</style> 