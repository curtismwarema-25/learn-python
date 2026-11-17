import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom'
import {
  apiRequest,
  getErrorMessage,
  parseSpaceDetail,
  parseSpaceJoinResult,
  parseSpaceMetadataList,
  parseSpaceSummaryList
} from '../api'
import type { SpaceMetadata, SpaceSummary, SpaceVisibility } from '../api'
import AppShell from './AppShell'

function getSessionToken () {
  return window.sessionStorage.getItem('authToken')
}

function getSessionUsername () {
  return window.sessionStorage.getItem('username')
}

function authHeaders (token: string) {
  return { Authorization: `Token ${token}` }
}

function isSpaceVisibility (value: string): value is SpaceVisibility {
  return value === 'private' || value === 'discoverable'
}

export default function Spaces () {
  const navigate = useNavigate()
  const location = useLocation()
  const token = getSessionToken()
  const username = getSessionUsername()
  const [directory, setDirectory] = useState<SpaceMetadata[]>([])
  const [mySpaces, setMySpaces] = useState<SpaceSummary[]>([])
  const [directoryLoading, setDirectoryLoading] = useState(true)
  const [mySpacesLoading, setMySpacesLoading] = useState(Boolean(token))
  const [directoryError, setDirectoryError] = useState('')
  const [mySpacesError, setMySpacesError] = useState('')
  const [createError, setCreateError] = useState('')
  const [creating, setCreating] = useState(false)
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [purpose, setPurpose] = useState('')
  const [visibility, setVisibility] = useState<SpaceVisibility>('private')

  useEffect(() => {
    const controller = new AbortController()
    let active = true

    async function loadDirectory () {
      try {
        const spaces = parseSpaceMetadataList(await apiRequest(
          '/api/spaces/',
          { signal: controller.signal }
        ))
        if (active) setDirectory(spaces)
      } catch (error: unknown) {
        if (active && !controller.signal.aborted) {
          setDirectoryError(getErrorMessage(error))
        }
      } finally {
        if (active) setDirectoryLoading(false)
      }
    }

    async function loadMySpaces () {
      if (!token) {
        setMySpacesLoading(false)
        return
      }
      try {
        const spaces = parseSpaceSummaryList(await apiRequest(
          '/api/spaces/mine/',
          {
            headers: authHeaders(token),
            signal: controller.signal
          }
        ))
        if (active) setMySpaces(spaces)
      } catch (error: unknown) {
        if (active && !controller.signal.aborted) {
          setMySpacesError(getErrorMessage(error))
        }
      } finally {
        if (active) setMySpacesLoading(false)
      }
    }

    void loadDirectory()
    void loadMySpaces()

    return () => {
      active = false
      controller.abort()
    }
  }, [token])

  async function createSpace (event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!token || creating) {
      if (!token) navigate('/auth', { state: { from: location } })
      return
    }

    setCreating(true)
    setCreateError('')
    try {
      const space = parseSpaceDetail(await apiRequest('/api/spaces/', {
        method: 'POST',
        headers: {
          ...authHeaders(token),
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ name, description, purpose, visibility })
      }))
      navigate(`/spaces/${encodeURIComponent(space.id)}`)
    } catch (error: unknown) {
      setCreateError(`Space could not be created: ${getErrorMessage(error)}`)
    } finally {
      setCreating(false)
    }
  }

  return (
    <AppShell username={username} conversationUri={undefined}>
      <main className="space-page">
        <header className="space-intro">
          <p className="eyebrow"><span aria-hidden="true" /> COMMUNITY</p>
          <h1>Spaces</h1>
          <p className="space-lede">
            Gather around a shared interest, goal, project, or learning journey.
          </p>
        </header>

        {token
          ? (
            <section className="space-section" aria-labelledby="my-spaces-heading">
              <div className="space-section-heading">
                <div>
                  <p className="section-index">YOUR COMMUNITIES</p>
                  <h2 id="my-spaces-heading">My Spaces</h2>
                </div>
              </div>
              {mySpacesLoading && <p role="status">Loading your Spaces…</p>}
              {mySpacesError && <p className="space-error" role="alert">{mySpacesError}</p>}
              {!mySpacesLoading && !mySpacesError && mySpaces.length === 0 && (
                <p className="space-empty">You have not joined a Space yet.</p>
              )}
              {mySpaces.length > 0 && (
                <ul className="space-list">
                  {mySpaces.map(space => (
                    <li className="space-list-item" key={space.id}>
                      <Link to={`/spaces/${encodeURIComponent(space.id)}`}>
                        <span className="space-list-title">{space.name}</span>
                        <span className="space-list-summary">{space.purpose}</span>
                        <span className="space-list-meta">
                          {space.role} · {space.visibility}
                        </span>
                      </Link>
                    </li>
                  ))}
                </ul>
              )}

              <form className="space-form" onSubmit={createSpace}>
                <div className="space-form-heading">
                  <p className="section-index">START A COMMUNITY</p>
                  <h2>Create a Space</h2>
                </div>
                <label>
                  Space name
                  <input
                    autoComplete="off"
                    maxLength={80}
                    onChange={event => setName(event.target.value)}
                    required
                    value={name}
                  />
                </label>
                <label>
                  Purpose
                  <input
                    maxLength={160}
                    onChange={event => setPurpose(event.target.value)}
                    required
                    value={purpose}
                  />
                </label>
                <label>
                  Description <span className="space-optional">(optional)</span>
                  <textarea
                    maxLength={280}
                    onChange={event => setDescription(event.target.value)}
                    rows={3}
                    value={description}
                  />
                </label>
                <label>
                  Discovery
                  <select
                    onChange={event => {
                      if (isSpaceVisibility(event.target.value)) {
                        setVisibility(event.target.value)
                      }
                    }}
                    value={visibility}
                  >
                    <option value="private">Private — invitation only</option>
                    <option value="discoverable">
                      Discoverable — public details, approval to join
                    </option>
                  </select>
                </label>
                {createError && <p className="space-error" role="alert">{createError}</p>}
                <button className="button button-primary" disabled={creating} type="submit">
                  {creating ? 'Creating…' : 'Create Space'}
                </button>
              </form>
            </section>
          )
          : (
            <p className="space-sign-in">
              <Link to="/auth" state={{ from: location }}>Sign in</Link> to create a Space
              or request access.
            </p>
          )}

        <section className="space-section" aria-labelledby="discover-spaces-heading">
          <div className="space-section-heading">
            <div>
              <p className="section-index">OPEN FOR DISCOVERY</p>
              <h2 id="discover-spaces-heading">Discover Spaces</h2>
            </div>
          </div>
          {directoryLoading && <p role="status">Loading discoverable Spaces…</p>}
          {directoryError && <p className="space-error" role="alert">{directoryError}</p>}
          {!directoryLoading && !directoryError && directory.length === 0 && (
            <p className="space-empty">No discoverable Spaces are available right now.</p>
          )}
          {directory.length > 0 && (
            <ul className="space-list">
              {directory.map(space => (
                <li className="space-list-item" key={space.id}>
                  <Link to={`/spaces/${encodeURIComponent(space.id)}`}>
                    <span className="space-list-title">{space.name}</span>
                    <span className="space-list-summary">{space.purpose}</span>
                    {space.description && (
                      <span className="space-list-description">{space.description}</span>
                    )}
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </section>
      </main>
    </AppShell>
  )
}

export function SpaceInviteJoin () {
  const { inviteToken } = useParams()
  const navigate = useNavigate()
  const username = getSessionUsername()
  const [message, setMessage] = useState('Joining Space…')
  const [error, setError] = useState('')

  useEffect(() => {
    const token = getSessionToken()
    if (!inviteToken || !token) {
      setError('Sign in before joining an invited Space.')
      return undefined
    }

    const authToken = token
    const controller = new AbortController()
    let active = true

    async function joinSpace () {
      try {
        const result = parseSpaceJoinResult(await apiRequest(
          '/api/spaces/invites/join/',
          {
            method: 'POST',
            headers: {
              ...authHeaders(authToken),
              'Content-Type': 'application/json'
            },
            body: JSON.stringify({ token: inviteToken }),
            referrerPolicy: 'no-referrer',
            signal: controller.signal
          }
        ))
        if (active) {
          navigate(`/spaces/${encodeURIComponent(result.spaceId)}`, { replace: true })
        }
      } catch (requestError: unknown) {
        if (active && !controller.signal.aborted) {
          setError(getErrorMessage(requestError))
          setMessage('')
        }
      }
    }

    void joinSpace()
    return () => {
      active = false
      controller.abort()
    }
  }, [inviteToken, navigate])

  return (
    <AppShell username={username} conversationUri={undefined}>
      <main className="space-page space-join-page">
        {error
          ? (
            <div>
              <p className="section-index">INVITATION</p>
              <h1>Could not join this Space</h1>
              <p className="space-error" role="alert">{error}</p>
              <Link className="text-link" to="/spaces">Browse Spaces</Link>
            </div>
          )
          : <p role="status">{message}</p>}
      </main>
    </AppShell>
  )
}
