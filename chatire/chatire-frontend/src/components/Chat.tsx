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
import type { ChatMessage } from '../api'

export default function Chat () {
  const { uri } = useParams()
  const navigate = useNavigate()
  const [username] = useState(() => window.sessionStorage.getItem('username'))
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [messageDraft, setMessageDraft] = useState('')
  const [loading, setLoading] = useState(false)
  const [sendingMessage, setSendingMessage] = useState(false)
  const [errorMessage, setErrorMessage] = useState('')
  const [websocketError, setWebsocketError] = useState('')
  const websocketRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    setMessages([])
    setErrorMessage('')
    setWebsocketError('')

    if (!uri) {
      setLoading(false)
      return undefined
    }
    const chatUri = uri

    const token = window.sessionStorage.getItem('authToken')
    if (!token) {
      setLoading(false)
      setErrorMessage('Your session has expired. Please sign in again.')
      return undefined
    }
    const authToken = token

    const controller = new AbortController()
    let active = true
    setLoading(true)

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

        const apiUrl = new URL(API_BASE_URL)
        const protocol = apiUrl.protocol === 'https:' ? 'wss:' : 'ws:'
        const socketUrl = `${protocol}//${apiUrl.host}/ws/chats/${encodeURIComponent(chatUri)}/?token=${encodeURIComponent(authToken)}`
        const websocket = new WebSocket(socketUrl)
        websocketRef.current = websocket

        websocket.onopen = () => {
          if (active) setWebsocketError('')
        }
        websocket.onmessage = event => {
          if (!active) return
          try {
            const payload: unknown = JSON.parse(event.data)
            addMessage(parseChatMessage(payload))
          } catch (error) {
            console.error('Could not parse chat WebSocket message:', error)
            setWebsocketError('Received an invalid real-time message.')
          }
        }
        websocket.onerror = () => {
          if (active) setWebsocketError('Real-time updates are unavailable.')
        }
        websocket.onclose = () => {
          if (websocketRef.current === websocket) websocketRef.current = null
        }
      } catch (error: unknown) {
        if (active && !controller.signal.aborted) setErrorMessage(getErrorMessage(error))
      } finally {
        if (active) setLoading(false)
      }
    }

    loadMessages()

    return () => {
      active = false
      controller.abort()
      if (websocketRef.current) {
        websocketRef.current.close()
        websocketRef.current = null
      }
    }
  }, [uri])

  function addMessage (message: ChatMessage) {
    setMessages(current => (
      current.some(existing => existing.id === message.id)
        ? current
        : [...current, message]
    ))
  }

  async function startChatSession () {
    const token = window.sessionStorage.getItem('authToken')
    if (!token) {
      navigate('/auth')
      return
    }

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
      setErrorMessage(`Unable to start a chat session: ${getErrorMessage(error)}`)
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
    <section className="container">
      {uri
        ? (
          <div id="chat-container" className="card">
            <div className="card-header text-white text-center font-weight-bold subtle-blue-gradient">
              Share the page URL to invite new friends
            </div>

            <div className="card-body">
              <div className="container chat-body" aria-live="polite">
                {errorMessage && <p className="alert alert-danger">{errorMessage}</p>}
                {websocketError && <p className="alert alert-warning">{websocketError}</p>}
                {loading && messages.length === 0 && (
                  <p className="text-center">Loading messages...</p>
                )}

                {messages.map((message, index) => {
                  const isOwnMessage = message.user?.username === username
                  return (
                    <div className="row chat-section" key={message.id ?? index}>
                      {isOwnMessage
                        ? (
                          <>
                            <div className="col-sm-7 offset-3">
                              <p className="card-text speech-bubble speech-bubble-user float-right text-white subtle-blue-gradient">
                                {message.message}
                              </p>
                            </div>
                            <div className="col-sm-2">
                              <span className="rounded-circle avatar avatar-user" aria-hidden="true">A</span>
                            </div>
                          </>
                        )
                        : (
                          <>
                            <div className="col-sm-2">
                              <span className="rounded-circle avatar avatar-peer" aria-hidden="true">D</span>
                            </div>
                            <div className="col-sm-7">
                              <p className="card-text speech-bubble speech-bubble-peer">
                                {message.message}
                              </p>
                            </div>
                          </>
                        )}
                    </div>
                  )
                })}
              </div>
            </div>

            <div className="card-footer text-muted">
              <form onSubmit={sendMessage}>
                <div className="row">
                  <div className="col-sm-10">
                    <input
                      className="message-input"
                      type="text"
                      placeholder="Type a message"
                      value={messageDraft}
                      onChange={event => setMessageDraft(event.target.value)}
                      required
                    />
                  </div>
                  <div className="col-sm-2">
                    <button className="btn btn-primary" type="submit" disabled={sendingMessage}>
                      Send
                    </button>
                  </div>
                </div>
              </form>
            </div>
          </div>
        )
        : (
          <div className="chat-welcome">
            <h3 className="text-center">Welcome!</h3>
            <p className="text-center">
              Start a chat session and share its URL with friends to invite them.
            </p>
            {errorMessage && <p className="alert alert-danger">{errorMessage}</p>}
            <button onClick={startChatSession} className="btn btn-primary btn-lg btn-block">
              Start Chatting
            </button>
          </div>
        )}
    </section>
  )
}
