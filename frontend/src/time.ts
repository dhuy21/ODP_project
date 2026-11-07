export function formatUnixTime(value: number): string {
  const date = new Date(value * 1000)
  if (Number.isNaN(date.getTime())) {
    return ''
  }
  return date.toLocaleString()
}
