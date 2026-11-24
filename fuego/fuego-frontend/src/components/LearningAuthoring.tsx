import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { apiRequest, getErrorMessage, parseLearningPathway, parseLearningPathways } from '../api'
import type { LearningPathway } from '../api'
import AppShell from './AppShell'

function authHeaders (token: string, json = false) {
  return { Authorization: `Token ${token}`, ...(json ? { 'Content-Type': 'application/json' } : {}) }
}

type PathwayForm = { slug: string; title: string; description: string; outcome: string }
type LessonForm = { title: string; objective: string; body: string; prompt: string; position: string }

const emptyLesson: LessonForm = { title: '', objective: '', body: '', prompt: '', position: '1' }

export default function LearningAuthoring () {
  const token = window.sessionStorage.getItem('authToken')
  const username = window.sessionStorage.getItem('username')
  const [pathways, setPathways] = useState<LearningPathway[]>([])
  const [selected, setSelected] = useState<LearningPathway | null>(null)
  const [form, setForm] = useState<PathwayForm>({ slug: '', title: '', description: '', outcome: '' })
  const [unitForm, setUnitForm] = useState({ title: '', description: '', position: '1' })
  const [lessonForms, setLessonForms] = useState<Record<number, LessonForm>>({})
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  async function load () {
    if (!token) return
    setLoading(true)
    try {
      const result = parseLearningPathways(await apiRequest('/api/learning/manage/pathways/', { headers: authHeaders(token) }))
      setPathways(result)
      if (selected) setSelected(result.find(item => item.slug === selected.slug) ?? null)
    } catch (reason: unknown) {
      setError(getErrorMessage(reason))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void load() }, [token])

  function choose (pathway: LearningPathway) {
    setSelected(pathway)
    setForm({ slug: pathway.slug, title: pathway.title, description: pathway.description, outcome: pathway.outcome })
  }

  async function submitPathway (event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!token || busy) return
    setBusy(true); setError('')
    try {
      const result = parseLearningPathway(await apiRequest('/api/learning/manage/pathways/', {
        method: 'POST', headers: authHeaders(token, true), body: JSON.stringify(form)
      }))
      setPathways(current => [...current, result]); choose(result); setNotice('Draft created.')
    } catch (reason: unknown) { setError(getErrorMessage(reason)) } finally { setBusy(false) }
  }

  async function savePathway (event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!token || !selected || busy) return
    setBusy(true); setError('')
    try {
      const result = parseLearningPathway(await apiRequest(`/api/learning/manage/pathways/${encodeURIComponent(selected.slug)}/`, {
        method: 'PATCH', headers: authHeaders(token, true), body: JSON.stringify(form)
      }))
      setSelected(result); setPathways(current => current.map(item => item.slug === result.slug ? result : item)); setNotice('Details saved.')
    } catch (reason: unknown) { setError(getErrorMessage(reason)) } finally { setBusy(false) }
  }

  async function publish (action: 'publish' | 'archive') {
    if (!token || !selected || busy) return
    if (action === 'archive' && !window.confirm('Archive this pathway? Existing progress will be retained.')) return
    setBusy(true); setError('')
    try {
      await apiRequest(`/api/learning/manage/pathways/${encodeURIComponent(selected.slug)}/${action}/`, { method: 'POST', headers: authHeaders(token) })
      await load(); setNotice(action === 'publish' ? 'Published.' : 'Archived.')
    } catch (reason: unknown) { setError(getErrorMessage(reason)) } finally { setBusy(false) }
  }

  async function addUnit (event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!token || !selected || busy) return
    setBusy(true)
    try {
      await apiRequest(`/api/learning/manage/pathways/${encodeURIComponent(selected.slug)}/units/`, {
        method: 'POST', headers: authHeaders(token, true), body: JSON.stringify({ ...unitForm, position: Number(unitForm.position) })
      })
      setUnitForm({ title: '', description: '', position: String(selected.units.length + 2) }); await load(); setNotice('Unit added.')
    } catch (reason: unknown) { setError(getErrorMessage(reason)) } finally { setBusy(false) }
  }

  async function addLesson (event: FormEvent<HTMLFormElement>, unitId: number, lesson: LessonForm) {
    event.preventDefault()
    if (!token || busy) return
    setBusy(true)
    try {
      await apiRequest(`/api/learning/manage/units/${unitId}/lessons/`, {
        method: 'POST', headers: authHeaders(token, true), body: JSON.stringify({ ...lesson, position: Number(lesson.position), activity_prompt: lesson.prompt })
      })
      setLessonForms(current => ({ ...current, [unitId]: emptyLesson })); await load(); setNotice('Lesson added.')
    } catch (reason: unknown) { setError(getErrorMessage(reason)) } finally { setBusy(false) }
  }

  return (
    <AppShell conversationUri={undefined} username={username || null}>
      <main className="learning-page">
        <div className="learning-heading"><div><p className="section-index">CONTENT STUDIO</p><h1>Author learning</h1><p className="learning-intro">Build a useful pathway, keep it private as a draft, then publish it for learners.</p></div><Link className="button button-secondary" to="/learning">Learner view</Link></div>
        {error && <p className="space-error" role="alert">{error}</p>}
        {notice && <p className="space-notice" role="status">{notice}</p>}
        <div className="learning-author-layout">
          <aside className="learning-author-list" aria-label="Learning pathways">
            <h2>Pathways</h2>
            {loading && <p role="status">Loading…</p>}
            {!loading && pathways.length === 0 && <p>No pathways yet.</p>}
            {pathways.map(pathway => <button className={`learning-author-item ${selected?.slug === pathway.slug ? 'is-selected' : ''}`} key={pathway.slug} onClick={() => choose(pathway)} type="button"><strong>{pathway.title}</strong><span>{pathway.status}</span></button>)}
            <form className="learning-author-form" onSubmit={submitPathway}><h3>New pathway</h3><input maxLength={80} onChange={event => setForm({ ...form, slug: event.target.value })} placeholder="pathway-slug" required value={form.slug} /><input maxLength={160} onChange={event => setForm({ ...form, title: event.target.value })} placeholder="Title" required value={form.title} /><textarea onChange={event => setForm({ ...form, description: event.target.value })} placeholder="Description" required rows={2} value={form.description} /><input maxLength={500} onChange={event => setForm({ ...form, outcome: event.target.value })} placeholder="Learner outcome" required value={form.outcome} /><button className="button button-primary" disabled={busy} type="submit">Create draft</button></form>
          </aside>
          {selected && <section className="learning-author-editor">
            <form className="learning-author-form" onSubmit={savePathway}><div className="learning-lesson-heading"><h2>{selected.title}</h2><span>{selected.status}</span></div><label>Slug<input maxLength={80} onChange={event => setForm({ ...form, slug: event.target.value })} required value={form.slug} /></label><label>Title<input maxLength={160} onChange={event => setForm({ ...form, title: event.target.value })} required value={form.title} /></label><label>Description<textarea onChange={event => setForm({ ...form, description: event.target.value })} required rows={3} value={form.description} /></label><label>Outcome<input maxLength={500} onChange={event => setForm({ ...form, outcome: event.target.value })} required value={form.outcome} /></label><div className="space-inline-actions"><button className="button button-secondary" disabled={busy} type="submit">Save details</button><button className="button button-primary" disabled={busy || selected.status === 'published'} onClick={() => { void publish('publish') }} type="button">Publish</button><button className="button button-danger" disabled={busy || selected.status === 'archived'} onClick={() => { void publish('archive') }} type="button">Archive</button></div></form>
            <form className="learning-author-form" onSubmit={addUnit}><h3>Add unit</h3><input maxLength={160} onChange={event => setUnitForm({ ...unitForm, title: event.target.value })} placeholder="Unit title" required value={unitForm.title} /><input maxLength={1000} onChange={event => setUnitForm({ ...unitForm, description: event.target.value })} placeholder="Unit description" value={unitForm.description} /><input min="1" onChange={event => setUnitForm({ ...unitForm, position: event.target.value })} type="number" value={unitForm.position} /><button className="button button-secondary" disabled={busy} type="submit">Add unit</button></form>
            {selected.units.map(unit => { const lesson = lessonForms[unit.id] ?? { ...emptyLesson, position: String(unit.lessons.length + 1) }; return <section className="learning-author-unit" key={unit.id}><p className="section-index">UNIT {unit.position}</p><h3>{unit.title}</h3><p>{unit.description}</p><ul>{unit.lessons.map(item => <li key={item.id}>{item.title} · {item.activity.prompt}</li>)}</ul><form className="learning-author-form" onSubmit={event => { void addLesson(event, unit.id, lesson) }}><h4>Add lesson</h4><input maxLength={160} onChange={event => setLessonForms({ ...lessonForms, [unit.id]: { ...lesson, title: event.target.value } })} placeholder="Lesson title" required value={lesson.title} /><input maxLength={500} onChange={event => setLessonForms({ ...lessonForms, [unit.id]: { ...lesson, objective: event.target.value } })} placeholder="Objective" required value={lesson.objective} /><textarea onChange={event => setLessonForms({ ...lessonForms, [unit.id]: { ...lesson, body: event.target.value } })} placeholder="Lesson explanation" required rows={3} value={lesson.body} /><input maxLength={1000} onChange={event => setLessonForms({ ...lessonForms, [unit.id]: { ...lesson, prompt: event.target.value } })} placeholder="Activity prompt" required value={lesson.prompt} /><button className="button button-secondary" disabled={busy} type="submit">Add lesson</button></form></section> })}
          </section>}
        </div>
      </main>
    </AppShell>
  )
}
