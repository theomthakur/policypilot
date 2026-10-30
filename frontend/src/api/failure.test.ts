import { describe, expect, it } from 'vitest'
import { failureAnswer } from './failure'

describe('failureAnswer', () => {
  it('always gives a readable reply, even when the server sent no answer', () => {
    const answer = failureAnswer(null)
    expect(answer.paragraphs[0]).toMatch(/could not finish/i)
    expect(answer.notices[0].message).toMatch(/did not complete/i)
    expect(answer.clarification).toBeNull()
  })

  it('keeps a server-provided message when there is one', () => {
    const answer = failureAnswer({
      paragraphs: ['Something went wrong while answering.'],
      claims: [],
      citations: [],
      notices: [],
      clarification: null,
    })
    expect(answer.paragraphs).toEqual(['Something went wrong while answering.'])
  })
})
