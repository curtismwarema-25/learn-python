import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import App from '../App'

function jsonResponse (body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { 'Content-Type': 'application/json' }
  })
}

function stubWebSockets () {
  const sockets: MockWebSocket[] = []
  class MockWebSocket {
    url: string
    onopen: ((event: Event) => void) | null = null
    onmessage: ((event: MessageEvent) => void) | null = null
    onerror: ((event: Event) => void) | null = null
    onclose: ((event: CloseEvent) => void) | null = null
    send = vi.fn()
    close = vi.fn()

    constructor (url: string) {
      this.url = url
      sockets.push(this)
    }
  }
  vi.stubGlobal('WebSocket', MockWebSocket)
  return sockets
}

describe('Conversation interface', () => {
  beforeEach(() => {
    window.sessionStorage.clear()
  })

  afterEach(() => {
    cleanup()
    vi.useRealTimers()
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
  })

  it('loads the empty state and sends a message through the chat API', async () => {
    window.sessionStorage.setItem('authToken', 'test-token')
    window.sessionStorage.setItem('username', 'curious_learner')

    const fetchMock = vi.fn<typeof fetch>()
      .mockResolvedValueOnce(jsonResponse({ messages: [] }))
      .mockResolvedValueOnce(jsonResponse({
        can_manage: true,
        token: 'invite-token',
        expires_at: '2026-12-01T00:00:00Z'
      }))
      .mockResolvedValueOnce(jsonResponse({
        can_manage: true,
        token: 'rotated-invite-token',
        expires_at: '2026-12-08T00:00:00Z'
      }))
      .mockResolvedValueOnce(jsonResponse({
        id: 8,
        user: { username: 'curious_learner' },
        message: 'I want to understand how AI learns from examples.'
      }))
    vi.stubGlobal('fetch', fetchMock)
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    vi.stubGlobal('WebSocket', class { close = vi.fn() })

    render(
      <MemoryRouter initialEntries={['/chats/test-uri']}>
        <App />
      </MemoryRouter>
    )

    expect(await screen.findByText(/Start with what's on your mind/)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Open invite' })).toHaveAttribute(
      'href',
      '/invites/invite-token'
    )
    fireEvent.click(screen.getByRole('button', { name: 'Rotate' }))
    expect(await screen.findByText('A new seven-day invite link is ready.')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Open invite' })).toHaveAttribute(
      'href',
      '/invites/rotated-invite-token'
    )
    fireEvent.change(screen.getByRole('textbox', { name: 'Write a message' }), {
      target: { value: 'I want to understand how AI learns from examples.' }
    })
    fireEvent.click(screen.getByRole('button', { name: 'Send' }))

    expect(await screen.findByText('I want to understand how AI learns from examples.')).toBeInTheDocument()
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(4))
    expect(JSON.parse(String(fetchMock.mock.calls[3]?.[1]?.body))).toEqual({
      message: 'I want to understand how AI learns from examples.'
    })
    expect(fetchMock.mock.calls[2]?.[1]?.method).toBe('POST')
  })

  it('shows an expired invite and lets its owner create a replacement', async () => {
    window.sessionStorage.setItem('authToken', 'test-token')
    const fetchMock = vi.fn<typeof fetch>()
      .mockResolvedValueOnce(jsonResponse({ messages: [] }))
      .mockResolvedValueOnce(jsonResponse({
        can_manage: true,
        token: null,
        expires_at: '2025-01-01T00:00:00Z'
      }))
      .mockResolvedValueOnce(jsonResponse({
        can_manage: true,
        token: 'replacement-token',
        expires_at: '2026-12-01T00:00:00Z'
      }))
    const sockets = stubWebSockets()
    vi.stubGlobal('fetch', fetchMock)

    render(
      <MemoryRouter initialEntries={['/chats/test-uri']}>
        <App />
      </MemoryRouter>
    )

    expect(await screen.findByText(/Invite expired/)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Create invite' }))

    expect(await screen.findByRole('link', { name: 'Open invite' })).toHaveAttribute(
      'href',
      '/invites/replacement-token'
    )
    expect(fetchMock.mock.calls[2]?.[1]?.method).toBe('POST')
    expect(sockets).toHaveLength(1)
  })

  it('reconnects after a dropped socket and refreshes missed history', async () => {
    window.sessionStorage.setItem('authToken', 'test-token')
    window.sessionStorage.setItem('username', 'curious_learner')

    const fetchMock = vi.fn<typeof fetch>()
      .mockResolvedValueOnce(jsonResponse({
        messages: [{ id: 1, user: { username: 'another_learner' }, message: 'First message' }]
      }))
      .mockResolvedValueOnce(jsonResponse({
        can_manage: false,
        token: null,
        expires_at: null
      }))
      .mockResolvedValueOnce(jsonResponse({
        messages: [
          { id: 1, user: { username: 'another_learner' }, message: 'First message' },
          { id: 2, user: { username: 'another_learner' }, message: 'Message sent while disconnected' }
        ]
      }))
    const sockets = stubWebSockets()
    vi.stubGlobal('fetch', fetchMock)

    render(
      <MemoryRouter initialEntries={['/chats/test-uri']}>
        <App />
      </MemoryRouter>
    )

    expect(await screen.findByText('First message')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Rotate' })).not.toBeInTheDocument()
    await waitFor(() => expect(sockets).toHaveLength(1))
    expect(sockets[0]?.url).not.toContain('test-token')

    act(() => sockets[0]?.onopen?.(new Event('open')))
    expect(sockets[0]?.send).toHaveBeenCalledWith(JSON.stringify({
      type: 'authenticate',
      token: 'test-token'
    }))
    act(() => sockets[0]?.onmessage?.({
      data: JSON.stringify({ type: 'authenticated' })
    } as MessageEvent))
    expect(screen.getByText('LIVE')).toBeInTheDocument()
    act(() => sockets[0]?.onclose?.(new CloseEvent('close')))
    expect(screen.getByText('RECONNECTING')).toBeInTheDocument()

    await waitFor(() => expect(sockets).toHaveLength(2), { timeout: 2500 })
    act(() => sockets[1]?.onopen?.(new Event('open')))
    act(() => sockets[1]?.onmessage?.({
      data: JSON.stringify({ type: 'authenticated' })
    } as MessageEvent))

    expect(await screen.findByText('Message sent while disconnected')).toBeInTheDocument()
    expect(screen.getAllByText('First message')).toHaveLength(1)
    expect(screen.getByText('LIVE')).toBeInTheDocument()
    expect(fetchMock).toHaveBeenCalledTimes(3)
  })

  it('stops automatic retries and offers a manual retry', async () => {
    window.sessionStorage.setItem('authToken', 'test-token')
    const fetchMock = vi.fn<typeof fetch>()
      .mockResolvedValueOnce(jsonResponse({ messages: [] }))
      .mockResolvedValueOnce(jsonResponse({
        can_manage: true,
        token: null,
        expires_at: null
      }))
    const sockets = stubWebSockets()
    vi.stubGlobal('fetch', fetchMock)

    render(
      <MemoryRouter initialEntries={['/chats/test-uri']}>
        <App />
      </MemoryRouter>
    )

    await screen.findByText(/Start with what's on your mind/)
    await waitFor(() => expect(sockets).toHaveLength(1))
    vi.useFakeTimers()

    await act(async () => {
      for (const delay of [1000, 2000, 4000, 8000, 16000]) {
        sockets[sockets.length - 1]?.onclose?.(new CloseEvent('close'))
        await vi.advanceTimersByTimeAsync(delay)
      }
      sockets[sockets.length - 1]?.onclose?.(new CloseEvent('close'))
    })

    expect(screen.getByText('OFFLINE')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Retry connection' }))
    expect(sockets).toHaveLength(7)
    expect(screen.getByText('CONNECTING')).toBeInTheDocument()
  })
})
