import { useEffect, useState } from 'react'
import type { FormEvent, ReactNode } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  apiRequest,
  getErrorMessage,
  parseSpaceChannels,
  parseSpaceDetail,
  parseSpaceSearchResponse
} from '../api'
import type {
  SpaceChannel,
  SpaceDetail,
  SpaceSearchContentType,
  SpaceSearchResult
} from '../api'
import AppShell from './AppShell'

const PAGE_SIZE = 20

function authHeaders (token: string) {
  return { Authorization: `Token ${token}` }
}

function escapeRegExp (value: string) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

function highlightText (text: string, query: string): ReactNode {
  const terms = [...new Set(query.match(/[^\W_]+/gu) ?? [])]
  if (terms.length === 0) return text

  const expression = new RegExp(`(${terms.map(escapeRegExp).join('|')})`, 'gi')
  return text.split(expression).map((part, index) => {
    const isMatch = terms.some(
      term => term.toLocaleLowerCase() === part.toLocaleLowerCase()
    )
    return isMatch
      ? <mark className="space-search-match" key={index}>{part}</mark>
      : part
  })
}

function searchResultPath (spaceId: string, result: SpaceSearchResult) {
  if ((result.type === 'discussion' || result.type === 'knowledge') && result.channel) {
    const messageId = result.sourceMessageId ?? result.id
    return `/spaces/${encodeURIComponent(spaceId)}/channels/${encodeURIComponent(result.channel.id)}#message-${encodeURIComponent(messageId)}`
  }
  return `/spaces/${encodeURIComponent(spaceId)}/resources/${encodeURIComponent(result.id)}`
}

function resultSourceLabel (result: SpaceSearchResult) {
  if (result.type === 'knowledge') {
    const archived = result.channel?.archived ? ' · ARCHIVED' : ''
    const corrected = result.knowledgeCorrected ? ' · CORRECTED' : ''
    const version = result.knowledgeVersion ? ` · V${result.knowledgeVersion}` : ''
    return `KNOWLEDGE · #${result.channel?.name ?? ''}${version}${archived}${corrected}`
  }
  if (result.type === 'discussion') {
    return result.channel?.archived
      ? `DISCUSSION · #${result.channel.name} · ARCHIVED`
      : `DISCUSSION · #${result.channel?.name ?? ''}`
  }
  return result.sourceDomain
    ? `RESOURCE · ${result.sourceDomain}`
    : 'RESOURCE'
}

function formatCreatedAt (value: string) {
  return new Date(value).toLocaleString()
}

export default function SpaceSearch () {
  const { spaceId } = useParams()
  const token = window.sessionStorage.getItem('authToken')
  const [space, setSpace] = useState<SpaceDetail | null>(null)
  const [channels, setChannels] = useState<SpaceChannel[]>([])
  const [contextLoading, setContextLoading] = useState(true)
  const [contextError, setContextError] = useState('')
  const [queryText, setQueryText] = useState('')
  const [submittedQuery, setSubmittedQuery] = useState('')
  const [contentType, setContentType] = useState<SpaceSearchContentType>('all')
  const [channelId, setChannelId] = useState('')
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [page, setPage] = useState(1)
  const [searchRun, setSearchRun] = useState(0)
  const [searchResults, setSearchResults] = useState<ReturnType<typeof parseSpaceSearchResponse> | null>(null)
  const [searchLoading, setSearchLoading] = useState(false)
  const [searchError, setSearchError] = useState('')

  useEffect(() => {
    if (!spaceId || !token) {
      setContextError('Sign in as an active Space member to search this Space.')
      setContextLoading(false)
      return undefined
    }

    const id = spaceId
    const authToken = token
    const controller = new AbortController()
    let active = true
    setContextLoading(true)
    setContextError('')

    async function loadSearchContext () {
      try {
        const detail = parseSpaceDetail(await apiRequest(
          `/api/spaces/${encodeURIComponent(id)}/`,
          { headers: authHeaders(authToken), signal: controller.signal }
        ))
        if (!detail.role) {
          throw new Error('Search is available to active Space members only.')
        }
        const availableChannels = parseSpaceChannels(await apiRequest(
          `/api/spaces/${encodeURIComponent(id)}/channels/`,
          { headers: authHeaders(authToken), signal: controller.signal }
        ))
        if (active) {
          setSpace(detail)
          setChannels(availableChannels)
        }
      } catch (error: unknown) {
        if (active && !controller.signal.aborted) {
          setContextError(getErrorMessage(error))
        }
      } finally {
        if (active) setContextLoading(false)
      }
    }

    void loadSearchContext()
    return () => {
      active = false
      controller.abort()
    }
  }, [spaceId, token])

  useEffect(() => {
    if (!submittedQuery || !spaceId || !token || !space) {
      setSearchLoading(false)
      return undefined
    }
    if (startDate && endDate && startDate > endDate) {
      setSearchResults(null)
      setSearchError('End date must not be before the start date.')
      setSearchLoading(false)
      return undefined
    }

    const id = spaceId
    const authToken = token
    const controller = new AbortController()
    let active = true
    const params = new URLSearchParams({
      q: submittedQuery,
      content_type: contentType,
      page: String(page),
      page_size: String(PAGE_SIZE)
    })
    if (channelId) params.set('channel_id', channelId)
    if (startDate) params.set('start_date', startDate)
    if (endDate) params.set('end_date', endDate)

    setSearchLoading(true)
    setSearchError('')
    setSearchResults(null)

    async function search () {
      try {
        const response = parseSpaceSearchResponse(await apiRequest(
          `/api/spaces/${encodeURIComponent(id)}/search/?${params.toString()}`,
          { headers: authHeaders(authToken), signal: controller.signal }
        ))
        if (active) setSearchResults(response)
      } catch (error: unknown) {
        if (active && !controller.signal.aborted) {
          setSearchError(getErrorMessage(error))
        }
      } finally {
        if (active) setSearchLoading(false)
      }
    }

    void search()
    return () => {
      active = false
      controller.abort()
    }
  }, [
    channelId,
    contentType,
    endDate,
    page,
    searchRun,
    space,
    spaceId,
    startDate,
    submittedQuery,
    token
  ])

  function submitSearch (event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const query = queryText.trim()
    if (!/[^\W_]/u.test(query)) {
      setSearchResults(null)
      setSubmittedQuery('')
      setSearchError('Enter at least one letter or number to search.')
      return
    }
    setPage(1)
    setSearchResults(null)
    setSearchError('')
    setSubmittedQuery(query)
    setSearchRun(value => value + 1)
  }

  function clearSearch () {
    setQueryText('')
    setSubmittedQuery('')
    setContentType('all')
    setChannelId('')
    setStartDate('')
    setEndDate('')
    setPage(1)
    setSearchResults(null)
    setSearchError('')
  }

  function changeContentType (value: SpaceSearchContentType) {
    setContentType(value)
    if (value === 'resources') setChannelId('')
    setPage(1)
  }

  const pageTitle = space ? `Search ${space.name}` : 'Search this Space'

  return (
    <AppShell username={window.sessionStorage.getItem('username')} conversationUri={undefined}>
      <main className="space-page space-search-page">
        <p className="space-breadcrumb">
          <Link to="/spaces">Spaces</Link>
          {space && (
            <>
              {' / '}
              <Link to={`/spaces/${encodeURIComponent(space.id)}`}>{space.name}</Link>
              {' / Search'}
            </>
          )}
        </p>
        {contextLoading && <p role="status">Loading Space search…</p>}
        {contextError && (
          <div className="space-failure">
            <h1>Search unavailable</h1>
            <p className="space-error" role="alert">{contextError}</p>
            <Link className="text-link" to="/spaces">Browse Spaces</Link>
          </div>
        )}
        {!contextLoading && !contextError && space && spaceId && (
          <>
            <header className="space-detail-header">
              <p className="eyebrow"><span aria-hidden="true" /> SPACE KNOWLEDGE</p>
              <div className="space-detail-title">
                <div>
                  <h1>{pageTitle}</h1>
                  <p className="space-purpose">Find discussions and shared links.</p>
                </div>
                <Link
                  className="button button-secondary"
                  to={`/spaces/${encodeURIComponent(spaceId)}`}
                >
                  Space overview
                </Link>
              </div>
            </header>

            <form className="space-search-form" onSubmit={submitSearch}>
              <label htmlFor="space-search-query">Search discussions and resources</label>
              <div className="space-search-query-row">
                <input
                  autoComplete="off"
                  id="space-search-query"
                  maxLength={200}
                  onChange={event => setQueryText(event.target.value)}
                  placeholder="Try a phrase or keyword"
                  type="search"
                  value={queryText}
                />
                <button className="button button-primary" disabled={searchLoading} type="submit">
                  {searchLoading ? 'Searching…' : 'Search'}
                </button>
                <button
                  className="button button-secondary"
                  disabled={!queryText && !submittedQuery && contentType === 'all' && !channelId && !startDate && !endDate}
                  onClick={clearSearch}
                  type="button"
                >
                  Clear
                </button>
              </div>
              <div className="space-search-filters">
                <label>
                  Content type
                  <select
                    onChange={event => {
                      const value = event.target.value
                      if (
                        value === 'all' ||
                        value === 'discussions' ||
                        value === 'knowledge' ||
                        value === 'resources'
                      ) {
                        changeContentType(value)
                      }
                    }}
                    value={contentType}
                  >
                    <option value="all">All</option>
                    <option value="discussions">Discussions</option>
                    <option value="knowledge">Preserved knowledge</option>
                    <option value="resources">Resources</option>
                  </select>
                </label>
                <label>
                  Channel
                  <select
                    disabled={contentType === 'resources'}
                    onChange={event => {
                      setChannelId(event.target.value)
                      setPage(1)
                    }}
                    value={channelId}
                  >
                    <option value="">All channels</option>
                    {channels.map(channel => (
                      <option key={channel.id} value={channel.id}>
                        #{channel.name}{channel.archived ? ' (archived)' : ''}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  From date
                  <input
                    onChange={event => {
                      setStartDate(event.target.value)
                      setPage(1)
                    }}
                    type="date"
                    value={startDate}
                  />
                </label>
                <label>
                  To date
                  <input
                    onChange={event => {
                      setEndDate(event.target.value)
                      setPage(1)
                    }}
                    type="date"
                    value={endDate}
                  />
                </label>
              </div>
              <p className="space-search-hint">
                Channel filters narrow discussions and preserved knowledge; resource results remain included when searching all content.
              </p>
            </form>

            {searchError && <p className="space-error" role="alert">{searchError}</p>}
            {!submittedQuery && !searchError && (
              <p className="space-empty" role="status">
                Search past channel messages and active links shared in this Space.
              </p>
            )}
            {searchLoading && <p className="space-search-status" role="status">Searching this Space…</p>}
            {searchResults && !searchLoading && (
              <section className="space-section space-search-results-section" aria-labelledby="space-search-results-heading">
                <div className="space-section-heading">
                  <div>
                    <p className="section-index">SEARCH RESULTS</p>
                    <h2 id="space-search-results-heading">
                      {searchResults.count} {searchResults.count === 1 ? 'result' : 'results'}
                    </h2>
                  </div>
                  {searchResults.totalPages > 0 && (
                    <span className="space-count">
                      Page {searchResults.page} of {searchResults.totalPages}
                    </span>
                  )}
                </div>
                {searchResults.count === 0
                  ? (
                    <p className="space-empty" role="status">
                      No discussions, preserved knowledge, or active resources match “{submittedQuery}”.
                    </p>
                  )
                  : (
                    <ol className="space-search-results">
                      {searchResults.results.map(result => (
                        <li key={`${result.type}-${result.id}`}>
                          <article className="space-search-result">
                            <Link
                              className="space-search-result-title"
                              to={searchResultPath(spaceId, result)}
                            >
                              {highlightText(result.title, submittedQuery)}
                            </Link>
                            {result.excerpt && (
                              <p className="space-search-result-excerpt">
                                {highlightText(result.excerpt, submittedQuery)}
                              </p>
                            )}
                            <p className="space-search-result-meta">
                              <span>{resultSourceLabel(result)}</span>
                              {result.author && <span>BY {result.author}</span>}
                              <time dateTime={result.createdAt}>
                                {formatCreatedAt(result.createdAt)}
                              </time>
                            </p>
                          </article>
                        </li>
                      ))}
                    </ol>
                  )}
                {searchResults.totalPages > 1 && (
                  <nav className="space-search-pagination" aria-label="Search result pages">
                    <button
                      className="button button-secondary"
                      disabled={searchResults.page <= 1 || searchLoading}
                      onClick={() => setPage(current => current - 1)}
                      type="button"
                    >
                      Previous
                    </button>
                    <button
                      className="button button-secondary"
                      disabled={searchResults.page >= searchResults.totalPages || searchLoading}
                      onClick={() => setPage(current => current + 1)}
                      type="button"
                    >
                      Next
                    </button>
                  </nav>
                )}
              </section>
            )}
          </>
        )}
      </main>
    </AppShell>
  )
}
