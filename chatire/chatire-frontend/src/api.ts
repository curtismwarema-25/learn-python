export const API_BASE_URL = `${window.location.protocol}//${window.location.hostname}:8000`

export interface ChatMessage {
  id: number
  user: { username: string }
  message: string
}

function isRecord (value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
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

export async function apiRequest (path: string, options: RequestInit = {}): Promise<unknown> {
  const response = await fetch(`${API_BASE_URL}${path}`, options)
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
