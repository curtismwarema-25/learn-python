import type { ChatMessage as ChatMessageData } from '../api'

interface ChatMessageProps {
  message: ChatMessageData
  isOwnMessage: boolean
}

export default function ChatMessage ({ message, isOwnMessage }: ChatMessageProps) {
  return (
    <article className={`message ${isOwnMessage ? 'message-own' : 'message-peer'}`}>
      <div className="message-author">
        {isOwnMessage ? 'YOU' : message.user.username}
      </div>
      <p className="message-text">{message.message}</p>
    </article>
  )
}
