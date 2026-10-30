import { afterEach, describe, expect, it, vi } from 'vitest'
import { newId } from './ids'

describe('newId', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('still returns a unique id where crypto.randomUUID is missing (plain HTTP)', () => {
    vi.stubGlobal('crypto', {})
    const a = newId()
    const b = newId()
    expect(a).not.toBe(b)
    expect(a.length).toBeGreaterThan(8)
  })
})
