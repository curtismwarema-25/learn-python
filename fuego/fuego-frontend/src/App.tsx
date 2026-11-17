import type { ReactNode } from 'react'
import { Navigate, Route, Routes, useLocation } from 'react-router-dom'
import UserAuth from './components/UserAuth'
import Chat from './components/Chat'

function RequireAuth ({ children }: { children: ReactNode }) {
  const location = useLocation()
  const token = window.sessionStorage.getItem('authToken')

  return token
    ? children
    : <Navigate to="/auth" replace state={{ from: location }} />
}

export default function App () {
  return (
    <Routes>
      <Route path="/auth" element={<UserAuth />} />
      <Route
        path="/"
        element={
          <RequireAuth>
            <Chat />
          </RequireAuth>
        }
      />
      <Route
        path="/chats/:uri"
        element={
          <RequireAuth>
            <Chat />
          </RequireAuth>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
