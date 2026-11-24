import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import App from '../App'

function jsonResponse (body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' }
  })
}

function noContentResponse (): Response {
  return new Response(null, { status: 204 })
}

const spaceId = '435c2511-8c43-4fd7-9e0a-b08749f76271'
const channelId = '5f81bb72-46c1-4cd7-97d7-7d464c0e1abe'
const resourceId = '7529b8a8-b32a-40c3-85f7-1ba0295e80f6'

function stubWebSockets () {
  const sockets: Array<{
    url: string
    onopen: ((event: Event) => void) | null
    onmessage: ((event: MessageEvent) => void) | null
    onerror: ((event: Event) => void) | null
    onclose: ((event: CloseEvent) => void) | null
    send: ReturnType<typeof vi.fn>
    close: ReturnType<typeof vi.fn>
  }> = []
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

function detailResponse (
  membershipStatus: 'owner' | 'member' | 'pending' | 'none',
  role: 'owner' | 'administrator' | 'moderator' | 'member' | null = null
) {
  return {
    id: spaceId,
    name: 'Python Learners',
    description: 'A place to learn by building.',
    purpose: 'Share practical Python learning.',
    visibility: 'discoverable',
    role,
    membership_status: membershipStatus
  }
}

describe('Space experience', () => {
  beforeEach(() => {
    window.sessionStorage.clear()
  })

  afterEach(() => {
    cleanup()
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
  })

  it('shows only public Space metadata to signed-out visitors', async () => {
    vi.stubGlobal('fetch', vi.fn<typeof fetch>().mockResolvedValueOnce(
      jsonResponse([{
        id: spaceId,
        name: 'Python Learners',
        description: 'A place to learn by building.',
        purpose: 'Share practical Python learning.'
      }])
    ))

    render(
      <MemoryRouter initialEntries={['/spaces']}>
        <App />
      </MemoryRouter>
    )

    expect(await screen.findByRole('heading', { name: 'Discover Spaces' })).toBeInTheDocument()
    expect(screen.getByText('Python Learners')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Create Space' })).not.toBeInTheDocument()
    expect(
      screen.getAllByRole('link', { name: 'Spaces' })
        .some(link => link.getAttribute('aria-current') === 'page')
    ).toBe(true)
  })

  it('creates a private Space and navigates to its details', async () => {
    window.sessionStorage.setItem('authToken', 'test-token')
    window.sessionStorage.setItem('username', 'space_owner')
    const fetchMock = vi.fn<typeof fetch>()
      .mockResolvedValueOnce(jsonResponse([]))
      .mockResolvedValueOnce(jsonResponse([]))
      .mockResolvedValueOnce(jsonResponse({
        ...detailResponse('owner', 'owner'),
        visibility: 'private'
      }, 201))
      .mockResolvedValueOnce(jsonResponse({
        ...detailResponse('owner', 'owner'),
        visibility: 'private'
      }))
      .mockResolvedValueOnce(jsonResponse([{
        user_id: 1,
        username: 'space_owner',
        role: 'owner',
        create_date: '2026-11-17T00:00:00Z'
      }]))
      .mockResolvedValueOnce(jsonResponse({
        can_manage: true,
        token: null,
        expires_at: null
      }))
      .mockResolvedValueOnce(jsonResponse([]))
      .mockResolvedValueOnce(jsonResponse([]))
    vi.stubGlobal('fetch', fetchMock)

    render(
      <MemoryRouter initialEntries={['/spaces']}>
        <App />
      </MemoryRouter>
    )

    fireEvent.change(screen.getByRole('textbox', { name: 'Space name' }), {
      target: { value: 'Python Learners' }
    })
    fireEvent.change(screen.getByRole('textbox', { name: 'Purpose' }), {
      target: { value: 'Share practical Python learning.' }
    })
    fireEvent.click(screen.getByRole('button', { name: 'Create Space' }))

    expect(await screen.findByRole('heading', { name: 'Python Learners' })).toBeInTheDocument()
    expect(fetchMock.mock.calls[2]?.[0]).toContain('/api/spaces/')
    expect(JSON.parse(String(fetchMock.mock.calls[2]?.[1]?.body))).toEqual({
      name: 'Python Learners',
      description: '',
      purpose: 'Share practical Python learning.',
      visibility: 'private'
    })
    expect(await screen.findByRole('heading', { name: 'Members' })).toBeInTheDocument()
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(8))
  })

  it('submits and cancels a join request, including successful 204 responses', async () => {
    window.sessionStorage.setItem('authToken', 'test-token')
    const fetchMock = vi.fn<typeof fetch>()
      .mockResolvedValueOnce(jsonResponse(detailResponse('none')))
      .mockResolvedValueOnce(jsonResponse({
        id: 1,
        user_id: 2,
        username: 'new_member',
        status: 'pending',
        requested_at: '2026-11-17T00:00:00Z'
      }, 201))
      .mockResolvedValueOnce(jsonResponse(detailResponse('pending')))
      .mockResolvedValueOnce(noContentResponse())
      .mockResolvedValueOnce(jsonResponse(detailResponse('none')))
    vi.stubGlobal('fetch', fetchMock)

    render(
      <MemoryRouter initialEntries={[`/spaces/${spaceId}`]}>
        <App />
      </MemoryRouter>
    )

    fireEvent.click(await screen.findByRole('button', { name: 'Request to join' }))
    expect(await screen.findByRole('heading', { name: 'Request pending' })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Cancel request' }))

    expect(await screen.findByRole('button', { name: 'Request to join' })).toBeInTheDocument()
    expect(fetchMock.mock.calls[1]?.[1]?.method).toBe('POST')
    expect(fetchMock.mock.calls[3]?.[1]?.method).toBe('DELETE')
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('redeems a Space invite in the request body after sign-in', async () => {
    window.sessionStorage.setItem('authToken', 'test-token')
    window.sessionStorage.setItem('username', 'invited_member')
    const fetchMock = vi.fn<typeof fetch>()
      .mockResolvedValueOnce(jsonResponse({ space_id: spaceId, role: 'member' }))
      .mockResolvedValueOnce(jsonResponse(detailResponse('member', 'member')))
      .mockResolvedValueOnce(jsonResponse([
        {
          user_id: 1,
          username: 'space_owner',
          role: 'owner',
          create_date: '2026-11-17T00:00:00Z'
        },
        {
          user_id: 2,
          username: 'invited_member',
          role: 'member',
          create_date: '2026-11-17T00:00:00Z'
        }
      ]))
      .mockResolvedValueOnce(jsonResponse([]))
    vi.stubGlobal('fetch', fetchMock)

    render(
      <MemoryRouter initialEntries={['/spaces/invites/secret-invite-token']}>
        <App />
      </MemoryRouter>
    )

    expect(await screen.findByRole('heading', { name: 'Python Learners' })).toBeInTheDocument()
    expect(fetchMock.mock.calls[0]?.[0]).toContain('/api/spaces/invites/join/')
    expect(fetchMock.mock.calls[0]?.[0]).not.toContain('secret-invite-token')
    expect(fetchMock.mock.calls[0]?.[1]?.referrerPolicy).toBe('no-referrer')
    expect(JSON.parse(String(fetchMock.mock.calls[0]?.[1]?.body))).toEqual({
      token: 'secret-invite-token'
    })
  })

  it('creates a link in the Space resource library', async () => {
    window.sessionStorage.setItem('authToken', 'test-token')
    window.sessionStorage.setItem('username', 'space_member')
    const resource = {
      id: resourceId,
      type: 'link',
      title: 'Python guide',
      description: 'A practical reference.',
      url: 'https://example.com/python',
      source_domain: 'example.com',
      creator_username: 'space_member',
      status: 'active',
      deleted_at: null,
      create_date: '2026-11-17T00:00:00Z',
      update_date: '2026-11-17T00:00:00Z',
      can_edit: true,
      can_archive: true,
      can_restore: false,
      can_delete: false
    }
    const fetchMock = vi.fn<typeof fetch>().mockImplementation(async (input, init) => {
      const path = String(input)
      if (path.endsWith(`/api/spaces/${spaceId}/`)) {
        return jsonResponse(detailResponse('member', 'member'))
      }
      if (
        path.endsWith(`/api/spaces/${spaceId}/resources/`) &&
        init?.method === 'POST'
      ) {
        return jsonResponse(resource, 201)
      }
      if (path.includes(`/api/spaces/${spaceId}/resources/?`)) {
        return jsonResponse([resource])
      }
      if (path.endsWith(`/api/spaces/${spaceId}/resources/${resourceId}/`)) {
        return jsonResponse(resource)
      }
      throw new Error(`Unexpected request: ${path}`)
    })
    vi.stubGlobal('fetch', fetchMock)

    render(
      <MemoryRouter initialEntries={[`/spaces/${spaceId}/resources`]}>
        <App />
      </MemoryRouter>
    )

    expect(await screen.findByRole('heading', { name: 'Resource library' }))
      .toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Add a link' }))
    fireEvent.change(screen.getByLabelText('Title'), {
      target: { value: 'Python guide' }
    })
    fireEvent.change(screen.getByLabelText('External URL'), {
      target: { value: 'https://example.com/python' }
    })
    fireEvent.change(screen.getByLabelText('Description'), {
      target: { value: 'A practical reference.' }
    })
    fireEvent.click(screen.getByRole('button', { name: 'Add link' }))

    expect(await screen.findByRole('heading', { name: 'Python guide', level: 1 }))
      .toBeInTheDocument()
    const createCall = fetchMock.mock.calls.find(call =>
      call[1]?.method === 'POST' &&
      String(call[0]).endsWith(`/api/spaces/${spaceId}/resources/`)
    )
    expect(JSON.parse(String(createCall?.[1]?.body))).toEqual({
      title: 'Python guide',
      url: 'https://example.com/python',
      description: 'A practical reference.'
    })
  })

  it('loads channel history and sends a deduplicated message', async () => {
    window.sessionStorage.setItem('authToken', 'test-token')
    window.sessionStorage.setItem('username', 'space_member')
    const channel = {
      id: channelId,
      name: 'general',
      description: 'Shared Space conversation.',
      archived: false,
      created_by_username: 'space_owner',
      create_date: '2026-11-17T00:00:00Z',
      update_date: '2026-11-17T00:00:00Z'
    }
    const resource = {
      id: resourceId,
      type: 'link',
      title: 'Django documentation',
      description: 'Official framework reference.',
      url: 'https://docs.djangoproject.com/en/6.1/',
      source_domain: 'docs.djangoproject.com',
      creator_username: 'space_member',
      status: 'active',
      deleted_at: null,
      create_date: '2026-11-17T00:00:00Z',
      update_date: '2026-11-17T00:00:00Z',
      can_edit: true,
      can_archive: true,
      can_restore: false,
      can_delete: false
    }
    const additionalResources = Array.from({ length: 20 }, (_, index) => ({
      ...resource,
      id: `additional-resource-${index}`,
      title: `Additional resource ${index + 1}`
    }))
    const resourceOptions = [resource, ...additionalResources]
    const fetchMock = vi.fn<typeof fetch>().mockImplementation(async (input, init) => {
      const path = String(input)
      if (path.endsWith(`/api/spaces/${spaceId}/`)) {
        return jsonResponse(detailResponse('member', 'member'))
      }
      if (path.endsWith(`/api/spaces/${spaceId}/members/`)) {
        return jsonResponse([])
      }
      if (path.endsWith(`/api/spaces/${spaceId}/channels/`)) {
        return jsonResponse([channel])
      }
      if (path.endsWith(`/api/spaces/${spaceId}/resources/`)) {
        return jsonResponse(resourceOptions)
      }
      if (path.endsWith(`/api/spaces/${spaceId}/channels/${channelId}/messages/`)) {
        if (init?.method === 'POST') {
          return jsonResponse({
            id: 9,
            user: { username: 'space_member' },
            message: 'A message for the Space.',
            resources: [{
              id: resourceId,
              title: 'Django documentation',
              status: 'active'
            }]
          }, 201)
        }
        return jsonResponse({ id: channelId, name: 'general', messages: [] })
      }
      if (path.endsWith(`/api/spaces/${spaceId}/knowledge/`)) {
        return jsonResponse({ id: 11, status: 'active' }, 201)
      }
      if (path.endsWith(`/api/spaces/${spaceId}/knowledge/11/withdraw/`)) {
        return noContentResponse()
      }
      if (path.endsWith(`/api/spaces/${spaceId}/knowledge/11/history/`)) {
        return jsonResponse({
          knowledge_id: 11,
          status: 'active',
          current_version: 2,
          versions: [
            {
              id: 2,
              version_number: 2,
              content: 'A corrected message.',
              explanation: 'Clarified the example.',
              source_message_id: 9,
              created_by_username: 'space_member',
              create_date: '2026-11-17T13:00:00Z',
              is_current: true
            },
            {
              id: 1,
              version_number: 1,
              content: 'A message for the Space.',
              explanation: '',
              source_message_id: 9,
              created_by_username: 'space_member',
              create_date: '2026-11-17T12:00:00Z',
              is_current: false
            }
          ]
        })
      }
      if (path.endsWith(`/api/spaces/${spaceId}/knowledge/11/corrections/`)) {
        return jsonResponse({ id: 11, status: 'active' }, 201)
      }
      throw new Error(`Unexpected request: ${path}`)
    })
    const sockets = stubWebSockets()
    vi.stubGlobal('fetch', fetchMock)

    render(
      <MemoryRouter initialEntries={[
        `/spaces/${spaceId}/channels/${channelId}`
      ]}>
        <App />
      </MemoryRouter>
    )

    expect(await screen.findByText('Start the conversation')).toBeInTheDocument()
    expect(await screen.findByRole('link', { name: /#general/ })).toHaveAttribute(
      'aria-current',
      'page'
    )
    await waitFor(() => expect(sockets).toHaveLength(1))
    expect(sockets[0]?.url).toContain(
      `/ws/spaces/${spaceId}/channels/${channelId}/`
    )
    expect(sockets[0]?.url).not.toContain('test-token')
    act(() => sockets[0]?.onopen?.(new Event('open')))
    expect(sockets[0]?.send).toHaveBeenCalledWith(JSON.stringify({
      type: 'authenticate',
      token: 'test-token'
    }))

    const resourceSelector = await screen.findByRole(
      'listbox',
      { name: 'Choose resources to reference' }
    ) as HTMLSelectElement
    for (const option of Array.from(resourceSelector.options)) {
      option.selected = true
    }
    fireEvent.change(resourceSelector)
    await waitFor(() => {
      expect(resourceSelector.selectedOptions).toHaveLength(20)
      expect(resourceSelector.options[20]).toBeDisabled()
    })
    expect(screen.getByText(/20 of 20 resources selected/)).toBeInTheDocument()

    for (const option of Array.from(resourceSelector.options)) {
      option.selected = option.value === resourceId
    }
    fireEvent.change(resourceSelector)
    fireEvent.change(screen.getByRole('textbox', { name: 'Write a message' }), {
      target: { value: 'A message for the Space.' }
    })
    fireEvent.click(screen.getByRole('button', { name: 'Send' }))

    expect(await screen.findByText('A message for the Space.')).toBeInTheDocument()
    expect(await screen.findByRole('link', { name: 'Django documentation' }))
      .toHaveAttribute('href', `/spaces/${spaceId}/resources/${resourceId}`)
    act(() => sockets[0]?.onmessage?.({
      data: JSON.stringify({
        id: 9,
        user: { username: 'space_member' },
        message: 'A message for the Space.'
      })
    } as MessageEvent))
    expect(screen.getAllByText('A message for the Space.')).toHaveLength(1)
    const sendCall = fetchMock.mock.calls.find(call =>
      call[1]?.method === 'POST' &&
      String(call[0]).endsWith(`/api/spaces/${spaceId}/channels/${channelId}/messages/`)
    )
    expect(JSON.parse(String(sendCall?.[1]?.body))).toEqual({
      message: 'A message for the Space.',
      resource_ids: [resourceId]
    })

    fireEvent.click(screen.getByRole('button', { name: 'Preserve knowledge' }))
    expect(await screen.findByText('PRESERVED KNOWLEDGE')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Withdraw knowledge' })).toBeInTheDocument()
    const preserveCall = fetchMock.mock.calls.find(call =>
      call[1]?.method === 'POST' &&
      String(call[0]).endsWith(`/api/spaces/${spaceId}/knowledge/`)
    )
    expect(JSON.parse(String(preserveCall?.[1]?.body))).toEqual({ message_id: 9 })

    fireEvent.click(screen.getByRole('button', { name: 'View history' }))
    expect(await screen.findByText('Current version V2')).toBeInTheDocument()
    expect(screen.getByText('Clarified the example.')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Submit correction' }))
    fireEvent.change(screen.getByLabelText('Corrected content'), {
      target: { value: 'A newly corrected message.' }
    })
    fireEvent.change(screen.getByLabelText('Explanation (optional)'), {
      target: { value: 'Added missing context.' }
    })
    fireEvent.click(screen.getByRole('button', { name: 'Submit correction' }))
    await waitFor(() => expect(fetchMock.mock.calls.some(call =>
      call[1]?.method === 'POST' &&
      String(call[0]).endsWith(`/api/spaces/${spaceId}/knowledge/11/corrections/`)
    )).toBe(true))

    fireEvent.click(screen.getByRole('button', { name: 'Withdraw knowledge' }))
    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Preserve knowledge' })).toBeInTheDocument()
    })
  })

  it('keeps archived channel history readable while removing the composer', async () => {
    window.sessionStorage.setItem('authToken', 'test-token')
    const archivedChannel = {
      id: channelId,
      name: 'general',
      description: '',
      archived: true,
      created_by_username: 'space_owner',
      create_date: '2026-11-17T00:00:00Z',
      update_date: '2026-11-17T00:00:00Z'
    }
    const fetchMock = vi.fn<typeof fetch>().mockImplementation(async input => {
      const path = String(input)
      if (path.endsWith(`/api/spaces/${spaceId}/channels/`)) {
        return jsonResponse([archivedChannel])
      }
      if (path.endsWith(`/api/spaces/${spaceId}/channels/${channelId}/messages/`)) {
        return jsonResponse({ id: channelId, name: 'general', messages: [] })
      }
      if (path.endsWith(`/api/spaces/${spaceId}/members/`)) {
        return jsonResponse([])
      }
      return jsonResponse(detailResponse('member', 'member'))
    })
    stubWebSockets()
    vi.stubGlobal('fetch', fetchMock)

    render(
      <MemoryRouter initialEntries={[
        `/spaces/${spaceId}/channels/${channelId}`
      ]}>
        <App />
      </MemoryRouter>
    )

    expect(await screen.findByText('This channel is archived and read-only.'))
      .toBeInTheDocument()
    expect(await screen.findByText('Start the conversation')).toBeInTheDocument()
    expect(screen.queryByRole('textbox', { name: 'Write a message' })).not.toBeInTheDocument()
  })

  it('searches member-only Space knowledge and links results to their source', async () => {
    window.sessionStorage.setItem('authToken', 'test-token')
    window.sessionStorage.setItem('username', 'space_member')
    const channel = {
      id: channelId,
      name: 'general',
      description: 'Shared Space conversation.',
      archived: false,
      created_by_username: 'space_owner',
      create_date: '2026-11-17T00:00:00Z',
      update_date: '2026-11-17T00:00:00Z'
    }
    const fetchMock = vi.fn<typeof fetch>().mockImplementation(async input => {
      const path = String(input)
      if (path.endsWith(`/api/spaces/${spaceId}/`)) {
        return jsonResponse(detailResponse('member', 'member'))
      }
      if (path.endsWith(`/api/spaces/${spaceId}/channels/`)) {
        return jsonResponse([channel])
      }
      if (path.includes(`/api/spaces/${spaceId}/search/?`)) {
        return jsonResponse({
          count: 3,
          page: 1,
          page_size: 20,
          total_pages: 1,
          results: [
            {
              id: 'message-1',
              type: 'discussion',
              title: 'space_member',
              excerpt: 'A useful Python discussion.',
              created_at: '2026-11-17T12:00:00Z',
              author: 'space_member',
              channel,
              source_domain: null,
              source_message_id: 'message-1',
              knowledge_id: null,
              knowledge_preserved_at: null,
              source_updated_at: '2026-11-17T12:00:00Z',
              knowledge_version: null,
              knowledge_corrected: false
            },
            {
              id: resourceId,
              type: 'resource',
              title: 'Python guide',
              excerpt: 'A practical Python reference.',
              created_at: '2026-11-16T12:00:00Z',
              author: 'space_member',
              channel: null,
              source_domain: 'example.com',
              source_message_id: null,
              knowledge_id: null,
              knowledge_preserved_at: null,
              source_updated_at: null,
              knowledge_version: null,
              knowledge_corrected: false
            },
            {
              id: 'message-knowledge',
              type: 'knowledge',
              title: '#general',
              excerpt: 'A preserved Python answer.',
              created_at: '2026-11-15T12:00:00Z',
              author: 'space_member',
              channel,
              source_domain: null,
              source_message_id: 'message-knowledge',
              knowledge_id: 7,
              knowledge_preserved_at: '2026-11-15T12:00:00Z',
              source_updated_at: '2026-11-16T12:00:00Z',
              knowledge_version: 2,
              knowledge_corrected: true
            }
          ]
        })
      }
      throw new Error(`Unexpected request: ${path}`)
    })
    vi.stubGlobal('fetch', fetchMock)

    render(
      <MemoryRouter initialEntries={[`/spaces/${spaceId}/search`]}>
        <App />
      </MemoryRouter>
    )

    expect(await screen.findByRole('heading', { name: 'Search Python Learners' }))
      .toBeInTheDocument()
    fireEvent.change(screen.getByRole('searchbox', { name: 'Search discussions and resources' }), {
      target: { value: 'Python' }
    })
    fireEvent.click(screen.getByRole('button', { name: 'Search' }))

    expect(await screen.findByRole('heading', { name: '3 results' })).toBeInTheDocument()
    expect(screen.getAllByText('Python').length).toBeGreaterThan(0)
    expect(screen.getByRole('link', { name: 'space_member' })).toHaveAttribute(
      'href',
      `/spaces/${spaceId}/channels/${channelId}#message-message-1`
    )
    expect(screen.getByRole('link', { name: 'Python guide' })).toHaveAttribute(
      'href',
      `/spaces/${spaceId}/resources/${resourceId}`
    )
    expect(screen.getByRole('link', { name: '#general' })).toHaveAttribute(
      'href',
      `/spaces/${spaceId}/channels/${channelId}#message-message-knowledge`
    )
    expect(screen.getByText(/KNOWLEDGE.*general.*CORRECTED/)).toBeInTheDocument()
    const searchCall = fetchMock.mock.calls.find(call =>
      String(call[0]).includes(`/api/spaces/${spaceId}/search/?`)
    )
    expect(String(searchCall?.[0])).toContain('q=Python')
    expect(searchCall?.[1]?.headers).toEqual({ Authorization: 'Token test-token' })
  })
})
