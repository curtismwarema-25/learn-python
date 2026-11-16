import { useState } from 'react'
import type { FormEvent } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
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
    <section className="container">
      <h1 className="text-center">Welcome to Fuego!</h1>

      <div id="auth-container" className="row">
        <div className="col-sm-4 offset-sm-4">
          <ul className="nav nav-tabs nav-justified" role="tablist">
            <li className="nav-item">
              <button
                className={`nav-link ${activeTab === 'signup' ? 'active' : ''}`}
                id="signup-tab"
                type="button"
                role="tab"
                aria-controls="signup"
                aria-selected={activeTab === 'signup'}
                onClick={() => {
                  setErrorMessage('')
                  setActiveTab('signup')
                }}
              >
                Sign Up
              </button>
            </li>
            <li className="nav-item">
              <button
                className={`nav-link ${activeTab === 'signin' ? 'active' : ''}`}
                id="signin-tab"
                type="button"
                role="tab"
                aria-controls="signin"
                aria-selected={activeTab === 'signin'}
                onClick={() => {
                  setErrorMessage('')
                  setActiveTab('signin')
                }}
              >
                Sign In
              </button>
            </li>
          </ul>

          {errorMessage && (
            <p className="alert alert-danger" role="alert">{errorMessage}</p>
          )}

          <div
            className="tab-content auth-content"
            id={activeTab}
            role="tabpanel"
            aria-labelledby={`${activeTab}-tab`}
          >
            <form onSubmit={handleSubmit}>
              {activeTab === 'signup' && (
                <div className="mb-3">
                  <input
                    className="form-control"
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

              <div className="mb-3">
                <input
                  className="form-control"
                  id={`${activeTab}-username`}
                  type="text"
                  placeholder="Username"
                  autoComplete="username"
                  value={username}
                  onChange={event => setUsername(event.target.value)}
                  required
                />
              </div>

              <div className="mb-3">
                <input
                  className="form-control"
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
                <div className="form-check mb-3">
                  <input className="form-check-input" type="checkbox" id="toc" required />
                  <label className="form-check-label" htmlFor="toc">
                    Accept terms and Conditions
                  </label>
                </div>
              )}

              <button className="btn btn-primary w-100" type="submit" disabled={submitting}>
                {submitting
                  ? 'Please wait...'
                  : activeTab === 'signup' ? 'Sign up' : 'Sign in'}
              </button>
            </form>
          </div>
        </div>
      </div>
    </section>
  )
}
