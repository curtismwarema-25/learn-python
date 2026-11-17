import type { ReactNode } from 'react'
import { Navigate, Route, Routes, useLocation } from 'react-router-dom'
import UserAuth from './components/UserAuth'
import Chat from './components/Chat'
import SpaceDetail from './components/SpaceDetail'
import SpaceResources from './components/SpaceResources'
import Spaces, { SpaceInviteJoin } from './components/Spaces'

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
      <Route path="/spaces" element={<Spaces />} />
      <Route
        path="/spaces/:spaceId/resources/:resourceId"
        element={<SpaceResources />}
      />
      <Route
        path="/spaces/:spaceId/resources"
        element={<SpaceResources />}
      />
      <Route
        path="/spaces/:spaceId/channels/:channelId"
        element={<SpaceDetail />}
      />
      <Route path="/spaces/:spaceId" element={<SpaceDetail />} />
      <Route
        path="/spaces/invites/:inviteToken"
        element={
          <RequireAuth>
            <SpaceInviteJoin />
          </RequireAuth>
        }
      />
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
      <Route
        path="/invites/:inviteToken"
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
