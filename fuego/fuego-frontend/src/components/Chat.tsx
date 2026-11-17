import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  API_BASE_URL,
  apiRequest,
  getErrorMessage,
  parseChatMessage,
  parseChatMessages,
  parseChatUri
} from '../api'
import type { ChatMessage as ChatMessageData } from '../api'
import AppShell from './AppShell'
import ChatMessage from './ChatMessage'
import MessageComposer from './MessageComposer'

type RealtimeStatus = 'connecting' | 'connected' | 'reconnecting' | 'offline' | 'unavailable'

const MAX_RECONNECT_ATTEMPTS = 5

function mergeMessages (history: ChatMessageData[], current: ChatMessageData[]) {
  const messagesById = new Map<number, ChatMessageData>()
  for (const message of [...history, ...current]) {
    if (!messagesById.has(message.id)) messagesById.set(message.id, message)
  }
  return [...messagesById.values()]
}

export default function Chat () {
  const { uri } = useParams()
  const navigate = useNavigate()
  const [username] = useState(() => window.sessionStorage.getItem('username'))
  const [messages, setMessages] = useState<ChatMessageData[]>([])
  const [messageDraft, setMessageDraft] = useState('')
  const [loading, setLoading] = useState(false)
  const [creatingConversation, setCreatingConversation] = useState(false)
  const [sendingMessage, setSendingMessage] = useState(false)
  const [errorMessage, setErrorMessage] = useState('')
  const [websocketError, setWebsocketError] = useState('')
  const [realtimeStatus, setRealtimeStatus] = useState<RealtimeStatus>('connecting')
  const websocketRef = useRef<WebSocket | null>(null)
  const reconnectRef = useRef<(() => void) | null>(null)

  useEffect(() => {
    setMessages([])
    setErrorMessage('')
    setWebsocketError('')
    setRealtimeStatus('connecting')
    reconnectRef.current = null

    if (!uri) {
      setLoading(false)
      setRealtimeStatus('unavailable')
      return undefined
    }
    const chatUri = uri

    const token = window.sessionStorage.getItem('authToken')
    if (!token) {
      setLoading(false)
      setRealtimeStatus('unavailable')
      setErrorMessage('Your session has expired. Please sign in again.')
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
    setLoading(true)

    async function syncMessageHistory () {
      if (historySyncInProgress) return
      historySyncInProgress = true
      try {
        const history = parseChatMessages(await apiRequest(
          `/api/chats/${encodeURIComponent(chatUri)}/messages/`,
          { headers: { Authorization: `Token ${authToken}` }, signal: controller.signal }
        ))

        if (active) setMessages(current => mergeMessages(history, current))
      } catch (error: unknown) {
        if (active && !controller.signal.aborted) {
          setWebsocketError(
            `Live updates returned, but message history could not be refreshed: ${getErrorMessage(error)}`
          )
        }
      } finally {
        historySyncInProgress = false
      }
    }

    function scheduleReconnect () {
      if (!active || reconnectTimer !== undefined) return
      if (reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
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

      const apiUrl = new URL(API_BASE_URL)
      const protocol = apiUrl.protocol === 'https:' ? 'wss:' : 'ws:'
      const socketUrl = `${protocol}//${apiUrl.host}/ws/chats/${encodeURIComponent(chatUri)}/?token=${encodeURIComponent(authToken)}`
      let websocket: WebSocket

      try {
        websocket = new WebSocket(socketUrl)
      } catch (error: unknown) {
        needsHistorySync = true
        setWebsocketError(`Real-time updates could not connect: ${getErrorMessage(error)}`)
        scheduleReconnect()
        return
      }

      websocketRef.current = websocket
      websocket.onopen = () => {
        if (!active || websocketRef.current !== websocket) return
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
      }
      websocket.onmessage = event => {
        if (!active || websocketRef.current !== websocket) return
        try {
          const payload: unknown = JSON.parse(event.data)
          addMessage(parseChatMessage(payload))
        } catch (error) {
          console.error('Could not parse chat WebSocket message:', error)
          setWebsocketError('Received an invalid real-time message.')
        }
      }
      websocket.onerror = () => {
        if (!active || websocketRef.current !== websocket) return
        needsHistorySync = true
        setRealtimeStatus('reconnecting')
        setWebsocketError('Real-time updates were interrupted. Reconnecting automatically.')
        websocket.close()
      }
      websocket.onclose = () => {
        if (stableConnectionTimer !== undefined) {
          window.clearTimeout(stableConnectionTimer)
          stableConnectionTimer = undefined
        }
        if (websocketRef.current === websocket) websocketRef.current = null
        if (!active) return
        needsHistorySync = true
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
      setRealtimeStatus('connecting')
      connectWebSocket()
    }

    async function loadMessages () {
      try {
        await apiRequest(`/api/chats/${encodeURIComponent(chatUri)}/join/`, {
          method: 'POST',
          headers: { Authorization: `Token ${authToken}` },
          signal: controller.signal
        })
        const messages = parseChatMessages(await apiRequest(
          `/api/chats/${encodeURIComponent(chatUri)}/messages/`,
          { headers: { Authorization: `Token ${authToken}` }, signal: controller.signal }
        ))

        if (!active) return
        setMessages(messages)
        connectWebSocket()
      } catch (error: unknown) {
        if (active && !controller.signal.aborted) {
          setRealtimeStatus('unavailable')
          setErrorMessage(getErrorMessage(error))
        }
      } finally {
        if (active) setLoading(false)
      }
    }

    loadMessages()

    return () => {
      active = false
      controller.abort()
      if (reconnectTimer !== undefined) window.clearTimeout(reconnectTimer)
      if (stableConnectionTimer !== undefined) window.clearTimeout(stableConnectionTimer)
      reconnectRef.current = null
      if (websocketRef.current) {
        websocketRef.current.close()
        websocketRef.current = null
      }
    }
  }, [uri])

  function addMessage (message: ChatMessageData) {
    setMessages(current => (
      current.some(existing => existing.id === message.id)
        ? current
        : [...current, message]
    ))
  }

  async function startChatSession () {
    if (creatingConversation) return
    const token = window.sessionStorage.getItem('authToken')
    if (!token) {
      navigate('/auth')
      return
    }

    setCreatingConversation(true)
    setErrorMessage('')
    try {
      const uri = parseChatUri(await apiRequest('/api/chats/', {
        method: 'POST',
        headers: {
          Authorization: `Token ${token}`,
          'Content-Type': 'application/json'
        }
      }))
      navigate(`/chats/${encodeURIComponent(uri)}`)
    } catch (error: unknown) {
      setErrorMessage(`Unable to start a conversation: ${getErrorMessage(error)}`)
    } finally {
      setCreatingConversation(false)
    }
  }

  async function sendMessage (event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const token = window.sessionStorage.getItem('authToken')
    const message = messageDraft.trim()

    if (!token || !uri || !message || sendingMessage) return

    setSendingMessage(true)
    setErrorMessage('')

    try {
      const result = parseChatMessage(await apiRequest(
        `/api/chats/${encodeURIComponent(uri)}/messages/`,
        {
          method: 'POST',
          headers: {
            Authorization: `Token ${token}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ message })
        }
      ))
      addMessage(result)
      setMessageDraft('')
    } catch (error: unknown) {
      setErrorMessage(getErrorMessage(error))
    } finally {
      setSendingMessage(false)
    }
  }

  return (
    <AppShell
      conversationUri={uri}
      username={username}
      creatingConversation={creatingConversation}
      onNewConversation={startChatSession}
    >
      {uri
        ? (
          <section className="conversation-view" aria-label="Chat conversation">
            <header className="conversation-header">
              <div>
                <div className="eyebrow"><span>01</span> OPEN CONVERSATION</div>
                <h1>Conversation</h1>
              </div>
              <div className="conversation-context">
                <div className="invite-note">
                  <span className="accent-dot" aria-hidden="true" />
                  Anyone with this URL can join
                </div>
                <div className={`realtime-status realtime-status-${realtimeStatus}`} role="status">
                  <span className="realtime-indicator" aria-hidden="true" />
                  {realtimeStatus === 'connected'
                    ? 'LIVE'
                    : realtimeStatus === 'reconnecting'
                      ? 'RECONNECTING'
                      : realtimeStatus === 'offline'
                        ? 'OFFLINE'
                        : realtimeStatus === 'unavailable' ? 'UNAVAILABLE' : 'CONNECTING'}
                </div>
                {realtimeStatus === 'offline' && (
                  <button
                    className="button button-secondary retry-button"
                    type="button"
                    onClick={() => reconnectRef.current?.()}
                  >
                    Retry connection
                  </button>
                )}
              </div>
            </header>

            <div className="conversation-panel">
              <div
                className="message-history"
                role="log"
                aria-label="Conversation messages"
                aria-live="polite"
                aria-relevant="additions text"
              >
                {errorMessage && <p className="notice notice-error" role="alert">{errorMessage}</p>}
                {websocketError && <p className="notice notice-warning" role="alert">{websocketError}</p>}
                {loading && messages.length === 0 && (
                  <p className="conversation-state" role="status">Loading conversation…</p>
                )}
                {!loading && messages.length === 0 && !errorMessage && (
                  <div className="conversation-empty">
                    <span className="empty-index">01 / FIRST MESSAGE</span>
                    <h2>Start with what&apos;s on your mind.</h2>
                    <p>A question, a thought, or something you&apos;re working through.</p>
                  </div>
                )}
                {messages.map(message => (
                  <ChatMessage
                    key={message.id}
                    message={message}
                    isOwnMessage={message.user.username === username}
                  />
                ))}
              </div>

              <MessageComposer
                value={messageDraft}
                sending={sendingMessage}
                onChange={setMessageDraft}
                onSubmit={sendMessage}
              />
              <p className="composer-note">Keep it thoughtful. Keep it human.</p>
            </div>
          </section>
        )
        : (
          <section className="home-view">
            <div className="home-intro">
              <p className="eyebrow"><span>F / 01</span> A PLACE TO THINK OUT LOUD</p>
              <h1>Bring the question<br /><span>you can&apos;t shake.</span></h1>
              <p className="home-description">
                Start a conversation, invite someone in, and work through an idea together.
              </p>
              {errorMessage && <p className="notice notice-error" role="alert">{errorMessage}</p>}
              <button
                className="button button-primary start-button"
                onClick={startChatSession}
                type="button"
                disabled={creatingConversation}
              >
                {creatingConversation ? 'Starting…' : 'Start a conversation'}
                <span className="send-arrow" aria-hidden="true">↑</span>
              </button>
            </div>

            <div className="home-footer" aria-label="A good place to begin">
              <span>ASK</span>
              <span className="footer-divider" aria-hidden="true" />
              <span>DISCUSS</span>
              <span className="footer-divider" aria-hidden="true" />
              <span>MAKE SENSE</span>
              <span className="footer-index">FUEGO / CHAT</span>
            </div>
          </section>
        )}
    </AppShell>
  )
}
