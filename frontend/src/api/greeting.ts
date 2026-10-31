/** Time-of-day greeting from the viewer's own clock. */
export function greeting(now: Date = new Date()): string {
  const hour = now.getHours()
  if (hour < 5) return 'Hello'
  if (hour < 12) return 'Good morning'
  if (hour < 17) return 'Good afternoon'
  return 'Good evening'
}

/** A warm greeting that uses only the first word of the signed-in profile name. */
export function personalizedGreeting(
  name: string | null | undefined,
  now: Date = new Date(),
): string {
  const firstName = name?.trim().split(/\s+/)[0]
  return firstName ? `${greeting(now)}, ${firstName}` : greeting(now)
}
