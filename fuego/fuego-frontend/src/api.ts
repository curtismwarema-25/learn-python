export const API_BASE_URL = `${window.location.protocol}//${window.location.hostname}:8000`

export interface ChatMessage {
  id: number
  user: { username: string }
  message: string
}

export interface SpaceChannel {
  id: string
  name: string
  description: string
  archived: boolean
  createdByUsername: string
  createDate: string
  updateDate: string
}

export interface ChatInvite {
  canManage: boolean
  token: string | null
  expiresAt: string | null
}

export type SpaceRole = 'owner' | 'administrator' | 'moderator' | 'member'
export type SpaceVisibility = 'private' | 'discoverable'
export type SpaceMembershipStatus = 'owner' | 'member' | 'pending' | 'none'

export interface SpaceMetadata {
  id: string
  name: string
  description: string
  purpose: string
}

export interface SpaceSummary extends SpaceMetadata {
  visibility: SpaceVisibility
  role: SpaceRole | null
}

export interface SpaceDetail extends SpaceSummary {
  membershipStatus: SpaceMembershipStatus
}

export interface SpaceMember {
  userId: number
  username: string
  role: SpaceRole
  createDate: string
}

export interface SpaceJoinRequest {
  id: number
  userId: number
  username: string
  status: 'pending'
  requestedAt: string
}

export interface SpaceInvite {
  canManage: boolean
  token: string | null
  expiresAt: string | null
}

function isRecord (value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

const SPACE_ROLES: SpaceRole[] = ['owner', 'administrator', 'moderator', 'member']
const SPACE_MEMBERSHIP_STATUSES: SpaceMembershipStatus[] = [
  'owner',
  'member',
  'pending',
  'none'
]

function isSpaceRole (value: unknown): value is SpaceRole {
  return typeof value === 'string' && SPACE_ROLES.some(role => role === value)
}

function isSpaceMembershipStatus (value: unknown): value is SpaceMembershipStatus {
  return typeof value === 'string' &&
    SPACE_MEMBERSHIP_STATUSES.some(status => status === value)
}

export function getErrorMessage (error: unknown): string {
  return error instanceof Error ? error.message : 'An unexpected error occurred.'
}

export function parseAuthToken (value: unknown): string {
  if (!isRecord(value) || typeof value.auth_token !== 'string') {
    throw new Error('The server returned an invalid authentication token.')
  }
  return value.auth_token
}

export function parseChatUri (value: unknown): string {
  if (!isRecord(value) || typeof value.uri !== 'string') {
    throw new Error('The server returned an invalid chat session.')
  }
  return value.uri
}

export function parseChatInvite (value: unknown): ChatInvite {
  if (
    !isRecord(value) ||
    typeof value.can_manage !== 'boolean' ||
    !(value.token === null || typeof value.token === 'string') ||
    !(value.expires_at === null || typeof value.expires_at === 'string') ||
    (value.token !== null && value.expires_at === null) ||
    (!value.can_manage && (value.token !== null || value.expires_at !== null))
  ) {
    throw new Error('The server returned an invalid invite link.')
  }

  return {
    canManage: value.can_manage,
    token: value.token,
    expiresAt: value.expires_at
  }
}

export function parseChatMessage (value: unknown): ChatMessage {
  if (
    !isRecord(value) ||
    typeof value.id !== 'number' ||
    !isRecord(value.user) ||
    typeof value.user.username !== 'string' ||
    typeof value.message !== 'string'
  ) {
    throw new Error('The server returned an invalid chat message.')
  }

  return {
    id: value.id,
    user: { username: value.user.username },
    message: value.message
  }
}

export function parseChatMessages (value: unknown): ChatMessage[] {
  if (!isRecord(value) || !Array.isArray(value.messages)) {
    throw new Error('The server returned an invalid chat history.')
  }
  return value.messages.map(parseChatMessage)
}

export function parseSpaceChannel (value: unknown): SpaceChannel {
  if (
    !isRecord(value) ||
    typeof value.id !== 'string' ||
    typeof value.name !== 'string' ||
    typeof value.description !== 'string' ||
    typeof value.archived !== 'boolean' ||
    typeof value.created_by_username !== 'string' ||
    typeof value.create_date !== 'string' ||
    typeof value.update_date !== 'string'
  ) {
    throw new Error('The server returned an invalid Space channel.')
  }
  return {
    id: value.id,
    name: value.name,
    description: value.description,
    archived: value.archived,
    createdByUsername: value.created_by_username,
    createDate: value.create_date,
    updateDate: value.update_date
  }
}

export function parseSpaceChannels (value: unknown): SpaceChannel[] {
  if (!Array.isArray(value)) {
    throw new Error('The server returned an invalid Space channel list.')
  }
  return value.map(parseSpaceChannel)
}

export function parseSpaceChannelMessages (value: unknown): {
  id: string
  name: string
  messages: ChatMessage[]
} {
  if (
    !isRecord(value) ||
    typeof value.id !== 'string' ||
    typeof value.name !== 'string'
  ) {
    throw new Error('The server returned an invalid Space channel history.')
  }
  return {
    id: value.id,
    name: value.name,
    messages: parseChatMessages(value)
  }
}

function parseSpaceMetadata (value: unknown): SpaceMetadata {
  if (
    !isRecord(value) ||
    typeof value.id !== 'string' ||
    typeof value.name !== 'string' ||
    typeof value.description !== 'string' ||
    typeof value.purpose !== 'string'
  ) {
    throw new Error('The server returned invalid Space metadata.')
  }
  return {
    id: value.id,
    name: value.name,
    description: value.description,
    purpose: value.purpose
  }
}

export function parseSpaceMetadataList (value: unknown): SpaceMetadata[] {
  if (!Array.isArray(value)) {
    throw new Error('The server returned an invalid Space directory.')
  }
  return value.map(parseSpaceMetadata)
}

export function parseSpaceSummary (value: unknown): SpaceSummary {
  const metadata = parseSpaceMetadata(value)
  if (
    !isRecord(value) ||
    (value.visibility !== 'private' && value.visibility !== 'discoverable') ||
    !(value.role === null || isSpaceRole(value.role))
  ) {
    throw new Error('The server returned an invalid Space summary.')
  }
  return {
    ...metadata,
    visibility: value.visibility,
    role: value.role
  }
}

export function parseSpaceSummaryList (value: unknown): SpaceSummary[] {
  if (!Array.isArray(value)) {
    throw new Error('The server returned an invalid Space list.')
  }
  return value.map(parseSpaceSummary)
}

export function parseSpaceDetail (value: unknown): SpaceDetail {
  const summary = parseSpaceSummary(value)
  if (
    !isRecord(value) ||
    !isSpaceMembershipStatus(value.membership_status)
  ) {
    throw new Error('The server returned an invalid Space detail.')
  }
  return {
    ...summary,
    membershipStatus: value.membership_status
  }
}

export function parseSpaceMembers (value: unknown): SpaceMember[] {
  if (!Array.isArray(value)) {
    throw new Error('The server returned an invalid Space member list.')
  }
  return value.map(member => {
    if (
      !isRecord(member) ||
      typeof member.user_id !== 'number' ||
      typeof member.username !== 'string' ||
      !isSpaceRole(member.role) ||
      typeof member.create_date !== 'string'
    ) {
      throw new Error('The server returned an invalid Space member.')
    }
    return {
      userId: member.user_id,
      username: member.username,
      role: member.role,
      createDate: member.create_date
    }
  })
}

export function parseSpaceJoinRequests (value: unknown): SpaceJoinRequest[] {
  if (!Array.isArray(value)) {
    throw new Error('The server returned an invalid join-request list.')
  }
  return value.map(joinRequest => {
    if (
      !isRecord(joinRequest) ||
      typeof joinRequest.id !== 'number' ||
      typeof joinRequest.user_id !== 'number' ||
      typeof joinRequest.username !== 'string' ||
      joinRequest.status !== 'pending' ||
      typeof joinRequest.requested_at !== 'string'
    ) {
      throw new Error('The server returned an invalid join request.')
    }
    return {
      id: joinRequest.id,
      userId: joinRequest.user_id,
      username: joinRequest.username,
      status: 'pending',
      requestedAt: joinRequest.requested_at
    }
  })
}

export function parseSpaceInvite (value: unknown): SpaceInvite {
  if (
    !isRecord(value) ||
    typeof value.can_manage !== 'boolean' ||
    !(value.token === null || typeof value.token === 'string') ||
    !(value.expires_at === null || typeof value.expires_at === 'string') ||
    (value.token !== null && value.expires_at === null) ||
    (!value.can_manage && (value.token !== null || value.expires_at !== null))
  ) {
    throw new Error('The server returned an invalid Space invite.')
  }
  return {
    canManage: value.can_manage,
    token: value.token,
    expiresAt: value.expires_at
  }
}

export function parseSpaceJoinResult (value: unknown): { spaceId: string } {
  if (
    !isRecord(value) ||
    typeof value.space_id !== 'string' ||
    !isSpaceRole(value.role)
  ) {
    throw new Error('The server returned an invalid Space join result.')
  }
  return { spaceId: value.space_id }
}

export async function apiRequest (path: string, options: RequestInit = {}): Promise<unknown> {
  const response = await fetch(`${API_BASE_URL}${path}`, options)
  if (response.status === 204) return undefined

  let result: unknown

  try {
    result = await response.json()
  } catch {
    if (response.ok) {
      throw new Error('The server returned an invalid response.')
    }
    throw new Error(response.statusText || 'The request failed.')
  }

  if (!response.ok) {
    throw new Error(typeof result === 'string' ? result : JSON.stringify(result))
  }

  return result
}
