import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { AccountMenu } from './AccountMenu'
import { SignInScreen } from './SignInScreen'

describe('SignInScreen', () => {
  it('offers one clear way in and says why the person is here', () => {
    render(<SignInScreen reason="expired" />)
    expect(screen.getByRole('alert')).toHaveTextContent('Your sign-in ended')
    expect(screen.getByRole('link', { name: 'Sign in' })).toHaveAttribute(
      'href',
      '/api/v1/auth/login',
    )
  })

  it('does not announce an error on a first visit', () => {
    render(<SignInScreen reason="first" />)
    expect(screen.queryByRole('alert')).toBeNull()
  })
})

describe('AccountMenu', () => {
  it('shows who is signed in and signs out on request', async () => {
    const user = userEvent.setup()
    const onSignOut = vi.fn()
    render(
      <AccountMenu
        name="Alice Analyst"
        email="alice@example.test"
        onSignOut={onSignOut}
      />,
    )
    await user.click(screen.getByRole('button', { name: /Account menu/ }))
    expect(screen.getByText('alice@example.test')).toBeInTheDocument()
    await user.click(screen.getByRole('menuitem', { name: 'Sign out' }))
    expect(onSignOut).toHaveBeenCalledOnce()
  })

  it('closes with Escape', async () => {
    const user = userEvent.setup()
    render(<AccountMenu name="Bob" email={null} onSignOut={() => undefined} />)
    await user.click(screen.getByRole('button', { name: /Account menu/ }))
    await user.keyboard('{Escape}')
    expect(screen.queryByRole('menu')).toBeNull()
  })
})
