import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import App from '../App'

function jsonResponse (body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' }
  })
}

describe('Fuego authentication', () => {
  beforeEach(() => {
    window.sessionStorage.clear()
  })

  afterEach(() => {
    cleanup()
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
  })

  it('creates an account, signs in, and returns to a requested chat invite', async () => {
    const websocket = { close: vi.fn() }
    const fetchMock = vi.fn<typeof fetch>()
      .mockResolvedValueOnce(jsonResponse({ id: 1 }))
      .mockResolvedValueOnce(jsonResponse({ auth_token: 'test-token' }))
      .mockResolvedValueOnce(jsonResponse({}))
      .mockResolvedValueOnce(jsonResponse({ messages: [] }))
    vi.stubGlobal('WebSocket', vi.fn(() => websocket))
    vi.stubGlobal('fetch', fetchMock)

    render(
      <MemoryRouter initialEntries={['/chats/invite-uri']}>
        <App />
      </MemoryRouter>
    )

    fireEvent.change(screen.getByPlaceholderText('Email Address'), {
      target: { value: 'new-user@example.com' }
    })
    fireEvent.change(screen.getByPlaceholderText('Username'), {
      target: { value: 'new_chat_user' }
    })
    fireEvent.change(screen.getByPlaceholderText('Password'), {
      target: { value: 'StrongTestPassword123!' }
    })
    fireEvent.click(screen.getByLabelText('Accept terms and Conditions'))
    fireEvent.click(screen.getByRole('button', { name: 'Sign up' }))

    expect(await screen.findByText('Share the page URL to invite new friends')).toBeInTheDocument()
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(4))

    expect(JSON.parse(String(fetchMock.mock.calls[0]?.[1]?.body))).toEqual({
      email: 'new-user@example.com',
      username: 'new_chat_user',
      password: 'StrongTestPassword123!'
    })
    expect(String(fetchMock.mock.calls[2]?.[0])).toContain('/api/chats/invite-uri/join/')
    expect(window.sessionStorage.getItem('authToken')).toBe('test-token')
  })

  it('shows server errors when sign-in fails', async () => {
    vi.stubGlobal('fetch', vi.fn<typeof fetch>().mockResolvedValue(
      jsonResponse({ non_field_errors: ['Invalid credentials'] }, 400)
    ))

    render(
      <MemoryRouter initialEntries={['/auth']}>
        <App />
      </MemoryRouter>
    )

    fireEvent.click(screen.getByRole('tab', { name: 'Sign In' }))
    fireEvent.change(screen.getByPlaceholderText('Username'), {
      target: { value: 'unknown-user' }
    })
    fireEvent.change(screen.getByPlaceholderText('Password'), {
      target: { value: 'incorrect' }
    })
    fireEvent.click(screen.getByRole('button', { name: 'Sign in' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Sign in failed')
    expect(screen.getByRole('alert')).toHaveTextContent('Invalid credentials')
  })
})
