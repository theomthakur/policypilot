import { describe, expect, it } from 'vitest'
import { viewerFirstName } from './viewerIdentity'

describe('viewerFirstName', () => {
  it('uses the first word of the signed-in name', () => {
    expect(viewerFirstName('Om Thakur')).toBe('Om')
  })

  it('keeps a safe generic fallback without a profile name', () => {
    expect(viewerFirstName(null)).toBe('You')
  })
})
