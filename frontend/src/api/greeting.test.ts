import { describe, expect, it } from 'vitest'
import { greeting } from './greeting'

const at = (hour: number) => new Date(2026, 9, 29, hour, 30)

describe('greeting', () => {
  it('follows the hour of the day', () => {
    expect(greeting(at(2))).toBe('Hello')
    expect(greeting(at(8))).toBe('Good morning')
    expect(greeting(at(12))).toBe('Good afternoon')
    expect(greeting(at(16))).toBe('Good afternoon')
    expect(greeting(at(17))).toBe('Good evening')
    expect(greeting(at(23))).toBe('Good evening')
  })
})
