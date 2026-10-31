import { afterEach, describe, expect, it } from 'vitest'
import { savedTheme } from './usePreference'

describe('savedTheme', () => {
  afterEach(() => window.localStorage.clear())

  it('starts a new visitor in light mode even when the system is dark', () => {
    window.matchMedia = () => ({ matches: true }) as MediaQueryList
    expect(savedTheme()).toBe('light')
  })

  it('uses a saved dark choice on a later visit', () => {
    window.localStorage.setItem('pp_theme', 'dark')
    expect(savedTheme()).toBe('dark')
  })
})
