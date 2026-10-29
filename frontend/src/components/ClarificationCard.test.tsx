import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { ClarificationCard } from './ClarificationCard'

describe('ClarificationCard', () => {
  it('submits a suggested clarification while preserving its exact text', async () => {
    const user = userEvent.setup()
    const onReply = vi.fn()
    render(
      <ClarificationCard
        clarification={{
          prompt: 'Which records do you mean?',
          options: ['Security logs', 'Account records'],
        }}
        onReply={onReply}
      />,
    )

    await user.click(screen.getByRole('button', { name: 'Security logs' }))
    expect(onReply).toHaveBeenCalledWith('Security logs')
  })

  it('allows a free-text clarification', async () => {
    const user = userEvent.setup()
    const onReply = vi.fn()
    render(
      <ClarificationCard
        clarification={{ prompt: 'Which system?' }}
        onReply={onReply}
      />,
    )

    await user.type(
      screen.getByLabelText('Write another reply'),
      'The research VPN',
    )
    await user.click(screen.getByRole('button', { name: 'Send' }))
    expect(onReply).toHaveBeenCalledWith('The research VPN')
  })
})
