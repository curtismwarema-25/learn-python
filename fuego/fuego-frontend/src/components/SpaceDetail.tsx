import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom'
import {
  apiRequest,
  getErrorMessage,
  parseSpaceDetail,
  parseSpaceInvite,
  parseSpaceJoinRequests,
  parseSpaceMembers
} from '../api'
import type {
  SpaceDetail as SpaceDetailData,
  SpaceInvite as SpaceInviteData,
  SpaceJoinRequest,
  SpaceMember,
  SpaceRole,
  SpaceVisibility
} from '../api'
import AppShell from './AppShell'
import SpaceChannels from './SpaceChannels'

const ROLE_OPTIONS: SpaceRole[] = ['member', 'moderator', 'administrator']

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

export default function SpaceDetail () {
  const { spaceId, channelId } = useParams()
  const navigate = useNavigate()
  const location = useLocation()
  const token = getSessionToken()
  const username = getSessionUsername()
  const [space, setSpace] = useState<SpaceDetailData | null>(null)
  const [members, setMembers] = useState<SpaceMember[]>([])
  const [requests, setRequests] = useState<SpaceJoinRequest[]>([])
  const [inviteInfo, setInviteInfo] = useState<SpaceInviteData | null>(null)
  const [loading, setLoading] = useState(true)
  const [pageError, setPageError] = useState('')
  const [actionError, setActionError] = useState('')
  const [notice, setNotice] = useState('')
  const [busyAction, setBusyAction] = useState('')
  const [refreshKey, setRefreshKey] = useState(0)
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [purpose, setPurpose] = useState('')
  const [visibility, setVisibility] = useState<SpaceVisibility>('private')
  const [transferUserId, setTransferUserId] = useState('')

  useEffect(() => {
    if (!spaceId) {
      setPageError('Space not found.')
      setLoading(false)
      return undefined
    }

    const id = spaceId
    const controller = new AbortController()
    let active = true
    setLoading(true)
    setPageError('')
    setActionError('')

    async function loadSpace () {
      try {
        const detail = parseSpaceDetail(await apiRequest(
          `/api/spaces/${encodeURIComponent(id)}/`,
          {
            ...(token ? { headers: authHeaders(token) } : {}),
            signal: controller.signal
          }
        ))
        if (!active) return
        setSpace(detail)
        if (detail.role === 'owner' || detail.role === 'administrator' ||
          detail.role === 'moderator' || detail.role === 'member') {
          setMembers(parseSpaceMembers(await apiRequest(
            `/api/spaces/${encodeURIComponent(id)}/members/`,
            {
              ...(token ? { headers: authHeaders(token) } : {}),
              signal: controller.signal
            }
          )))
        }
        if (detail.role === 'owner' || detail.role === 'administrator') {
          const invite = parseSpaceInvite(await apiRequest(
            `/api/spaces/${encodeURIComponent(id)}/invite/`,
            {
              ...(token ? { headers: authHeaders(token) } : {}),
              signal: controller.signal
            }
          ))
          const joinRequests = parseSpaceJoinRequests(await apiRequest(
            `/api/spaces/${encodeURIComponent(id)}/requests/`,
            {
              ...(token ? { headers: authHeaders(token) } : {}),
              signal: controller.signal
            }
          ))
          if (active) {
            setInviteInfo(invite)
            setRequests(joinRequests)
          }
        } else if (active) {
          setInviteInfo(null)
          setRequests([])
        }
      } catch (error: unknown) {
        if (active && !controller.signal.aborted) {
          setPageError(getErrorMessage(error))
        }
      } finally {
        if (active) setLoading(false)
      }
    }

    void loadSpace()
    return () => {
      active = false
      controller.abort()
    }
  }, [spaceId, token, refreshKey])

  useEffect(() => {
    if (!space) return
    setName(space.name)
    setDescription(space.description)
    setPurpose(space.purpose)
    setVisibility(space.visibility)
  }, [space])

  const canManage = Boolean(
    space?.role === 'owner' || space?.role === 'administrator'
  )
  const isOwner = space?.role === 'owner'
  const inviteUrl = inviteInfo?.token
    ? `${window.location.origin}/spaces/invites/${encodeURIComponent(inviteInfo.token)}`
    : null

  function refresh () {
    setRefreshKey(value => value + 1)
  }

  async function submitAction (
    label: string,
    path: string,
    method: string,
    body?: unknown
  ): Promise<boolean> {
    if (!token || busyAction) return false
    setBusyAction(label)
    setActionError('')
    setNotice('')
    try {
      await apiRequest(path, {
        method,
        headers: {
          ...authHeaders(token),
          ...(body ? { 'Content-Type': 'application/json' } : {})
        },
        ...(body !== undefined ? { body: JSON.stringify(body) } : {})
      })
      setNotice(label)
      refresh()
      return true
    } catch (error: unknown) {
      setActionError(`${label} failed: ${getErrorMessage(error)}`)
      return false
    } finally {
      setBusyAction('')
    }
  }

  async function updateSpace (event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!spaceId || !token || busyAction) return
    await submitAction('Space settings saved', `/api/spaces/${spaceId}/`, 'PATCH', {
      name,
      description,
      purpose,
      visibility
    })
  }

  async function requestAccess () {
    if (!spaceId) return
    if (!token) {
      navigate('/auth', { state: { from: location } })
      return
    }
    await submitAction(
      'Join request submitted',
      `/api/spaces/${spaceId}/requests/`,
      'POST',
      {}
    )
  }

  async function changeInvite (method: 'POST' | 'DELETE') {
    if (!spaceId || !token || busyAction) return
    if (
      method === 'POST' &&
      inviteInfo?.token &&
      !window.confirm('Rotating this invite will invalidate the current link. Continue?')
    ) return
    if (
      method === 'DELETE' &&
      !window.confirm('Revoke this invite link? Existing members will keep their access.')
    ) return

    setBusyAction(method === 'POST' ? 'Rotating invite' : 'Revoking invite')
    setActionError('')
    setNotice('')
    try {
      const invite = parseSpaceInvite(await apiRequest(
        `/api/spaces/${spaceId}/invite/`,
        {
          method,
          headers: authHeaders(token)
        }
      ))
      setInviteInfo(invite)
      setNotice(method === 'POST' ? 'A new seven-day invite link is ready.' : 'Invite link revoked.')
    } catch (error: unknown) {
      setActionError(`Invite could not be updated: ${getErrorMessage(error)}`)
    } finally {
      setBusyAction('')
    }
  }

  async function copyInviteLink () {
    if (!inviteUrl) return
    setActionError('')
    setNotice('')
    try {
      if (!navigator.clipboard) {
        throw new Error('Clipboard access is unavailable in this browser context.')
      }
      await navigator.clipboard.writeText(inviteUrl)
      setNotice('Invite link copied.')
    } catch (error: unknown) {
      setActionError(`Invite link could not be copied: ${getErrorMessage(error)}`)
    }
  }

  async function changeMemberRole (member: SpaceMember, role: SpaceRole) {
    if (!spaceId || member.role === 'owner') return
    await submitAction(
      `Role updated for ${member.username}`,
      `/api/spaces/${spaceId}/members/${member.userId}/`,
      'PATCH',
      { role }
    )
  }

  async function removeMember (member: SpaceMember) {
    if (
      !spaceId ||
      member.role === 'owner' ||
      !window.confirm(`Remove ${member.username} from this Space?`)
    ) return
    await submitAction(
      `${member.username} removed`,
      `/api/spaces/${spaceId}/members/${member.userId}/`,
      'DELETE'
    )
  }

  async function decideRequest (request: SpaceJoinRequest, decision: 'approve' | 'deny') {
    if (!spaceId) return
    await submitAction(
      decision === 'approve' ? `${request.username} approved` : `${request.username} denied`,
      `/api/spaces/${spaceId}/requests/${request.id}/${decision}/`,
      'POST'
    )
  }

  async function leaveSpace () {
    if (
      !spaceId ||
      !window.confirm('Leave this Space? You will need approval or an invitation to rejoin.')
    ) return
    const succeeded = await submitAction(
      'You left the Space',
      `/api/spaces/${spaceId}/leave/`,
      'POST'
    )
    if (succeeded) navigate('/spaces')
  }

  async function transferOwnership (event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (
      !spaceId ||
      !transferUserId ||
      !window.confirm('Transfer ownership? You will become an administrator.')
    ) return
    await submitAction(
      'Ownership transferred',
      `/api/spaces/${spaceId}/transfer/`,
      'POST',
      { user_id: Number(transferUserId) }
    )
  }

  async function deleteSpace () {
    if (
      !spaceId ||
      !window.confirm('Delete this Space? This permanently removes its membership and requests.')
    ) return
    const succeeded = await submitAction(
      'Space deleted',
      `/api/spaces/${spaceId}/`,
      'DELETE'
    )
    if (succeeded) navigate('/spaces')
  }

  return (
    <AppShell username={username} conversationUri={undefined}>
      <main className={channelId ? 'space-page space-page-channel' : 'space-page'}>
        <p className="space-breadcrumb">
          <Link to="/spaces">Spaces</Link>
          {space && (
            <>
              {' / '}
              <Link to={`/spaces/${encodeURIComponent(space.id)}`}>{space.name}</Link>
            </>
          )}
          {channelId && ' / CHANNEL'}
        </p>
        {loading && <p role="status">Loading Space…</p>}
        {pageError && (
          <div className="space-failure">
            <h1>Space unavailable</h1>
            <p className="space-error" role="alert">{pageError}</p>
            <Link className="text-link" to="/spaces">Browse Spaces</Link>
          </div>
        )}
        {!loading && !pageError && space && (
          <>
            <header className="space-detail-header">
              <p className="eyebrow"><span aria-hidden="true" /> SPACE</p>
              <div className="space-detail-title">
                <div>
                  <h1>{space.name}</h1>
                  <p className="space-purpose">{space.purpose}</p>
                </div>
                <span className="space-visibility">
                  {space.visibility === 'private' ? 'PRIVATE' : 'DISCOVERABLE'}
                </span>
              </div>
              {space.description && <p className="space-description">{space.description}</p>}
            </header>

            {(space.membershipStatus === 'owner' || space.membershipStatus === 'member') && (
              <p className="space-resource-entry">
                <Link
                  className="button button-secondary"
                  to={`/spaces/${encodeURIComponent(space.id)}/search`}
                >
                  Search this Space
                </Link>
                <Link
                  className="button button-secondary"
                  to={`/spaces/${encodeURIComponent(space.id)}/resources`}
                >
                  Open resource library
                </Link>
              </p>
            )}

            {space.membershipStatus === 'none' && space.visibility === 'discoverable' && (
              <section className="space-access-section" aria-labelledby="space-access-heading">
                <h2 id="space-access-heading">Join this Space</h2>
                <p>Request access from the Space owner or an administrator.</p>
                <button
                  className="button button-primary"
                  disabled={Boolean(busyAction)}
                  onClick={() => { void requestAccess() }}
                  type="button"
                >
                  {busyAction || 'Request to join'}
                </button>
              </section>
            )}

            {space.membershipStatus === 'pending' && (
              <section className="space-access-section" aria-labelledby="request-status-heading">
                <h2 id="request-status-heading">Request pending</h2>
                <p>You will see Space content after an owner or administrator approves.</p>
                <button
                  className="button button-secondary"
                  disabled={Boolean(busyAction)}
                  onClick={() => {
                    if (spaceId) {
                      void submitAction(
                        'Join request cancelled',
                        `/api/spaces/${spaceId}/requests/`,
                        'DELETE'
                      )
                    }
                  }}
                  type="button"
                >
                  Cancel request
                </button>
              </section>
            )}

            {(space.membershipStatus === 'owner' || space.membershipStatus === 'member') && (
              <>
                {spaceId && (
                  <SpaceChannels
                    spaceId={spaceId}
                    canManage={canManage}
                    username={username}
                  />
                )}
                <section className="space-section" aria-labelledby="space-members-heading">
                  <div className="space-section-heading">
                    <div>
                      <p className="section-index">SPACE MEMBERS</p>
                      <h2 id="space-members-heading">Members</h2>
                    </div>
                    <span className="space-count">{members.length}</span>
                  </div>
                  {members.length === 0 && !loading && (
                    <p className="space-empty">Member information is unavailable.</p>
                  )}
                  {members.length > 0 && (
                    <ul className="space-member-list">
                      {members.map(member => {
                        const canManageMember = canManage &&
                          member.role !== 'owner' &&
                          (isOwner || member.role !== 'administrator')
                        const roleOptions = isOwner
                          ? ROLE_OPTIONS
                          : ROLE_OPTIONS.filter(role => role !== 'administrator')
                        return (
                          <li className="space-member-row" key={member.userId}>
                            <span className="space-member-name">{member.username}</span>
                            {canManageMember
                              ? (
                                <label className="space-role-control">
                                  <span className="visually-hidden">
                                    Role for {member.username}
                                  </span>
                                  <select
                                    disabled={Boolean(busyAction)}
                                    onChange={event => {
                                      const role = ROLE_OPTIONS.find(
                                        option => option === event.target.value
                                      )
                                      if (role) void changeMemberRole(member, role)
                                    }}
                                    value={member.role}
                                  >
                                    {roleOptions.map(role => (
                                      <option key={role} value={role}>{role}</option>
                                    ))}
                                  </select>
                                </label>
                              )
                              : <span className="space-member-role">{member.role}</span>}
                            {canManageMember && (
                              <button
                                className="button button-secondary space-remove-button"
                                disabled={Boolean(busyAction)}
                                onClick={() => { void removeMember(member) }}
                                type="button"
                              >
                                Remove
                              </button>
                            )}
                          </li>
                        )
                      })}
                    </ul>
                  )}
                </section>

                {canManage && (
                  <>
                    <section className="space-section" aria-labelledby="space-requests-heading">
                      <div className="space-section-heading">
                        <div>
                          <p className="section-index">ACCESS</p>
                          <h2 id="space-requests-heading">Join requests</h2>
                        </div>
                      </div>
                      {requests.length === 0
                        ? <p className="space-empty">There are no pending requests.</p>
                        : (
                          <ul className="space-member-list">
                            {requests.map(joinRequest => (
                              <li className="space-member-row" key={joinRequest.id}>
                                <span className="space-member-name">{joinRequest.username}</span>
                                <span className="space-member-role">Requested access</span>
                                <div className="space-inline-actions">
                                  <button
                                    className="button button-secondary"
                                    disabled={Boolean(busyAction)}
                                    onClick={() => { void decideRequest(joinRequest, 'approve') }}
                                    type="button"
                                  >
                                    Approve
                                  </button>
                                  <button
                                    className="button button-secondary"
                                    disabled={Boolean(busyAction)}
                                    onClick={() => { void decideRequest(joinRequest, 'deny') }}
                                    type="button"
                                  >
                                    Deny
                                  </button>
                                </div>
                              </li>
                            ))}
                          </ul>
                        )}
                    </section>

                    <section className="space-section" aria-labelledby="space-invite-heading">
                      <div className="space-section-heading">
                        <div>
                          <p className="section-index">INVITATIONS</p>
                          <h2 id="space-invite-heading">Invite people</h2>
                        </div>
                      </div>
                      <p className="space-empty">
                        Invite links can be used by signed-in users and expire after seven days.
                      </p>
                      {inviteInfo?.token && inviteInfo.expiresAt && (
                        <p className="space-invite-status">
                          Active until {new Date(inviteInfo.expiresAt).toLocaleDateString()}.
                        </p>
                      )}
                      {inviteInfo?.token && inviteUrl && (
                        <div className="space-invite-actions">
                          <Link
                            className="space-invite-link"
                            to={`/spaces/invites/${encodeURIComponent(inviteInfo.token)}`}
                          >
                            Open invite
                          </Link>
                          <button
                            className="button button-secondary"
                            disabled={Boolean(busyAction)}
                            onClick={() => { void copyInviteLink() }}
                            type="button"
                          >
                            Copy link
                          </button>
                        </div>
                      )}
                      {!inviteInfo?.token && inviteInfo?.expiresAt && (
                        <p className="space-invite-status">
                          Invite expired {new Date(inviteInfo.expiresAt).toLocaleDateString()}.
                        </p>
                      )}
                      {!inviteInfo?.token && !inviteInfo?.expiresAt && (
                        <p className="space-invite-status">No active invite link.</p>
                      )}
                      <div className="space-inline-actions">
                        <button
                          className="button button-secondary"
                          disabled={Boolean(busyAction)}
                          onClick={() => { void changeInvite('POST') }}
                          type="button"
                        >
                          {inviteInfo?.token ? 'Rotate invite' : 'Create invite'}
                        </button>
                        {inviteInfo?.token && (
                          <button
                            className="button button-secondary"
                            disabled={Boolean(busyAction)}
                            onClick={() => { void changeInvite('DELETE') }}
                            type="button"
                          >
                            Revoke
                          </button>
                        )}
                      </div>
                    </section>

                    <section className="space-section" aria-labelledby="space-settings-heading">
                      <div className="space-section-heading">
                        <div>
                          <p className="section-index">MANAGEMENT</p>
                          <h2 id="space-settings-heading">Space settings</h2>
                        </div>
                      </div>
                      <form className="space-form" onSubmit={updateSpace}>
                        <label>
                          Space name
                          <input
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
                          Description
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
                        <button
                          className="button button-primary"
                          disabled={Boolean(busyAction)}
                          type="submit"
                        >
                          Save settings
                        </button>
                      </form>
                    </section>
                  </>
                )}

                {space.role !== 'owner' && (
                  <section className="space-section">
                    <button
                      className="button button-secondary"
                      disabled={Boolean(busyAction)}
                      onClick={() => { void leaveSpace() }}
                      type="button"
                    >
                      Leave Space
                    </button>
                  </section>
                )}

                    {isOwner && (
                      <section className="space-section" aria-labelledby="ownership-heading">
                    <div className="space-section-heading">
                      <div>
                        <p className="section-index">OWNER</p>
                        <h2 id="ownership-heading">Ownership</h2>
                      </div>
                    </div>
                    <form className="space-transfer-form" onSubmit={transferOwnership}>
                      <label>
                        Transfer ownership to
                        <select
                          onChange={event => setTransferUserId(event.target.value)}
                          required
                          value={transferUserId}
                        >
                          <option value="">Select a Space member</option>
                          {members
                            .filter(member => member.role !== 'owner')
                            .map(member => (
                              <option key={member.userId} value={member.userId}>
                                {member.username}
                              </option>
                            ))}
                        </select>
                      </label>
                      <button
                        className="button button-secondary"
                        disabled={Boolean(busyAction) || members.length < 2}
                        type="submit"
                      >
                        Transfer ownership
                      </button>
                    </form>
                    <button
                      className="button button-danger"
                      disabled={Boolean(busyAction)}
                      onClick={() => { void deleteSpace() }}
                      type="button"
                    >
                      Delete Space
                    </button>
                  </section>
                )}
              </>
            )}

            {actionError && <p className="space-error" role="alert">{actionError}</p>}
            {notice && <p className="space-notice" role="status">{notice}</p>}
          </>
        )}
      </main>
    </AppShell>
  )
}
