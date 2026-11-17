import { useState } from 'react'
import type { FormEvent } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { apiRequest, getErrorMessage, parseAuthToken } from '../api'

function getSafeRedirect (state: unknown): string {
  if (typeof state !== 'object' || state === null || !('from' in state)) return '/'
  const from = state.from
  if (typeof from !== 'object' || from === null || !('pathname' in from)) return '/'
  const redirect = from.pathname
  return typeof redirect === 'string' &&
    redirect.startsWith('/') &&
    redirect !== '/auth'
    ? redirect
    : '/'
}

export default function UserAuth () {
  const [activeTab, setActiveTab] = useState<'signup' | 'signin'>('signup')
  const [email, setEmail] = useState('')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [errorMessage, setErrorMessage] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const location = useLocation()
  const navigate = useNavigate()

  async function signIn () {
    const token = parseAuthToken(await apiRequest('/auth/token/login/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    }))

    window.sessionStorage.setItem('authToken', token)
    window.sessionStorage.setItem('username', username)
    navigate(getSafeRedirect(location.state), { replace: true })
  }

  async function handleSubmit (event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setErrorMessage('')
    setSubmitting(true)

    try {
      if (activeTab === 'signup') {
        await apiRequest('/auth/users/', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email, username, password })
        })
      }

      await signIn()
    } catch (error: unknown) {
      setErrorMessage(
        `${activeTab === 'signup' ? 'Registration' : 'Sign in'} failed: ${getErrorMessage(error)}`
      )
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <main className="auth-screen">
      <section className="auth-panel" aria-labelledby="auth-heading">
        <Link className="brand-lockup auth-brand" to="/" aria-label="Fuego home">
          <span className="brand-mark" aria-hidden="true">F</span>
          <span className="brand-name">fuego<span>.</span></span>
        </Link>

        <p className="eyebrow"><span>F / ACCOUNT</span> A PLACE TO BEGIN</p>
        <h1 className="auth-heading" id="auth-heading">Join the conversation.</h1>
        <p className="auth-description">Sign in or create an account to get started.</p>

        <div className="auth-tabs" role="tablist" aria-label="Account access">
          <button
            className={`auth-tab ${activeTab === 'signup' ? 'is-active' : ''}`}
            id="signup-tab"
            type="button"
            role="tab"
            aria-controls="signup-panel"
            aria-selected={activeTab === 'signup'}
            onClick={() => {
              setErrorMessage('')
              setActiveTab('signup')
            }}
          >
            Sign Up
          </button>
          <button
            className={`auth-tab ${activeTab === 'signin' ? 'is-active' : ''}`}
            id="signin-tab"
            type="button"
            role="tab"
            aria-controls="signin-panel"
            aria-selected={activeTab === 'signin'}
            onClick={() => {
              setErrorMessage('')
              setActiveTab('signin')
            }}
          >
            Sign In
          </button>
        </div>

        {errorMessage && (
          <p className="notice notice-error auth-error" role="alert">{errorMessage}</p>
        )}

        <div
          className="auth-content"
          id={`${activeTab}-panel`}
          role="tabpanel"
          aria-labelledby={`${activeTab}-tab`}
        >
          <form className="auth-form" onSubmit={handleSubmit}>
            {activeTab === 'signup' && (
              <div>
                <label className="visually-hidden" htmlFor="signup-email">Email address</label>
                <input
                  className="auth-input"
                  id="signup-email"
                  type="email"
                  placeholder="Email Address"
                  autoComplete="email"
                  value={email}
                  onChange={event => setEmail(event.target.value)}
                  required
                />
              </div>
            )}

            <div>
              <label className="visually-hidden" htmlFor={`${activeTab}-username`}>Username</label>
              <input
                className="auth-input"
                id={`${activeTab}-username`}
                type="text"
                placeholder="Username"
                autoComplete="username"
                value={username}
                onChange={event => setUsername(event.target.value)}
                required
              />
            </div>

            <div>
              <label className="visually-hidden" htmlFor={`${activeTab}-password`}>Password</label>
              <input
                className="auth-input"
                id={`${activeTab}-password`}
                type="password"
                placeholder="Password"
                autoComplete={activeTab === 'signup' ? 'new-password' : 'current-password'}
                value={password}
                onChange={event => setPassword(event.target.value)}
                required
              />
            </div>

            {activeTab === 'signup' && (
              <label className="terms-check" htmlFor="toc">
                <input type="checkbox" id="toc" required />
                <span>Accept terms and Conditions</span>
              </label>
            )}

            <button className="button button-primary auth-submit" type="submit" disabled={submitting}>
              {submitting
                ? 'Please wait…'
                : activeTab === 'signup' ? 'Sign up' : 'Sign in'}
            </button>
          </form>
        </div>
      </section>
    </main>
  )
}
