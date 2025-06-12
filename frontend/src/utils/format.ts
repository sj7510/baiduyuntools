export const formatSize = (size: number): string => {
  if (size === 0) return '0 B'

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