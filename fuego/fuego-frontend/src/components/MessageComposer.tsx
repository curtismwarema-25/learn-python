import type { FormEvent } from 'react'

interface MessageComposerProps {
  value: string
  sending: boolean
  onChange: (value: string) => void
  onSubmit: (event: FormEvent<HTMLFormElement>) => void
}

export default function MessageComposer ({
  value,
  sending,
  onChange,
  onSubmit
}: MessageComposerProps) {
  return (
    <form className="message-composer" onSubmit={onSubmit}>
      <label className="visually-hidden" htmlFor="message-draft">Write a message</label>
      <input
        id="message-draft"
        className="message-input"
        type="text"
        maxLength={2000}
        placeholder="Write a message…"
        value={value}
        onChange={event => onChange(event.target.value)}
        autoComplete="off"
        required
      />
      <button
        className="button button-primary send-button"
        type="submit"
        disabled={sending || !value.trim()}
      >
        {sending ? 'Sending…' : 'Send'}
        <span className="send-arrow" aria-hidden="true">↑</span>
      </button>
    </form>
  )
}
