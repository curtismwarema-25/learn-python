export const API_BASE_URL = `${window.location.protocol}//${window.location.hostname}:8000`

export interface ChatMessage {
  id: number
  user: { username: string }
  message: string
  resources?: SpaceResourceReference[]
  knowledge?: SpaceKnowledgeReference
}

export interface SpaceKnowledgeReference {
  id: number
  status: SpaceKnowledgeStatus
}

export type SpaceKnowledgeStatus = 'active' | 'needs_review' | 'source_deleted' | 'withdrawn'

export interface SpaceKnowledgeVersion {
  id: number
  versionNumber: number
  content: string
  explanation: string
  sourceMessageId: number
  createdByUsername: string
  createDate: string
  isCurrent: boolean
}

export interface SpaceKnowledgeHistory {
  knowledgeId: number
  status: SpaceKnowledgeStatus
  currentVersion: number | null
  versions: SpaceKnowledgeVersion[]
}

export type SpaceResourceStatus = 'active' | 'archived' | 'deleted'

export interface SpaceResourceReference {
  id: string
  title: string
  status: SpaceResourceStatus
}

export interface SpaceResource {
  id: string
  type: 'link'
  title: string
  description: string
  url: string | null
  sourceDomain: string | null
  creatorUsername: string | null
  status: SpaceResourceStatus
  deletedAt: string | null
  createDate: string
  updateDate: string
  canEdit: boolean
  canArchive: boolean
  canRestore: boolean
  canDelete: boolean
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

export type SpaceSearchContentType = 'all' | 'discussions' | 'knowledge' | 'resources'

export interface SpaceSearchResult {
  id: string
  type: 'discussion' | 'knowledge' | 'resource'
  title: string
  excerpt: string
  createdAt: string
  author: string | null
  channel: {
    id: string
    name: string
    archived: boolean
  } | null
  sourceDomain: string | null
  sourceMessageId: string | null
  knowledgeId: number | null
  knowledgePreservedAt: string | null
  sourceUpdatedAt: string | null
  knowledgeVersion: number | null
  knowledgeCorrected: boolean
}

export interface SpaceSearchResponse {
  count: number
  page: number
  pageSize: number
  totalPages: number
  results: SpaceSearchResult[]
}

export interface LearningActivity {
  id: number
  kind: 'short_response'
  prompt: string
}

export interface LearningLesson {
  id: number
  title: string
  objective: string
  body: string
  estimatedMinutes: number
  position: number
  activity: LearningActivity
  completed: boolean
  response: string | null
  discussions: LearningDiscussion[]
}

export interface LearningDiscussion {
  spaceId: string
  spaceName: string
  channelId: string
  channelName: string
  sourceMessageId: number | null
}

export interface LearningUnit {
  id: number
  title: string
  description: string
  position: number
  lessons: LearningLesson[]
}

export interface LearningPathway {
  slug: string
  title: string
  description: string
  outcome: string
  units: LearningUnit[]
  enrolled: boolean
  completedLessons: number
  totalLessons: number
  status: 'draft' | 'published' | 'archived'
}

export interface LearningCompletion {
  lessonId: number
  completed: boolean
  response: string
  completedLessons: number
  totalLessons: number
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

function isInteger (value: unknown): value is number {
  return typeof value === 'number' && Number.isInteger(value)
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

function parseLearningLesson (value: unknown): LearningLesson {
  if (!isRecord(value) || !isInteger(value.id) || typeof value.title !== 'string' ||
    typeof value.objective !== 'string' || typeof value.body !== 'string' ||
    !isInteger(value.estimated_minutes) || !isInteger(value.position) ||
    !isRecord(value.activity) || !isInteger(value.activity.id) ||
    value.activity.kind !== 'short_response' || typeof value.activity.prompt !== 'string' ||
    typeof value.completed !== 'boolean' ||
    !(value.response === null || typeof value.response === 'string') ||
    !Array.isArray(value.discussions)) {
    throw new Error('The server returned an invalid learning lesson.')
  }
  const discussions = value.discussions.map(item => {
    if (!isRecord(item) || typeof item.space_id !== 'string' || typeof item.space_name !== 'string' ||
      typeof item.channel_id !== 'string' || typeof item.channel_name !== 'string' ||
      !(item.source_message_id === null || isInteger(item.source_message_id))) {
      throw new Error('The server returned an invalid learning discussion.')
    }
    return {
      spaceId: item.space_id,
      spaceName: item.space_name,
      channelId: item.channel_id,
      channelName: item.channel_name,
      sourceMessageId: item.source_message_id
    }
  })
  return {
    id: value.id,
    title: value.title,
    objective: value.objective,
    body: value.body,
    estimatedMinutes: value.estimated_minutes,
    position: value.position,
    activity: {
      id: value.activity.id,
      kind: 'short_response',
      prompt: value.activity.prompt
    },
    completed: value.completed,
    response: value.response,
    discussions
  }
}

export function parseLearningPathway (value: unknown): LearningPathway {
  if (!isRecord(value) || typeof value.slug !== 'string' || typeof value.title !== 'string' ||
    typeof value.description !== 'string' || typeof value.outcome !== 'string' ||
    !Array.isArray(value.units) || (value.status !== 'draft' && value.status !== 'published' && value.status !== 'archived') || typeof value.enrolled !== 'boolean' ||
    !isInteger(value.completed_lessons) || !isInteger(value.total_lessons)) {
    throw new Error('The server returned an invalid learning pathway.')
  }
  const units = value.units.map(unit => {
    if (!isRecord(unit) || !isInteger(unit.id) || typeof unit.title !== 'string' ||
      typeof unit.description !== 'string' || !isInteger(unit.position) ||
      !Array.isArray(unit.lessons)) {
      throw new Error('The server returned an invalid learning unit.')
    }
    return {
      id: unit.id,
      title: unit.title,
      description: unit.description,
      position: unit.position,
      lessons: unit.lessons.map(parseLearningLesson)
    }
  })
  return {
    slug: value.slug,
    title: value.title,
    description: value.description,
    outcome: value.outcome,
    units,
    enrolled: value.enrolled,
    completedLessons: value.completed_lessons,
    totalLessons: value.total_lessons,
    status: value.status
  }
}

export function parseLearningPathways (value: unknown): LearningPathway[] {
  if (!Array.isArray(value)) throw new Error('The server returned invalid learning pathways.')
  return value.map(parseLearningPathway)
}

export function parseLearningCompletion (value: unknown): LearningCompletion {
  if (!isRecord(value) || !isInteger(value.lesson_id) || value.completed !== true ||
    typeof value.response !== 'string' || !isInteger(value.completed_lessons) ||
    !isInteger(value.total_lessons)) {
    throw new Error('The server returned an invalid learning completion.')
  }
  return {
    lessonId: value.lesson_id,
    completed: true,
    response: value.response,
    completedLessons: value.completed_lessons,
    totalLessons: value.total_lessons
  }
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

  let resources: SpaceResourceReference[] = []
  if (value.resources !== undefined) {
    if (!Array.isArray(value.resources)) {
      throw new Error('The server returned invalid message resources.')
    }
    resources = value.resources.map(parseSpaceResourceReference)
  }

  let knowledge: SpaceKnowledgeReference | undefined
  if (value.knowledge !== undefined) {
    if (
      !isRecord(value.knowledge) ||
      !isInteger(value.knowledge.id) ||
      !isKnowledgeStatus(value.knowledge.status)
    ) {
      throw new Error('The server returned invalid preserved knowledge.')
    }
    knowledge = { id: value.knowledge.id, status: value.knowledge.status }
  }

  return {
    id: value.id,
    user: { username: value.user.username },
    message: value.message,
    resources,
    ...(knowledge ? { knowledge } : {})
  }
}

export function parseSpaceKnowledgeReference (value: unknown): SpaceKnowledgeReference {
  if (
    !isRecord(value) ||
    !isInteger(value.id) ||
    !isKnowledgeStatus(value.status)
  ) {
    throw new Error('The server returned invalid preserved knowledge.')
  }
  return { id: value.id, status: value.status }
}

function isKnowledgeStatus (value: unknown): value is SpaceKnowledgeStatus {
  return value === 'active' || value === 'needs_review' || value === 'source_deleted' || value === 'withdrawn'
}

export function parseSpaceKnowledgeHistory (value: unknown): SpaceKnowledgeHistory {
  if (
    !isRecord(value) ||
    !isInteger(value.knowledge_id) ||
    !isKnowledgeStatus(value.status) ||
    !(value.current_version === null || isInteger(value.current_version)) ||
    !Array.isArray(value.versions)
  ) {
    throw new Error('The server returned invalid knowledge history.')
  }
  return {
    knowledgeId: value.knowledge_id,
    status: value.status,
    currentVersion: value.current_version,
    versions: value.versions.map(parseSpaceKnowledgeVersion)
  }
}

function parseSpaceKnowledgeVersion (value: unknown): SpaceKnowledgeVersion {
  if (
    !isRecord(value) ||
    !isInteger(value.id) ||
    !isInteger(value.version_number) ||
    typeof value.content !== 'string' ||
    typeof value.explanation !== 'string' ||
    !isInteger(value.source_message_id) ||
    typeof value.created_by_username !== 'string' ||
    typeof value.create_date !== 'string' ||
    typeof value.is_current !== 'boolean'
  ) {
    throw new Error('The server returned an invalid knowledge version.')
  }
  return {
    id: value.id,
    versionNumber: value.version_number,
    content: value.content,
    explanation: value.explanation,
    sourceMessageId: value.source_message_id,
    createdByUsername: value.created_by_username,
    createDate: value.create_date,
    isCurrent: value.is_current
  }
}

function isSpaceResourceStatus (value: unknown): value is SpaceResourceStatus {
  return value === 'active' || value === 'archived' || value === 'deleted'
}

export function parseSpaceResourceReference (value: unknown): SpaceResourceReference {
  if (
    !isRecord(value) ||
    typeof value.id !== 'string' ||
    typeof value.title !== 'string' ||
    !isSpaceResourceStatus(value.status)
  ) {
    throw new Error('The server returned an invalid resource reference.')
  }
  return {
    id: value.id,
    title: value.title,
    status: value.status
  }
}

export function parseSpaceResource (value: unknown): SpaceResource {
  if (
    !isRecord(value) ||
    typeof value.id !== 'string' ||
    value.type !== 'link' ||
    typeof value.title !== 'string' ||
    typeof value.description !== 'string' ||
    !(value.url === null || typeof value.url === 'string') ||
    !(value.source_domain === null || typeof value.source_domain === 'string') ||
    !(value.creator_username === null || typeof value.creator_username === 'string') ||
    !isSpaceResourceStatus(value.status) ||
    !(value.deleted_at === null || typeof value.deleted_at === 'string') ||
    typeof value.create_date !== 'string' ||
    typeof value.update_date !== 'string' ||
    typeof value.can_edit !== 'boolean' ||
    typeof value.can_archive !== 'boolean' ||
    typeof value.can_restore !== 'boolean' ||
    typeof value.can_delete !== 'boolean'
  ) {
    throw new Error('The server returned an invalid Space resource.')
  }

  return {
    id: value.id,
    type: 'link',
    title: value.title,
    description: value.description,
    url: value.url,
    sourceDomain: value.source_domain,
    creatorUsername: value.creator_username,
    status: value.status,
    deletedAt: value.deleted_at,
    createDate: value.create_date,
    updateDate: value.update_date,
    canEdit: value.can_edit,
    canArchive: value.can_archive,
    canRestore: value.can_restore,
    canDelete: value.can_delete
  }
}

export function parseSpaceResources (value: unknown): SpaceResource[] {
  if (!Array.isArray(value)) {
    throw new Error('The server returned an invalid Space resource list.')
  }
  return value.map(parseSpaceResource)
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

export function parseSpaceSearchResponse (value: unknown): SpaceSearchResponse {
  if (!isRecord(value)) {
    throw new Error('The server returned an invalid Space search response.')
  }

  const { count, page, page_size: pageSize, total_pages: totalPages, results } = value
  if (
    !isInteger(count) ||
    count < 0 ||
    !isInteger(page) ||
    page < 1 ||
    !isInteger(pageSize) ||
    pageSize < 1 ||
    pageSize > 50 ||
    !isInteger(totalPages) ||
    totalPages < 0 ||
    !Array.isArray(results)
  ) {
    throw new Error('The server returned an invalid Space search response.')
  }

  const expectedPages = Math.ceil(count / pageSize)
  if (
    totalPages !== expectedPages ||
    results.length > pageSize
  ) {
    throw new Error('The server returned an invalid Space search page.')
  }

  return {
    count,
    page,
    pageSize,
    totalPages,
    results: results.map(parseSpaceSearchResult)
  }
}

function parseSpaceSearchResult (value: unknown): SpaceSearchResult {
  if (
    !isRecord(value) ||
    typeof value.id !== 'string' ||
    (value.type !== 'discussion' && value.type !== 'knowledge' && value.type !== 'resource') ||
    typeof value.title !== 'string' ||
    typeof value.excerpt !== 'string' ||
    typeof value.created_at !== 'string' ||
    Number.isNaN(Date.parse(value.created_at)) ||
    !(value.author === null || typeof value.author === 'string') ||
    !(value.source_domain === null || typeof value.source_domain === 'string') ||
    !(value.source_message_id === null || typeof value.source_message_id === 'string') ||
    !(value.knowledge_id === null || isInteger(value.knowledge_id)) ||
    !(value.knowledge_preserved_at === null || typeof value.knowledge_preserved_at === 'string') ||
    !(value.source_updated_at === null || typeof value.source_updated_at === 'string') ||
    !(value.knowledge_version === null || isInteger(value.knowledge_version)) ||
    typeof value.knowledge_corrected !== 'boolean'
  ) {
    throw new Error('The server returned an invalid Space search result.')
  }

  let channel: SpaceSearchResult['channel'] = null
  if (value.channel !== null) {
    if (
      !isRecord(value.channel) ||
      typeof value.channel.id !== 'string' ||
      typeof value.channel.name !== 'string' ||
      typeof value.channel.archived !== 'boolean'
    ) {
      throw new Error('The server returned an invalid search channel.')
    }
    channel = {
      id: value.channel.id,
      name: value.channel.name,
      archived: value.channel.archived
    }
  }

  if (
    ((value.type === 'discussion' || value.type === 'knowledge') && channel === null) ||
    (value.type === 'resource' && channel !== null) ||
    (value.type === 'knowledge' && (
      typeof value.source_message_id !== 'string' ||
      !isInteger(value.knowledge_id) ||
      typeof value.knowledge_preserved_at !== 'string' ||
      typeof value.source_updated_at !== 'string' ||
      !isInteger(value.knowledge_version)
    ))
  ) {
    throw new Error('The server returned a mismatched search source.')
  }

  return {
    id: value.id,
    type: value.type,
    title: value.title,
    excerpt: value.excerpt,
    createdAt: value.created_at,
    author: value.author,
    channel,
    sourceDomain: value.source_domain,
    sourceMessageId: value.source_message_id,
    knowledgeId: value.knowledge_id,
    knowledgePreservedAt: value.knowledge_preserved_at,
    sourceUpdatedAt: value.source_updated_at,
    knowledgeVersion: value.knowledge_version,
    knowledgeCorrected: value.knowledge_corrected
  }
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
