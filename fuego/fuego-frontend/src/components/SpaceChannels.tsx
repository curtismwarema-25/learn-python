import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import {
  API_BASE_URL,
  apiRequest,
  getErrorMessage,
  parseChatMessage,
  parseSpaceChannel,
  parseSpaceChannelMessages,
  parseSpaceChannels
} from '../api'
import type { ChatMessage, SpaceChannel } from '../api'
import ChatMessageView from './ChatMessage'
import MessageComposer from './MessageComposer'

interface SpaceChannelsProps {
  spaceId: string
  canManage: boolean
  username: string | null
}

type RealtimeStatus = 'connecting' | 'connected' | 'reconnecting' | 'offline' | 'unavailable'

function isAuthenticationAcknowledgement (value: unknown): boolean {
  return typeof value === 'object' &&
    value !== null &&
    'type' in value &&
    value.type === 'authenticated'
}

function mergeMessages (history: ChatMessage[], current: ChatMessage[]) {
  const messagesById = new Map<number, ChatMessage>()
  for (const message of [...history, ...current]) {
    if (!messagesById.has(message.id)) messagesById.set(message.id, message)
  }
  return [...messagesById.values()]
}

function channelPath (spaceId: string, channelId: string) {
  return `/spaces/${encodeURIComponent(spaceId)}/channels/${encodeURIComponent(channelId)}`
}

function ChannelConversation ({
  spaceId,
  channel,
  username,
  token
}: {
  spaceId: string
  channel: SpaceChannel
  username: string | null
  token: string | null
}) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [draft, setDraft] = useState('')
  const [loading, setLoading] = useState(true)
  const [sending, setSending] = useState(false)
  const [historyError, setHistoryError] = useState('')
  const [sendError, setSendError] = useState('')
  const [websocketError, setWebsocketError] = useState('')
  const [realtimeStatus, setRealtimeStatus] = useState<RealtimeStatus>('connecting')
  const websocketRef = useRef<WebSocket | null>(null)
  const reconnectRef = useRef<(() => void) | null>(null)

  useEffect(() => {
    setMessages([])
    setHistoryError('')
    setSendError('')
    setWebsocketError('')
    setRealtimeStatus('connecting')

    if (!token) {
      setLoading(false)
      setRealtimeStatus('unavailable')
      setHistoryError('Sign in to read this channel.')
      return undefined
    }

    const authToken = token
    const controller = new AbortController()
    let active = true
    let reconnectAttempts = 0
    let reconnectTimer: number | undefined
    let stableConnectionTimer: number | undefined
    let needsHistorySync = false
    let historySyncInProgress = false

    async function syncMessageHistory () {
      if (historySyncInProgress) return
      historySyncInProgress = true
      try {
        const history = parseSpaceChannelMessages(await apiRequest(
          `/api/spaces/${encodeURIComponent(spaceId)}/channels/${encodeURIComponent(channel.id)}/messages/`,
          { headers: { Authorization: `Token ${authToken}` }, signal: controller.signal }
        ))
        if (history.id !== channel.id) {
          throw new Error('The server returned history for a different channel.')
        }
        if (active) setMessages(current => mergeMessages(history.messages, current))
      } catch (error: unknown) {
        if (active && !controller.signal.aborted) {
          setHistoryError(getErrorMessage(error))
        }
      } finally {
        historySyncInProgress = false
      }
    }

    function scheduleReconnect () {
      if (!active || reconnectTimer !== undefined) return
      if (reconnectAttempts >= 5) {
        setRealtimeStatus('offline')
        setWebsocketError('Live updates could not reconnect. You can retry the connection.')
        return
      }

      reconnectAttempts += 1
      setRealtimeStatus('reconnecting')
      reconnectTimer = window.setTimeout(() => {
        reconnectTimer = undefined
        connectWebSocket()
      }, 1000 * (2 ** (reconnectAttempts - 1)))
    }

    function connectWebSocket () {
      if (!active) return
      setRealtimeStatus('connecting')
      const apiUrl = new URL(API_BASE_URL)
      const protocol = apiUrl.protocol === 'https:' ? 'wss:' : 'ws:'
      const socketUrl = `${protocol}//${apiUrl.host}/ws/spaces/${encodeURIComponent(spaceId)}/channels/${encodeURIComponent(channel.id)}/`
      let websocket: WebSocket

      try {
        websocket = new WebSocket(socketUrl)
      } catch (error: unknown) {
        needsHistorySync = true
        setWebsocketError(`Live updates could not connect: ${getErrorMessage(error)}`)
        scheduleReconnect()
        return
      }

      websocketRef.current = websocket
      websocket.onopen = () => {
        if (!active || websocketRef.current !== websocket) return
        try {
          websocket.send(JSON.stringify({
            type: 'authenticate',
            token: authToken
          }))
        } catch (error: unknown) {
          needsHistorySync = true
          setWebsocketError(`Real-time authentication failed: ${getErrorMessage(error)}`)
          websocket.close()
        }
      }
      websocket.onmessage = event => {
        if (!active || websocketRef.current !== websocket) return
        try {
          const payload: unknown = JSON.parse(event.data)
          if (isAuthenticationAcknowledgement(payload)) {
            setRealtimeStatus('connected')
            setWebsocketError('')
            if (stableConnectionTimer !== undefined) {
              window.clearTimeout(stableConnectionTimer)
            }
            stableConnectionTimer = window.setTimeout(() => {
              reconnectAttempts = 0
              stableConnectionTimer = undefined
            }, 30000)
            if (needsHistorySync) {
              needsHistorySync = false
              void syncMessageHistory()
            }
            return
          }
          const message = parseChatMessage(payload)
          setMessages(current => (
            current.some(existing => existing.id === message.id)
              ? current
              : [...current, message]
          ))
        } catch (error: unknown) {
          console.error('Could not parse Space channel WebSocket message:', error)
          setWebsocketError('Received an invalid real-time channel message.')
        }
      }
      websocket.onerror = () => {
        if (!active || websocketRef.current !== websocket) return
        needsHistorySync = true
        setWebsocketError('Live updates were interrupted. Reconnecting automatically.')
        websocket.close()
      }
      websocket.onclose = event => {
        if (websocketRef.current === websocket) websocketRef.current = null
        if (stableConnectionTimer !== undefined) {
          window.clearTimeout(stableConnectionTimer)
          stableConnectionTimer = undefined
        }
        if (!active) return
        needsHistorySync = true
        if (event.code === 4401 || event.code === 4403 || event.code === 4404) {
          setRealtimeStatus('unavailable')
          setWebsocketError('Real-time access was denied. Check your Space membership.')
          return
        }
        scheduleReconnect()
      }
    }

    reconnectRef.current = () => {
      if (!active) return
      if (reconnectTimer !== undefined) {
        window.clearTimeout(reconnectTimer)
        reconnectTimer = undefined
      }
      reconnectAttempts = 0
      setWebsocketError('')
      connectWebSocket()
    }

    async function loadMessages () {
      try {
        const history = parseSpaceChannelMessages(await apiRequest(
          `/api/spaces/${encodeURIComponent(spaceId)}/channels/${encodeURIComponent(channel.id)}/messages/`,
          { headers: { Authorization: `Token ${authToken}` }, signal: controller.signal }
        ))
        if (history.id !== channel.id) {
          throw new Error('The server returned history for a different channel.')
        }
        if (!active) return
        setMessages(history.messages)
        connectWebSocket()
      } catch (error: unknown) {
        if (active && !controller.signal.aborted) {
          setRealtimeStatus('unavailable')
          setHistoryError(getErrorMessage(error))
        }
      } finally {
        if (active) setLoading(false)
      }
    }

    void loadMessages()
    return () => {
      active = false
      controller.abort()
      if (reconnectTimer !== undefined) window.clearTimeout(reconnectTimer)
      if (stableConnectionTimer !== undefined) {
        window.clearTimeout(stableConnectionTimer)
      }
      reconnectRef.current = null
      websocketRef.current?.close()
      websocketRef.current = null
    }
  }, [spaceId, channel.id, token])

  async function sendMessage (event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const message = draft.trim()
    if (!token || !message || sending || channel.archived) return

    setSending(true)
    setSendError('')
    try {
      const result = parseChatMessage(await apiRequest(
        `/api/spaces/${encodeURIComponent(spaceId)}/channels/${encodeURIComponent(channel.id)}/messages/`,
        {
          method: 'POST',
          headers: {
            Authorization: `Token ${token}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ message })
        }
      ))
      setMessages(current => (
        current.some(existing => existing.id === result.id)
          ? current
          : [...current, result]
      ))
      setDraft('')
    } catch (error: unknown) {
      setSendError(getErrorMessage(error))
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="space-channel-conversation">
      <header className="space-channel-header">
        <div>
          <p className="section-index">CHANNEL</p>
          <h3>#{channel.name}</h3>
          {channel.description && <p>{channel.description}</p>}
        </div>
        <span
          className={`realtime-status realtime-status-${realtimeStatus}`}
          aria-live="polite"
        >
          <span className="realtime-indicator" aria-hidden="true" />
          {realtimeStatus === 'connected'
            ? 'LIVE'
            : realtimeStatus === 'connecting'
              ? 'CONNECTING'
              : realtimeStatus === 'reconnecting'
                ? 'RECONNECTING'
                : 'OFFLINE'}
        </span>
      </header>

      {historyError && <p className="space-error" role="alert">{historyError}</p>}
      {websocketError && (
        <div className="space-channel-feedback">
          <p className="space-error" role="alert">{websocketError}</p>
          {realtimeStatus === 'offline' && (
            <button
              className="button button-secondary"
              onClick={() => reconnectRef.current?.()}
              type="button"
            >
              Retry live updates
            </button>
          )}
        </div>
      )}
      <div
        className="message-history space-channel-history"
        role="log"
        aria-label={`${channel.name} messages`}
        aria-live="polite"
        aria-relevant="additions"
      >
        {loading
          ? <p className="conversation-state" role="status">Loading messages…</p>
          : messages.length === 0 && !historyError
            ? (
              <div className="conversation-empty">
                <span className="empty-index">NO MESSAGES YET</span>
                <h2>Start the conversation</h2>
                <p>Messages shared here are visible to active members of this Space.</p>
              </div>
            )
            : messages.map(message => (
              <ChatMessageView
                key={message.id}
                message={message}
                isOwnMessage={message.user.username === username}
              />
            ))}
      </div>
      {sendError && <p className="space-error" role="alert">{sendError}</p>}
      {channel.archived
        ? <p className="space-channel-readonly">This channel is archived and read-only.</p>
        : <MessageComposer
            value={draft}
            sending={sending}
            onChange={setDraft}
            onSubmit={sendMessage}
          />}
    </div>
  )
}

export default function SpaceChannels ({
  spaceId,
  canManage,
  username
}: SpaceChannelsProps) {
  const { channelId } = useParams()
  const navigate = useNavigate()
  const token = window.sessionStorage.getItem('authToken')
  const [channels, setChannels] = useState<SpaceChannel[]>([])
  const [loading, setLoading] = useState(true)
  const [channelsError, setChannelsError] = useState('')
  const [actionError, setActionError] = useState('')
  const [notice, setNotice] = useState('')
  const [busyAction, setBusyAction] = useState('')
  const [newName, setNewName] = useState('')
  const [newDescription, setNewDescription] = useState('')
  const [editName, setEditName] = useState('')
  const [editDescription, setEditDescription] = useState('')

  const activeChannel = channels.find(channel => channel.id === channelId) ?? null

  useEffect(() => {
    const controller = new AbortController()
    let active = true
    setLoading(true)
    setChannelsError('')

    async function loadChannels () {
      if (!token) {
        setChannelsError('Sign in to view Space channels.')
        setLoading(false)
        return
      }
      try {
        const result = parseSpaceChannels(await apiRequest(
          `/api/spaces/${encodeURIComponent(spaceId)}/channels/`,
          {
            headers: { Authorization: `Token ${token}` },
            signal: controller.signal
          }
        ))
        if (active) setChannels(result)
      } catch (error: unknown) {
        if (active && !controller.signal.aborted) {
          setChannelsError(getErrorMessage(error))
        }
      } finally {
        if (active) setLoading(false)
      }
    }

    void loadChannels()
    return () => {
      active = false
      controller.abort()
    }
  }, [spaceId, token])

  useEffect(() => {
    setEditName(activeChannel?.name ?? '')
    setEditDescription(activeChannel?.description ?? '')
  }, [activeChannel?.id, activeChannel?.name, activeChannel?.description])

  async function createChannel (event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!token || busyAction) return
    setBusyAction('Creating channel')
    setActionError('')
    setNotice('')
    try {
      const channel = parseSpaceChannel(await apiRequest(
        `/api/spaces/${encodeURIComponent(spaceId)}/channels/`,
        {
          method: 'POST',
          headers: {
            Authorization: `Token ${token}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ name: newName, description: newDescription })
        }
      ))
      setChannels(current => [...current, channel].sort((a, b) => a.name.localeCompare(b.name)))
      setNewName('')
      setNewDescription('')
      setNotice(`Channel #${channel.name} created.`)
      navigate(channelPath(spaceId, channel.id))
    } catch (error: unknown) {
      setActionError(`Channel could not be created: ${getErrorMessage(error)}`)
    } finally {
      setBusyAction('')
    }
  }

  async function updateChannel (body: { name?: string; description?: string; archived?: boolean }) {
    if (!activeChannel || !token || busyAction) return
    setBusyAction('Saving channel')
    setActionError('')
    setNotice('')
    try {
      const channel = parseSpaceChannel(await apiRequest(
        `/api/spaces/${encodeURIComponent(spaceId)}/channels/${encodeURIComponent(activeChannel.id)}/`,
        {
          method: 'PATCH',
          headers: {
            Authorization: `Token ${token}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(body)
        }
      ))
      setChannels(current => current.map(item => item.id === channel.id ? channel : item)
        .sort((a, b) => a.name.localeCompare(b.name)))
      setNotice(`Channel #${channel.name} updated.`)
    } catch (error: unknown) {
      setActionError(`Channel could not be updated: ${getErrorMessage(error)}`)
    } finally {
      setBusyAction('')
    }
  }

  async function deleteChannel () {
    if (!activeChannel || !token || busyAction) return
    if (!window.confirm(`Permanently delete empty channel #${activeChannel.name}? Channels with messages must be archived.`)) return
    setBusyAction('Deleting channel')
    setActionError('')
    setNotice('')
    try {
      await apiRequest(
        `/api/spaces/${encodeURIComponent(spaceId)}/channels/${encodeURIComponent(activeChannel.id)}/`,
        {
          method: 'DELETE',
          headers: { Authorization: `Token ${token}` }
        }
      )
      setChannels(current => current.filter(channel => channel.id !== activeChannel.id))
      navigate(`/spaces/${encodeURIComponent(spaceId)}`)
      setNotice(`Channel #${activeChannel.name} deleted.`)
    } catch (error: unknown) {
      setActionError(`Channel could not be deleted: ${getErrorMessage(error)}`)
    } finally {
      setBusyAction('')
    }
  }

  return (
    <section className="space-section space-channels-section" aria-labelledby="space-channels-heading">
      <div className="space-section-heading">
        <div>
          <p className="section-index">PARTICIPATE</p>
          <h2 id="space-channels-heading">Channels</h2>
        </div>
      </div>
      {loading && <p className="space-empty" role="status">Loading channels…</p>}
      {channelsError && <p className="space-error" role="alert">{channelsError}</p>}
      {!loading && !channelsError && (
        <div className="space-channel-layout">
          <nav className="space-channel-navigation" aria-label="Space channels">
            {channels.length === 0
              ? <p className="space-empty">This Space has no channels yet.</p>
              : (
                <ul>
                  {channels.map(channel => (
                    <li key={channel.id}>
                      <Link
                        aria-current={channel.id === channelId ? 'page' : undefined}
                        className="space-channel-link"
                        to={channelPath(spaceId, channel.id)}
                      >
                        <span>#{channel.name}</span>
                        {channel.archived && <span className="space-channel-archived">Archived</span>}
                      </Link>
                    </li>
                  ))}
                </ul>
              )}
          </nav>
          <div className="space-channel-main">
            {activeChannel
              ? (
                <>
                  <ChannelConversation
                    key={activeChannel.id}
                    spaceId={spaceId}
                    channel={activeChannel}
                    username={username}
                    token={token}
                  />
                  {canManage && (
                    <div className="space-channel-management">
                      <details>
                        <summary>Edit channel details</summary>
                        <form
                          className="space-form"
                          onSubmit={event => {
                            event.preventDefault()
                            void updateChannel({ name: editName, description: editDescription })
                          }}
                        >
                          <label>
                            Channel name
                            <input
                              maxLength={50}
                              onChange={event => setEditName(event.target.value)}
                              pattern="[A-Za-z0-9_-]+"
                              required
                              value={editName}
                            />
                          </label>
                          <label>
                            Description
                            <textarea
                              maxLength={280}
                              onChange={event => setEditDescription(event.target.value)}
                              rows={2}
                              value={editDescription}
                            />
                          </label>
                          <button
                            className="button button-secondary"
                            disabled={Boolean(busyAction)}
                            type="submit"
                          >
                            Save details
                          </button>
                        </form>
                      </details>
                      <div className="space-inline-actions">
                        <button
                          className="button button-secondary"
                          disabled={Boolean(busyAction)}
                          onClick={() => {
                            if (!activeChannel.archived || window.confirm('Restore this channel for new messages?')) {
                              void updateChannel({ archived: !activeChannel.archived })
                            }
                          }}
                          type="button"
                        >
                          {activeChannel.archived ? 'Restore channel' : 'Archive channel'}
                        </button>
                        <button
                          className="button button-danger"
                          disabled={Boolean(busyAction)}
                          onClick={() => { void deleteChannel() }}
                          type="button"
                        >
                          Delete empty channel
                        </button>
                      </div>
                    </div>
                  )}
                </>
              )
              : (
                <div className="space-channel-empty">
                  <p className="section-index">SPACE CONVERSATION</p>
                  <h3>Select a channel</h3>
                  <p>Choose a channel to read and participate in its conversation.</p>
                </div>
              )}
          </div>
        </div>
      )}
      {canManage && (
        <details className="space-channel-create">
          <summary>Create a channel</summary>
          <form className="space-form" onSubmit={createChannel}>
            <label>
              Channel name
              <input
                maxLength={50}
                onChange={event => setNewName(event.target.value)}
                pattern="[A-Za-z0-9_-]+"
                placeholder="project-updates"
                required
                value={newName}
              />
            </label>
            <label>
              Description
              <textarea
                maxLength={280}
                onChange={event => setNewDescription(event.target.value)}
                rows={2}
                value={newDescription}
              />
            </label>
            <button
              className="button button-secondary"
              disabled={Boolean(busyAction)}
              type="submit"
            >
              {busyAction || 'Create channel'}
            </button>
          </form>
        </details>
      )}
      {actionError && <p className="space-error" role="alert">{actionError}</p>}
      {notice && <p className="space-notice" role="status">{notice}</p>}
    </section>
  )
}
