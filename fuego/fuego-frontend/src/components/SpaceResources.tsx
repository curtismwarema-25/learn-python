import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import {
  apiRequest,
  getErrorMessage,
  parseSpaceDetail,
  parseSpaceResource,
  parseSpaceResources
} from '../api'
import type { SpaceDetail, SpaceResource } from '../api'
import AppShell from './AppShell'

function authHeaders (token: string) {
  return { Authorization: `Token ${token}` }
}

function resourcePath (spaceId: string, resourceId?: string) {
  const base = `/spaces/${encodeURIComponent(spaceId)}/resources`
  return resourceId
    ? `${base}/${encodeURIComponent(resourceId)}`
    : base
}

function resourceApiPath (spaceId: string, resourceId?: string) {
  const base = `/api/spaces/${encodeURIComponent(spaceId)}/resources/`
  return resourceId
    ? `${base}${encodeURIComponent(resourceId)}/`
    : base
}

function ResourceForm ({
  initial,
  submitLabel,
  busy,
  onCancel,
  onSubmit
}: {
  initial?: SpaceResource
  submitLabel: string
  busy: boolean
  onCancel?: () => void
  onSubmit: (event: FormEvent<HTMLFormElement>) => void
}) {
  return (
    <form className="space-form resource-form" onSubmit={onSubmit}>
      <label>
        Title
        <input
          name="title"
          defaultValue={initial?.title ?? ''}
          maxLength={160}
          required
        />
      </label>
      <label>
        External URL
        <input
          name="url"
          defaultValue={initial?.url ?? ''}
          type="url"
          maxLength={2048}
          placeholder="https://example.com/guide"
          required
        />
      </label>
      <label>
        Description
        <textarea
          name="description"
          defaultValue={initial?.description ?? ''}
          maxLength={2000}
          rows={3}
        />
      </label>
      <p className="resource-form-note">
        Fuego stores this link and does not fetch previews from the external site.
      </p>
      <div className="space-inline-actions">
        <button className="button button-primary" disabled={busy} type="submit">
          {busy ? 'Saving…' : submitLabel}
        </button>
        {onCancel && (
          <button
            className="button button-secondary"
            disabled={busy}
            onClick={onCancel}
            type="button"
          >
            Cancel
          </button>
        )}
      </div>
    </form>
  )
}

export default function SpaceResources () {
  const { spaceId, resourceId } = useParams()
  const navigate = useNavigate()
  const token = window.sessionStorage.getItem('authToken')
  const [space, setSpace] = useState<SpaceDetail | null>(null)
  const [resources, setResources] = useState<SpaceResource[]>([])
  const [resource, setResource] = useState<SpaceResource | null>(null)
  const [searchText, setSearchText] = useState('')
  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState<'active' | 'archived'>('active')
  const [creating, setCreating] = useState(false)
  const [editing, setEditing] = useState(false)
  const [loading, setLoading] = useState(true)
  const [pageError, setPageError] = useState('')
  const [actionError, setActionError] = useState('')
  const [notice, setNotice] = useState('')
  const [busy, setBusy] = useState(false)
  const [refreshKey, setRefreshKey] = useState(0)

  useEffect(() => {
    if (!spaceId || !token) {
      setPageError('Sign in as an active Space member to view resources.')
      setLoading(false)
      return undefined
    }

    const id = spaceId
    const controller = new AbortController()
    let active = true
    setLoading(true)
    setPageError('')
    const query = new URLSearchParams({ status: statusFilter })
    if (searchQuery) query.set('q', searchQuery)
    const headers = authHeaders(token)

    async function loadResources () {
      try {
        const [spaceResult, resourcesResult, selectedResult] = await Promise.all([
          apiRequest(`/api/spaces/${encodeURIComponent(id)}/`, {
            headers,
            signal: controller.signal
          }),
          apiRequest(
            `${resourceApiPath(id)}?${query.toString()}`,
            { headers, signal: controller.signal }
          ),
          resourceId
            ? apiRequest(resourceApiPath(id, resourceId), {
                headers,
                signal: controller.signal
              })
            : Promise.resolve(null)
        ])
        if (!active) return
        setSpace(parseSpaceDetail(spaceResult))
        setResources(parseSpaceResources(resourcesResult))
        setResource(selectedResult === null ? null : parseSpaceResource(selectedResult))
      } catch (error: unknown) {
        if (active && !controller.signal.aborted) {
          setPageError(getErrorMessage(error))
        }
      } finally {
        if (active) setLoading(false)
      }
    }

    void loadResources()
    return () => {
      active = false
      controller.abort()
    }
  }, [spaceId, resourceId, token, searchQuery, statusFilter, refreshKey])

  async function createResource (event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!spaceId || !token || busy) return
    const form = new FormData(event.currentTarget)
    setBusy(true)
    setActionError('')
    setNotice('')
    try {
      const created = parseSpaceResource(await apiRequest(
        resourceApiPath(spaceId),
        {
          method: 'POST',
          headers: {
            ...authHeaders(token),
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            title: form.get('title'),
            url: form.get('url'),
            description: form.get('description')
          })
        }
      ))
      setCreating(false)
      setNotice('Link added to this Space.')
      navigate(resourcePath(spaceId, created.id))
      setRefreshKey(value => value + 1)
    } catch (error: unknown) {
      setActionError(`Link could not be added: ${getErrorMessage(error)}`)
    } finally {
      setBusy(false)
    }
  }

  async function updateResource (event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!spaceId || !resourceId || !token || !resource || busy) return
    const form = new FormData(event.currentTarget)
    const body: Record<string, string> = {}
    if (editing) {
      body.title = String(form.get('title') ?? '')
      body.url = String(form.get('url') ?? '')
      body.description = String(form.get('description') ?? '')
    }
    setBusy(true)
    setActionError('')
    setNotice('')
    try {
      await apiRequest(resourceApiPath(spaceId, resourceId), {
        method: 'PATCH',
        headers: {
          ...authHeaders(token),
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(body)
      })
      setEditing(false)
      setNotice('Resource details saved.')
      setRefreshKey(value => value + 1)
    } catch (error: unknown) {
      setActionError(`Resource could not be updated: ${getErrorMessage(error)}`)
    } finally {
      setBusy(false)
    }
  }

  async function changeResourceStatus (status: 'active' | 'archived') {
    if (!spaceId || !resourceId || !token || !resource || busy) return
    setBusy(true)
    setActionError('')
    setNotice('')
    try {
      await apiRequest(resourceApiPath(spaceId, resourceId), {
        method: 'PATCH',
        headers: {
          ...authHeaders(token),
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ status })
      })
      setNotice(status === 'archived' ? 'Resource archived.' : 'Resource restored.')
      setRefreshKey(value => value + 1)
    } catch (error: unknown) {
      setActionError(`Resource could not be updated: ${getErrorMessage(error)}`)
    } finally {
      setBusy(false)
    }
  }

  async function deleteResource () {
    if (!spaceId || !resourceId || !token || !resource || busy) return
    if (!window.confirm(
      'Remove this resource? Its link and descriptive content will be erased. Existing channel references will remain as “Resource removed.”'
    )) return
    setBusy(true)
    setActionError('')
    setNotice('')
    try {
      await apiRequest(resourceApiPath(spaceId, resourceId), {
        method: 'DELETE',
        headers: authHeaders(token)
      })
      setNotice('Resource removed; existing channel references are preserved.')
      navigate(resourcePath(spaceId))
      setRefreshKey(value => value + 1)
    } catch (error: unknown) {
      setActionError(`Resource could not be removed: ${getErrorMessage(error)}`)
    } finally {
      setBusy(false)
    }
  }

  function searchResources (event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSearchQuery(searchText.trim())
  }

  const pageTitle = resource
    ? resource.status === 'deleted' ? 'Resource removed' : resource.title
    : 'Resources'

  return (
    <AppShell username={window.sessionStorage.getItem('username')} conversationUri={undefined}>
      <main className="space-page space-resources-page">
        <p className="space-breadcrumb">
          <Link to="/spaces">Spaces</Link>
          {space && (
            <>
              {' / '}
              <Link to={`/spaces/${encodeURIComponent(space.id)}`}>{space.name}</Link>
              {' / Resources'}
            </>
          )}
        </p>
        {loading && <p role="status">Loading resources…</p>}
        {pageError && (
          <div className="space-failure">
            <h1>Resources unavailable</h1>
            <p className="space-error" role="alert">{pageError}</p>
            <Link className="text-link" to="/spaces">Browse Spaces</Link>
          </div>
        )}
        {!loading && !pageError && space && spaceId && (
          <>
            <header className="space-detail-header">
              <p className="eyebrow"><span aria-hidden="true" /> SPACE KNOWLEDGE</p>
              <div className="space-detail-title">
                <div>
                  <h1>{pageTitle}</h1>
                  <p className="space-purpose">{space.name}</p>
                </div>
                <Link
                  className="button button-secondary"
                  to={`/spaces/${encodeURIComponent(spaceId)}`}
                >
                  Space overview
                </Link>
              </div>
            </header>

            {resource
              ? (
                <section className="space-section resource-detail" aria-labelledby="resource-detail-heading">
                  {resource.status === 'deleted'
                    ? (
                      <>
                        <p className="section-index">REMOVED</p>
                        <h2 id="resource-detail-heading">Resource removed</h2>
                        <p className="space-empty">
                          The link and its descriptive content were removed. Existing channel references remain.
                        </p>
                      </>
                    )
                    : (
                      <>
                        <div className="space-section-heading">
                          <div>
                            <p className="section-index">
                              {resource.status === 'archived' ? 'ARCHIVED LINK' : 'SPACE LINK'}
                            </p>
                            <h2 id="resource-detail-heading">{resource.title}</h2>
                          </div>
                          {resource.status === 'archived' && (
                            <span className="resource-status">ARCHIVED</span>
                          )}
                        </div>
                        {resource.description && <p className="resource-description">{resource.description}</p>}
                        {resource.url && (
                          <p className="resource-source">
                            <span>{resource.sourceDomain}</span>
                            <a href={resource.url} rel="noopener noreferrer" target="_blank">
                              Open external link
                            </a>
                          </p>
                        )}
                        <p className="resource-byline">
                          Added by {resource.creatorUsername ?? 'a former member'} ·{' '}
                          {new Date(resource.createDate).toLocaleDateString()}
                        </p>

                        {editing && (
                          <ResourceForm
                            initial={resource}
                            submitLabel="Save changes"
                            busy={busy}
                            onCancel={() => setEditing(false)}
                            onSubmit={event => { void updateResource(event) }}
                          />
                        )}
                        {!editing && (
                          <div className="space-inline-actions resource-actions">
                            {resource.canEdit && (
                              <button
                                className="button button-secondary"
                                disabled={busy}
                                onClick={() => setEditing(true)}
                                type="button"
                              >
                                Edit details
                              </button>
                            )}
                            {resource.canArchive && (
                              <button
                                className="button button-secondary"
                                disabled={busy}
                                onClick={() => { void changeResourceStatus('archived') }}
                                type="button"
                              >
                                Archive
                              </button>
                            )}
                            {resource.canRestore && (
                              <button
                                className="button button-secondary"
                                disabled={busy}
                                onClick={() => { void changeResourceStatus('active') }}
                                type="button"
                              >
                                Restore
                              </button>
                            )}
                            {resource.canDelete && (
                              <button
                                className="button button-danger"
                                disabled={busy}
                                onClick={() => { void deleteResource() }}
                                type="button"
                              >
                                Remove resource
                              </button>
                            )}
                          </div>
                        )}
                      </>
                    )}
                </section>
              )
              : (
                <section className="space-section resource-library" aria-labelledby="resource-library-heading">
                  <div className="space-section-heading">
                    <div>
                      <p className="section-index">PRESERVED KNOWLEDGE</p>
                      <h2 id="resource-library-heading">Resource library</h2>
                    </div>
                    <button
                      className="button button-primary"
                      onClick={() => setCreating(value => !value)}
                      type="button"
                    >
                      {creating ? 'Close form' : 'Add a link'}
                    </button>
                  </div>
                  <p className="resource-library-intro">
                    Useful links stay in this Space, separate from the conversations that introduced them.
                  </p>
                  {creating && (
                    <ResourceForm
                      submitLabel="Add link"
                      busy={busy}
                      onCancel={() => setCreating(false)}
                      onSubmit={event => { void createResource(event) }}
                    />
                  )}
                  <form className="resource-search" onSubmit={searchResources}>
                    <label htmlFor="resource-search">Search titles, descriptions, and URLs</label>
                    <div>
                      <input
                        id="resource-search"
                        onChange={event => setSearchText(event.target.value)}
                        value={searchText}
                      />
                      <select
                        aria-label="Resource status"
                        onChange={event => setStatusFilter(event.target.value as 'active' | 'archived')}
                        value={statusFilter}
                      >
                        <option value="active">Active resources</option>
                        <option value="archived">Archived resources</option>
                      </select>
                      <button className="button button-secondary" type="submit">Search</button>
                    </div>
                  </form>
                  {resources.length === 0
                    ? (
                      <p className="space-empty" role="status">
                        {searchQuery
                          ? 'No resources match this search.'
                          : statusFilter === 'archived'
                            ? 'There are no archived resources available to you.'
                            : 'No links have been shared yet. Add one to preserve a useful reference.'}
                      </p>
                    )
                    : (
                      <ul className="resource-list">
                        {resources.map(item => (
                          <li className="resource-list-item" key={item.id}>
                            <Link to={resourcePath(spaceId, item.id)}>
                              <span className="resource-list-title">{item.title}</span>
                              {item.description && (
                                <span className="resource-list-description">{item.description}</span>
                              )}
                              <span className="resource-list-meta">
                                <span>{item.sourceDomain ?? 'External link'}</span>
                                <span>{item.creatorUsername ?? 'Former member'}</span>
                                <time dateTime={item.createDate}>
                                  {new Date(item.createDate).toLocaleDateString()}
                                </time>
                                {item.status === 'archived' && <span className="resource-status">ARCHIVED</span>}
                              </span>
                            </Link>
                          </li>
                        ))}
                      </ul>
                    )}
                </section>
              )}
            {actionError && <p className="space-error" role="alert">{actionError}</p>}
            {notice && <p className="space-notice" role="status">{notice}</p>}
          </>
        )}
      </main>
    </AppShell>
  )
}
