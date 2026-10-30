import { useCallback, useState } from 'react'

/** A value remembered in localStorage; falls back quietly when storage is unavailable. */
export function usePreference<T extends string | boolean>(
  key: string,
  fallback: T,
): [T, (value: T) => void] {
  const [value, setValue] = useState<T>(() => {
    try {
      const stored = window.localStorage.getItem(key)
      if (stored === null) return fallback
      return (typeof fallback === 'boolean' ? stored === 'true' : stored) as T
    } catch {
      return fallback
    }
  })
  const update = useCallback(
    (next: T) => {
      setValue(next)
      try {
        window.localStorage.setItem(key, String(next))
      } catch {
        // Private mode or blocked storage: the choice still applies for this visit.
      }
    },
    [key],
  )
  return [value, update]
}

export function systemTheme(): 'light' | 'dark' {
  return window.matchMedia?.('(prefers-color-scheme: dark)').matches
    ? 'dark'
    : 'light'
}
