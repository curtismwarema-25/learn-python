import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  apiRequest,
  getErrorMessage,
  parseLearningCompletion,
  parseLearningPathway,
  parseLearningPathways
} from '../api'
import type { LearningPathway } from '../api'
import AppShell from './AppShell'

function authHeaders (token: string) {
  return { Authorization: `Token ${token}` }
}

export default function Learning () {
  const { slug } = useParams()
  const token = window.sessionStorage.getItem('authToken')
  const username = window.sessionStorage.getItem('username')
  const [pathways, setPathways] = useState<LearningPathway[]>([])
  const [pathway, setPathway] = useState<LearningPathway | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [responses, setResponses] = useState<Record<number, string>>({})
  const [questions, setQuestions] = useState<Record<number, string>>({})
  const [questionNotice, setQuestionNotice] = useState<Record<number, string>>({})

  useEffect(() => {
    if (!token) return undefined
    const controller = new AbortController()
    let active = true
    setLoading(true)
    setError('')
    const path = slug
      ? `/api/learning/pathways/${encodeURIComponent(slug)}/`
      : '/api/learning/pathways/'
    apiRequest(path, { headers: authHeaders(token), signal: controller.signal })
      .then(value => {
        if (!active) return
        if (slug) setPathway(parseLearningPathway(value))
        else setPathways(parseLearningPathways(value))
      })
      .catch((reason: unknown) => {
        if (active && !controller.signal.aborted) setError(getErrorMessage(reason))
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
      controller.abort()
    }
  }, [slug, token])

  async function enroll () {
    if (!token || !pathway || busy) return
    setBusy(true)
    setError('')
    try {
      await apiRequest(
        `/api/learning/pathways/${encodeURIComponent(pathway.slug)}/enroll/`,
        { method: 'POST', headers: authHeaders(token) }
      )
      setPathway({ ...pathway, enrolled: true })
    } catch (reason: unknown) {
      setError(getErrorMessage(reason))
    } finally {
      setBusy(false)
    }
  }

  async function completeLesson (lessonId: number) {
    if (!token || busy) return
    const response = responses[lessonId]?.trim() || ''
    if (!response) {
      setError('Write a short response before completing the activity.')
      return
    }
    setBusy(true)
    setError('')
    try {
      parseLearningCompletion(await apiRequest(
        `/api/learning/lessons/${lessonId}/complete/`,
        {
          method: 'POST',
          headers: { ...authHeaders(token), 'Content-Type': 'application/json' },
          body: JSON.stringify({ response })
        }
      ))
      const refreshed = parseLearningPathway(await apiRequest(
        `/api/learning/pathways/${encodeURIComponent(pathway?.slug || slug || '')}/`,
        { headers: authHeaders(token) }
      ))
      setPathway(refreshed)
    } catch (reason: unknown) {
      setError(getErrorMessage(reason))
    } finally {
      setBusy(false)
    }
  }

  async function askQuestion (lessonId: number, discussion: { spaceId: string; channelId: string }) {
    if (!token || busy) return
    const message = questions[lessonId]?.trim() || ''
    if (!message) {
      setError('Write a question before sending it.')
      return
    }
    setBusy(true)
    setError('')
    try {
      await apiRequest(`/api/learning/lessons/${lessonId}/questions/`, {
        method: 'POST',
        headers: { ...authHeaders(token), 'Content-Type': 'application/json' },
        body: JSON.stringify({ space_id: discussion.spaceId, channel_id: discussion.channelId, message })
      })
      setQuestions(current => ({ ...current, [lessonId]: '' }))
      setQuestionNotice(current => ({ ...current, [lessonId]: 'Question posted in the discussion.' }))
    } catch (reason: unknown) {
      setError(getErrorMessage(reason))
    } finally {
      setBusy(false)
    }
  }

  return (
    <AppShell conversationUri={undefined} username={username || null}>
      <main className="learning-page">
        <div className="learning-heading">
          <div>
            <p className="section-index">LEARN BY DOING</p>
            <h1>{pathway?.title || 'Learning pathways'}</h1>
            <p className="learning-intro">
              Move from a useful question to a small experiment, then share what you learned.
            </p>
          </div>
          {pathway && (
            <Link className="button button-secondary" to="/learning">All pathways</Link>
          )}
          {!pathway && <Link className="button button-secondary" to="/learning/manage">Author content</Link>}
        </div>
        {loading && <p className="space-empty" role="status">Loading learning content…</p>}
        {error && <p className="space-error" role="alert">{error}</p>}
        {!loading && !error && !pathway && (
          <section className="learning-grid" aria-label="Learning pathways">
            {pathways.map(item => (
              <Link className="learning-card" key={item.slug} to={`/learning/${item.slug}`}>
                <span className="section-index">PATHWAY</span>
                <h2>{item.title}</h2>
                <p>{item.description}</p>
                <span className="learning-card-meta">
                  {item.totalLessons} activities · {item.enrolled ? `${item.completedLessons}/${item.totalLessons} complete` : 'Start learning'}
                </span>
              </Link>
            ))}
          </section>
        )}
        {!loading && !error && pathway && (
          <>
            <section className="learning-overview">
              <p>{pathway.description}</p>
              <p><strong>Outcome:</strong> {pathway.outcome}</p>
              <div className="learning-progress" aria-label="Learning progress">
                <span style={{ width: `${pathway.totalLessons ? (pathway.completedLessons / pathway.totalLessons) * 100 : 0}%` }} />
              </div>
              <p className="learning-progress-label">
                {pathway.completedLessons} of {pathway.totalLessons} activities complete
              </p>
              {!pathway.enrolled && (
                <button className="button button-primary" disabled={busy} onClick={() => { void enroll() }} type="button">
                  Start this pathway
                </button>
              )}
            </section>
            {pathway.units.map(unit => (
              <section className="learning-unit" key={unit.id}>
                <p className="section-index">UNIT {unit.position}</p>
                <h2>{unit.title}</h2>
                <p>{unit.description}</p>
                <div className="learning-lessons">
                  {unit.lessons.map(lesson => (
                    <article className={`learning-lesson ${lesson.completed ? 'is-complete' : ''}`} key={lesson.id}>
                      <div className="learning-lesson-heading">
                        <div>
                          <span className="section-index">LESSON {lesson.position}</span>
                          <h3>{lesson.title}</h3>
                        </div>
                        <span>{lesson.completed ? 'COMPLETE' : `${lesson.estimatedMinutes} MIN`}</span>
                      </div>
                      <p><strong>Objective:</strong> {lesson.objective}</p>
                      <p>{lesson.body}</p>
                      {lesson.discussions.length > 0 && (
                        <div className="learning-discussions">
                          <strong>Discuss this lesson</strong>
                          {lesson.discussions.map(discussion => (
                            <Link
                              key={`${discussion.channelId}-${discussion.sourceMessageId ?? 'channel'}`}
                              to={`/spaces/${discussion.spaceId}/channels/${discussion.channelId}${discussion.sourceMessageId ? `#message-${discussion.sourceMessageId}` : ''}`}
                            >
                              {discussion.spaceName} / {discussion.channelName}
                            </Link>
                          ))}
                          {pathway.enrolled && (
                            <form onSubmit={event => { event.preventDefault(); void askQuestion(lesson.id, lesson.discussions[0]!) }}>
                              <label>
                                Ask a question
                                <textarea
                                  maxLength={2000}
                                  onChange={event => setQuestions(current => ({ ...current, [lesson.id]: event.target.value }))}
                                  placeholder="What would you like to clarify?"
                                  rows={2}
                                  value={questions[lesson.id] || ''}
                                />
                              </label>
                              <button className="button button-secondary" disabled={busy} type="submit">Post question</button>
                              {questionNotice[lesson.id] && <p className="space-success" role="status">{questionNotice[lesson.id]}</p>}
                            </form>
                          )}
                        </div>
                      )}
                      {pathway.enrolled && (
                        <form onSubmit={event => { event.preventDefault(); void completeLesson(lesson.id) }}>
                          <label>
                            Practical response
                            <textarea
                              maxLength={2000}
                              onChange={event => setResponses(current => ({ ...current, [lesson.id]: event.target.value }))}
                              placeholder={lesson.activity.prompt}
                              rows={3}
                              value={responses[lesson.id] ?? lesson.response ?? ''}
                            />
                          </label>
                          <button className="button button-secondary" disabled={busy} type="submit">
                            {lesson.completed ? 'Update response' : 'Complete activity'}
                          </button>
                        </form>
                      )}
                    </article>
                  ))}
                </div>
              </section>
            ))}
          </>
        )}
      </main>
    </AppShell>
  )
}
