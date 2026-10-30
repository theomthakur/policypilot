/** Time-of-day greeting from the viewer's own clock. */
export function greeting(now: Date = new Date()): string {
  const hour = now.getHours()
  if (hour < 5) return 'Hello'
  if (hour < 12) return 'Good morning'
  if (hour < 17) return 'Good afternoon'
  return 'Good evening'
}
