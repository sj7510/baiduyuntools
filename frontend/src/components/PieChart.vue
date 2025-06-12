<template>
  <div class="pie-chart" ref="chartContainer"></div>
</template>

<script lang="ts">
import { defineComponent, ref, onMounted, onUnmounted, watch, PropType } from 'vue'
import * as echarts from 'echarts'
import type { TreeNode } from '@/types'
import { formatSize } from '@/utils/format'

export default defineComponent({
  name: 'PieChart',
  props: {
    data: {
      type: Array as PropType<any[]>,
      default: () => []
    },
    currentFolder: {
      type: Object as PropType<{name: string, id: string}>,
      default: () => ({ name: '根目录', id: '0' })
    }
  },
  emits: ['slice-click', 'slice-double-click'],
  setup(props, { emit }) {
    const chartContainer = ref<HTMLElement | null>(null)
    let chart: echarts.ECharts | null = null
    let clickTimer: number | null = null
    let lastClickIndex = -1

    onMounted(() => {
      if (chartContainer.value) {
        chart = echarts.init(chartContainer.value)
        bindEvents()
        
        // 初始化时如果有数据就更新图表
        if (props.data.length > 0) {
          updateChart(props.data)
        }
      }
    })

    onUnmounted(() => {
      if (chart) {
        chart.dispose()
      }
    })

    // 监听数据变化
    watch(() => props.data, (newData) => {
      if (chart && newData.length > 0) {
        updateChart(newData)
      }
    }, { deep: true })

    const bindEvents = () => {
      if (!chart) return

      chart.on('click', (params) => {
        const index = params.dataIndex
        
        if (clickTimer === null) {
          // 第一次点击，启动定时器
          clickTimer = window.setTimeout(() => {
            // 单击不触发任何事件
            clickTimer = null
            lastClickIndex = -1
          }, 300)
          lastClickIndex = index
        } else {
          // 可能是双击
          if (index === lastClickIndex) {
            // 是双击，清除定时器并触发双击事件
            clearTimeout(clickTimer)
            clickTimer = null
            handleDoubleClick(index)
          } else {
            // 点击了不同的切片，重置定时器
            clearTimeout(clickTimer)
            clickTimer = window.setTimeout(() => {
              // 单击不触发任何事件
              clickTimer = null
              lastClickIndex = -1
            }, 300)
          }
          lastClickIndex = index
        }
      })
    }

    const handleDoubleClick = (index: number) => {
      if (!chart) return
      const option = chart.getOption()
      const data = option.series[0].data[index]
      if (data && data.isdir) {
        emit('slice-double-click', data)
      }
    }

    const updateChart = (data: any[]) => {
      if (!chart) return
      
      console.log('更新饼图数据:', data)

      // 定义颜色数组
      const colors = [
        '#409EFF', // 蓝色
        '#67C23A', // 绿色
        '#E6A23C', // 橙色
        '#F56C6C', // 红色
        '#909399', // 灰色
        '#9B59B6', // 紫色
        '#3498DB', // 浅蓝
        '#2ECC71', // 浅绿
        '#F1C40F', // 黄色
        '#E74C3C'  // 深红
      ]

      // 计算总大小
      const totalSize = data.reduce((sum: number, item: any) => sum + (item.value || 0), 0)

      const option = {
        tooltip: {
          trigger: 'item',
          formatter: (params: any) => {
            const { name, value, data } = params
            const isDirectory = data && data.isdir
            return `${name}<br/>大小: ${formatSize(value)}${isDirectory ? ' (文件夹)' : ''}`
          }
        },
        title: {
          text: props.currentFolder.name,
          subtext: `总大小: ${formatSize(totalSize)}`,
          left: 'center',
          top: 'center',
          textStyle: {
            fontSize: 16,
            color: '#303133'
          },
          subtextStyle: {
            fontSize: 14,
            color: '#909399'
          }
        },
        series: [
          {
            name: '大小分布',
            type: 'pie',
            radius: ['40%', '70%'],
            avoidLabelOverlap: true,
            itemStyle: {
              borderRadius: 4,
              borderColor: '#fff',
              borderWidth: 2
            },
            label: {
              show: true,
              position: 'outside',
              formatter: '{b}\n{c|{d}%}',
              rich: {
                c: {
                  fontSize: 12,
                  color: '#909399'
                }
              }
            },
            labelLine: {
              length: 10,
              length2: 10,
              maxSurfaceAngle: 80
            },
            emphasis: {
              label: {
                show: true,
                fontSize: '14',
                fontWeight: 'bold'
              }
            },
            data: data.map((item, index) => ({
              id: item.id,
              name: item.name,
              value: item.value,
              path: item.path,
              isdir: item.isdir,
              itemStyle: {
                color: colors[index % colors.length]
              }
            }))
          }
        ]
      }
      
      chart.setOption(option)
    }

    return {
      chartContainer,
      updateChart
    }
  }
})
</script>

<style scoped>
.pie-chart {
  width: 100%;
  height: 100%;
  min-height: 400px;
}
</style> 