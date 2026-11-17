import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'

interface AppShellProps {
  children: ReactNode
  conversationUri: string | undefined
  username: string | null
  creatingConversation: boolean
  onNewConversation: () => void
}

function getInitial (value: string | null) {
  return value?.trim().charAt(0).toUpperCase() || '?'
}

export default function AppShell ({
  children,
  conversationUri,
  username,
  creatingConversation,
  onNewConversation
}: AppShellProps) {
  return (
    <div className="app-shell">
      <aside className="app-sidebar" aria-label="Primary">
        <Link className="brand-lockup" to="/" aria-label="Fuego home">
          <span className="brand-mark" aria-hidden="true">F</span>
          <span className="brand-name">fuego<span>.</span></span>
        </Link>

        <nav className="primary-nav" aria-label="Workspace">
          <Link
            className={`nav-item ${conversationUri ? '' : 'is-active'}`}
            to="/"
            aria-current={conversationUri ? undefined : 'page'}
          >
            <span className="nav-indicator" aria-hidden="true" />
            Home
          </Link>
          {conversationUri && (
            <Link
              className="nav-item is-active"
              to={`/chats/${encodeURIComponent(conversationUri)}`}
              aria-current="page"
            >
              <span className="nav-indicator" aria-hidden="true" />
              Current conversation
            </Link>
          )}
        </nav>

        <button
          className="button button-primary new-conversation-button"
          type="button"
          onClick={onNewConversation}
          disabled={creatingConversation}
        >
          <span className="button-plus" aria-hidden="true">+</span>
          {creatingConversation ? 'Starting…' : 'New conversation'}
        </button>

        <div className="sidebar-bottom">
          <span className="account-avatar" aria-hidden="true">{getInitial(username)}</span>
          <span className="account-name">{username || 'Your account'}</span>
        </div>
      </aside>

      <div className="app-main">
        <header className="app-topbar">
          <span className="topbar-label">
            {conversationUri ? 'CONVERSATION' : 'YOUR SPACE'}
          </span>
          {username && <span className="topbar-user">{username}</span>}
        </header>
        {children}
      </div>
    </div>
  )
}
