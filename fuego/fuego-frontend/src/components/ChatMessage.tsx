import { Link } from 'react-router-dom'
import type { ChatMessage as ChatMessageData } from '../api'

interface ChatMessageProps {
  message: ChatMessageData
  isOwnMessage: boolean
  spaceId?: string
}

export default function ChatMessage ({
  message,
  isOwnMessage,
  spaceId
}: ChatMessageProps) {
  return (
    <article
      id={spaceId ? `message-${message.id}` : undefined}
      className={`message ${isOwnMessage ? 'message-own' : 'message-peer'}`}
    >
      <div className="message-author">
        {isOwnMessage ? 'YOU' : message.user.username}
      </div>
      <p className="message-text">{message.message}</p>
      {spaceId && message.resources && message.resources.length > 0 && (
        <ul className="message-resource-references" aria-label="Referenced resources">
          {message.resources.map(resource => (
            <li key={resource.id}>
              <Link to={`/spaces/${encodeURIComponent(spaceId)}/resources/${encodeURIComponent(resource.id)}`}>
                {resource.title}
              </Link>
              {resource.status === 'archived' && <span> · Archived</span>}
            </li>
          ))}
        </ul>
      )}
    </article>
  )
}
