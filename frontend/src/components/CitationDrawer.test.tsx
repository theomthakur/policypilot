import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { Citation } from '../api/types'
import { CitationDrawer } from './CitationDrawer'

const citation: Citation = {
  id: 'citation-1',
  number: 1,
  document_id: 'doc-1',
  document_title: 'Remote Access Policy',
  page: 3,
  quote: 'Multi-factor authentication is required.',
  validation_status: 'verified',
}

afterEach(() => vi.restoreAllMocks())

describe('CitationDrawer', () => {
  it('loads the cited page, highlights the quote, and closes', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(
        JSON.stringify({
          document_id: 'doc-1',
          document_title: 'Remote Access Policy',
          page: 3,
          text: 'Remote access rules. Multi-factor authentication is required. Contact support.',
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } },
      ),
    )
    const onClose = vi.fn()
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    })

    render(
      <QueryClientProvider client={queryClient}>
        <CitationDrawer citation={citation} onClose={onClose} />
      </QueryClientProvider>,
    )

    expect(
      await screen.findByText('Multi-factor authentication is required.', {
        selector: 'mark',
      }),
    ).toBeInTheDocument()
    expect(screen.getByText('Quote verified on this page')).toBeInTheDocument()
    await userEvent.click(
      screen.getByRole('button', { name: 'Close citation' }),
    )
    expect(onClose).toHaveBeenCalledOnce()
  })
})
