export interface TreeNode {
  name: string
  path?: string
  isdir: boolean
  file_size?: number
  size?: string
  children?: TreeNode[]
}

export interface DirectorySize {
  items: Array<{
    name: string
    value: number
    isdir: boolean
  }>
  total: number
} 