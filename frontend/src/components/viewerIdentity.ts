export function viewerFirstName(name: string | null): string {
  return name?.trim().split(/\s+/)[0] || 'You'
}
