import { useState } from 'react'
import type { FormEvent } from 'react'
import { Link } from 'react-router-dom'
import type { ChatMessage as ChatMessageData } from '../api'
import type { SpaceKnowledgeHistory } from '../api'

interface ChatMessageProps {
  message: ChatMessageData
  isOwnMessage: boolean
  spaceId?: string
  onToggleKnowledge?: () => void
  knowledgeBusy?: boolean
  knowledgeHistory?: SpaceKnowledgeHistory
  knowledgeHistoryLoading?: boolean
  onViewKnowledgeHistory?: () => void
  onSubmitKnowledgeCorrection?: (content: string, explanation: string) => void
  onEditMessage?: (content: string) => void
  onDeleteMessage?: () => void
  onReportMessage?: (reason: string) => void
  messageBusy?: boolean
}

export default function ChatMessage ({
  message,
  isOwnMessage,
  spaceId,
  onToggleKnowledge,
  knowledgeBusy = false,
  knowledgeHistory,
  knowledgeHistoryLoading = false,
  onViewKnowledgeHistory,
  onSubmitKnowledgeCorrection,
  onEditMessage,
  onDeleteMessage,
  onReportMessage,
  messageBusy = false
}: ChatMessageProps) {
  const [correctionOpen, setCorrectionOpen] = useState(false)
  const [correctionContent, setCorrectionContent] = useState('')
  const [correctionExplanation, setCorrectionExplanation] = useState('')
  const [editing, setEditing] = useState(false)
  const [editContent, setEditContent] = useState(message.message)
  const [reporting, setReporting] = useState(false)
  const [reportReason, setReportReason] = useState('')

  function submitCorrection (event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!correctionContent.trim() || !onSubmitKnowledgeCorrection) return
    onSubmitKnowledgeCorrection(correctionContent.trim(), correctionExplanation.trim())
    setCorrectionOpen(false)
  }

  function submitEdit (event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const content = editContent.trim()
    if (!content || !onEditMessage) return
    onEditMessage(content)
    setEditing(false)
  }

  return (
    <article
      id={spaceId ? `message-${message.id}` : undefined}
      className={`message ${isOwnMessage ? 'message-own' : 'message-peer'}`}
    >
      <div className="message-author">
        {isOwnMessage ? 'YOU' : message.user.username}
      </div>
      {editing
        ? (
          <form className="message-edit-form" onSubmit={submitEdit}>
            <label>
              Edit message
              <textarea
                maxLength={2000}
                onChange={event => setEditContent(event.target.value)}
                required
                rows={3}
                value={editContent}
              />
            </label>
            <div className="space-inline-actions">
              <button className="button button-secondary" disabled={messageBusy} type="submit">Save</button>
              <button className="button button-secondary" onClick={() => setEditing(false)} type="button">Cancel</button>
            </div>
          </form>
        )
        : <p className="message-text">{message.message}</p>}
      {(onEditMessage || onDeleteMessage || onReportMessage) && (
        <div className="message-source-actions" aria-label="Message actions">
          {onEditMessage && !editing && (
            <button className="button button-secondary" disabled={messageBusy} onClick={() => {
              setEditContent(message.message)
              setEditing(true)
            }} type="button">Edit</button>
          )}
          {onDeleteMessage && (
            <button className="button button-danger" disabled={messageBusy} onClick={() => {
              if (window.confirm('Delete this message? Preserved knowledge will be marked source-deleted.')) onDeleteMessage()
            }} type="button">Delete</button>
          )}
          {onReportMessage && !reporting && (
            <button className="button button-secondary" disabled={messageBusy} onClick={() => setReporting(true)} type="button">Report</button>
          )}
        </div>
      )}
      {reporting && onReportMessage && (
        <form className="message-report-form" onSubmit={event => {
          event.preventDefault()
          const reason = reportReason.trim()
          if (!reason) return
          onReportMessage(reason)
          setReporting(false)
          setReportReason('')
        }}>
          <label>
            Why are you reporting this message?
            <textarea maxLength={500} onChange={event => setReportReason(event.target.value)} required rows={2} value={reportReason} />
          </label>
          <div className="space-inline-actions">
            <button className="button button-danger" disabled={messageBusy} type="submit">Submit report</button>
            <button className="button button-secondary" onClick={() => setReporting(false)} type="button">Cancel</button>
          </div>
        </form>
      )}
      {spaceId && onToggleKnowledge && (
        <div className="message-knowledge-actions">
          {message.knowledge && (
            <span className="message-knowledge-label">
              {message.knowledge.status === 'active' && 'PRESERVED KNOWLEDGE'}
              {message.knowledge.status === 'needs_review' && 'SOURCE CHANGED · REVIEW'}
              {message.knowledge.status === 'source_deleted' && 'SOURCE DELETED'}
              {message.knowledge.status === 'withdrawn' && 'WITHDRAWN'}
            </span>
          )}
          {(!message.knowledge || message.knowledge.status === 'active') && <button
            className="button button-secondary"
            disabled={knowledgeBusy}
            onClick={onToggleKnowledge}
            type="button"
          >
            {message.knowledge ? 'Withdraw knowledge' : 'Preserve knowledge'}
          </button>}
          {message.knowledge && onViewKnowledgeHistory && (
            <button
              className="button button-secondary"
              disabled={knowledgeHistoryLoading}
              onClick={onViewKnowledgeHistory}
              type="button"
            >
              {knowledgeHistoryLoading ? 'Loading history…' : 'View history'}
            </button>
          )}
        </div>
      )}
      {knowledgeHistory && (
        <section className="message-knowledge-history" aria-label="Knowledge correction history">
          <p className="message-knowledge-history-heading">
            Current version V{knowledgeHistory.currentVersion ?? '—'}
          </p>
          <ol>
            {knowledgeHistory.versions.map(version => (
              <li key={version.id}>
                <strong>V{version.versionNumber}{version.isCurrent ? ' · CURRENT' : ''}</strong>
                <span>{version.content}</span>
                <small>
                  {version.createdByUsername} · {new Date(version.createDate).toLocaleString()}
                </small>
                {version.explanation && <em>{version.explanation}</em>}
              </li>
            ))}
          </ol>
          {onSubmitKnowledgeCorrection && (
            correctionOpen
              ? (
                <form className="knowledge-correction-form" onSubmit={submitCorrection}>
                  <label>
                    Corrected content
                    <textarea
                      maxLength={2000}
                      onChange={event => setCorrectionContent(event.target.value)}
                      required
                      rows={3}
                      value={correctionContent}
                    />
                  </label>
                  <label>
                    Explanation (optional)
                    <input
                      maxLength={500}
                      onChange={event => setCorrectionExplanation(event.target.value)}
                      value={correctionExplanation}
                    />
                  </label>
                  <div className="space-inline-actions">
                    <button className="button button-secondary" type="submit">Submit correction</button>
                    <button
                      className="button button-secondary"
                      onClick={() => setCorrectionOpen(false)}
                      type="button"
                    >
                      Cancel
                    </button>
                  </div>
                </form>
              )
              : (
                <button
                  className="button button-secondary"
                  onClick={() => setCorrectionOpen(true)}
                  type="button"
                >
                  Submit correction
                </button>
              )
          )}
        </section>
      )}
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
