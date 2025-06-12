<template>
  <div class="file-tree">
    <el-tree
      ref="tree"
      :data="treeData"
      :props="defaultProps"
      :load="loadNode"
      node-key="id"
      lazy
      :default-expanded-keys="['0']"
      @node-click="handleNodeClick"
      @node-expand="handleNodeExpand"
    >
      <template #default="{ node, data }">
        <span class="custom-tree-node" :class="{ 'is-file': !data.isdir }">
          <el-tooltip
            :content="node.label"
            placement="top"
            :disabled="!node.label || node.label.length <= 20"
          >
            <span class="node-label">{{ truncateFileName(node.label || '') }}</span>
          </el-tooltip>
          <span v-if="data.size" class="size-text">{{ data.size }}</span>
        </span>
      </template>
    </el-tree>
  </div>
</template>

<script lang="ts">
import { defineComponent, ref, nextTick, onMounted } from 'vue'
import type { TreeNode } from '@/types'
import type Node from 'element-plus/es/components/tree/src/model/node'
import { ElMessage } from 'element-plus'
import axios from 'axios'

export default defineComponent({
  name: 'FileTree',
  emits: ['node-click'],
  setup(props, { emit }) {
    const tree = ref()
    const treeData = ref<TreeNode[]>([])
    const dbPath = ref<string | null>(null)

    const defaultProps = {
      children: 'children',
      label: 'name',
      isLeaf: (data: TreeNode) => !data.isdir
    }

    const formatSize = (size: number): string => {
      if (size === 0) return ''

      const units = [
        { size: 1024 ** 3, unit: 'GB' },
        { size: 1024 ** 2, unit: 'MB' },
        { size: 1024, unit: 'KB' },
        { size: 1, unit: 'B' }
      ]

      for (const { size: divider, unit } of units) {
        if (size >= divider) {
          const value = size / divider
          if (unit === 'B') {
            return `${Math.round(value)} ${unit}`
          }
          return `${value.toFixed(2)} ${unit}`
        }
      }

      return `${size} B`
    }

    const loadNode = async (node: Node, resolve: (data: TreeNode[]) => void) => {
      try {
        const nodeId = node.level === 0 ? '0' : node.data.id
        console.log('加载节点:', nodeId)
        const { data } = await axios.get(`/api/v1/directory-tree/${encodeURIComponent(nodeId)}`)
        
        // 格式化文件大小
        const formattedData = (data.children || []).map((item: TreeNode) => ({
          ...item,
          size: formatSize(item.value || 0)
        }))
        console.log('格式化后的数据:', formattedData)
        
        // 确保在调用 resolve 之前数据是有效的数组
        if (Array.isArray(formattedData)) {
          resolve(formattedData)
          
          // 在数据加载完成后展开节点
          nextTick(async () => {
            console.log('格式化后的数据是数组:', node.data.name,'展开状态',node.expanded)
            console.log('展开节点:', node.data.name)
            
            node.expanded = true
            await handleNodeExpand(node.data, node)
          })
        } else {
          console.error('格式化后的数据不是数组:', formattedData)
          resolve([])
        }
      } catch (error) {
        console.error('加载节点失败:', error)
        resolve([])
      }
    }

    const handleNodeClick = (data: TreeNode, node: Node) => {
      // 移除文件类型检查，允许所有节点触发点击事件
      console.log('节点点击:', data)
      emit('node-click', data)
    }

    const handleNodeExpand = async (data: TreeNode, node: Node) => {
      // 如果是文件，不触发事件
      if (!data.isdir) {
        return
      }
      console.log('节点展开:', data)
      
      try {
        // 确保节点数据已加载
        if (node.childNodes.length === 0) {
          await new Promise<void>((resolve) => {
            tree.value?.store.load(node, () => {
              resolve()
            })
          })
        }
      } catch (error) {
        console.error('展开节点失败:', error)
      }
    }

    const loadDatabase = async (dbPath: string) => {
      try {
        // 先获取数据库信息
        const { data: dbInfo } = await axios.get(`/api/v1/database-info?db_path=${encodeURIComponent(dbPath)}`)
        
        // 获取根节点数据
        const { data: rootData } = await axios.get(`/api/v1/directory-tree/0`)
        
        if (rootData) {
          // 使用数据库信息构建根节点
          const dbName = dbInfo.name.replace(/\.db$/, '')  // 移除 .db 后缀
          rootData.name = `${dbName} (${dbInfo.dir_count}个文件夹, ${dbInfo.file_count}个文件)`
          rootData.size = formatSize(dbInfo.total_size || 0)
          rootData.value = dbInfo.total_size || 0
          treeData.value = [rootData]

          // 等待DOM更新后触发根节点点击
          await nextTick()
          if (tree.value) {
            const rootNode = tree.value.getNode('0')
            if (rootNode) {
              console.log('触发根节点点击事件')
              emit('node-click', rootData)
            }
          }
        }
      } catch (error) {
        console.error('加载数据库失败:', error)
        ElMessage.error('加载数据库失败')
      }
    }

    const clearTree = () => {
      treeData.value = []
    }

    const selectNode = async (nodeId: string) => {
      if (!tree.value) return
      
      try {
        // 获取节点实例
        const node = tree.value.getNode(nodeId)
        if (node) {
          // 如果节点已经存在，直接选中并展开
          tree.value.setCurrentKey(nodeId)
          await expandToNode(node)
        } else {
          console.warn('节点未找到:', nodeId)
        }
      } catch (error) {
        console.error('选择节点失败:', error)
      }
    }

    const expandToNode = async (node: Node) => {
      if (!tree.value) return

      try {
        // 直接设置节点的展开状态
        node.expanded = true
        
        // 加载节点数据
        await new Promise<void>((resolve) => {
          tree.value?.store.load(node, () => {
            resolve()
          })
        })
      } catch (error) {
        console.error('展开节点失败:', error)
      }
    }

    const truncateFileName = (fileName: string): string => {
      if (!fileName || fileName.length <= 20) return fileName || ''
      return fileName.slice(0, 17) + '...'
    }

    return {
      tree,
      treeData,
      defaultProps,
      loadNode,
      handleNodeClick,
      handleNodeExpand,
      loadDatabase,
      clearTree,
      selectNode,
      expandToNode,
      truncateFileName
    }
  }
})
</script>

<style scoped>
.file-tree {
  height: 100%;
  overflow: auto;
}

.custom-tree-node {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 14px;
  padding-right: 8px;
}

.custom-tree-node.is-file {
  cursor: default;
  color: #606266;
}

.custom-tree-node.is-file:hover {
  background: transparent;
}

.node-label {
  flex: 1;
  min-width: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.size-text {
  color: #909399;
  font-size: 12px;
  margin-left: 8px;
  flex-shrink: 0;
}
</style> 