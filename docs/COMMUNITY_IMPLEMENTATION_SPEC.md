# Fuego Community Implementation Specification

**Status:** Approved Space and Channels slices implemented; migrations pending on the tracked local database  
**Product authority:** [Fuego Master](FUEGO_MASTER.md), especially §§5–7, 13–17, 21  
**Technical evidence:** [Technical Baseline](TECHNICAL_BASELINE.md) and current source  
**Scope:** Spaces and shared channels are implemented. Structured discussions,
resources, search, notifications, and AI remain later milestones.

## 1. Current-state assessment

The verified application is a Django 6.1 / Django REST Framework backend with
`chat` and `community` apps, Django Channels WebSockets, SQLite, and a React +
TypeScript frontend. The `community` app contains the Space, membership,
request, and Channel models and APIs. Separate Discussion and Resource models
are not implemented.

Existing chat capabilities that must remain intact include authenticated chat
creation, owner-managed members and invites, message history and sending, and
real-time delivery. Space channel access derives from current Space membership,
not duplicated chat membership. The default Channels consumers authenticate
on the first frame and recheck access before events. The optional
uWSGI/RabbitMQ bridge is limited to direct chats and excludes channel-backed
conversations.

There is no conversation-list endpoint. The frontend now has a Spaces
destination and foundation screens. It is React + TypeScript with React Router;
the Fuego design system and agent guidance are in
`.agents/skills/fuego-design/`.

No separate architecture document or repository-local backend/security skill
was found. Do not treat the roadmap as proof that a feature exists.

## 2. Approved product decisions

| Area | Decision |
|---|---|
| Space visibility | A Space is private by default. Its owner or an administrator may make it discoverable. A public directory shows only its name, description, and purpose; all Space content remains member-only. |
| Joining | A user may join through an authenticated invitation. A user may request membership in a discoverable Space; an owner or administrator must approve the request. Private Spaces are not requestable or listed. |
| Roles | Owner, Administrator, Moderator, and Member. The role matrix is below. |
| Channel access | Every active Space member can read and send in every channel. Private/restricted channels and separate channel membership are out of this slice. |
| Channel management | Every new Space receives a `general` channel. Owner/admin can create, edit, archive, and delete empty channels. Archived channels retain history and are read-only. |
| Invitations | Owner/admin only; authenticated joining; reusable for seven days; revocable and rotatable. An invitation grants the Member role, never an administrative role. |
| Discussion model | Persistent channel message streams reuse the existing chat message infrastructure. Separate titled Discussion entities are deferred until knowledge workflows are validated. |
| Product boundary | Spaces and channels are the approved Community slices. Do not add a feed, resources, search, notifications, or AI as placeholders. |

### Role and permission matrix

| Capability | Owner | Administrator | Moderator | Member |
|---|---:|---:|---:|---:|
| View Space content and participate | Yes | Yes | Yes | Yes |
| Edit Space profile and visibility | Yes | Yes | No | No |
| Create, rotate, and revoke Space invite | Yes | Yes | No | No |
| View and approve/deny join requests | Yes | Yes | No | No |
| Remove members | Yes | Yes, except owner/other administrators | No | No |
| Assign Member or Moderator | Yes | Yes | No | No |
| Assign Administrator or transfer ownership | Yes | No | No | No |
| Delete the Space | Yes | No | No | No |
| Create, edit, archive, or delete an empty channel | Yes | Yes | No | No |
| Read and send channel messages | Yes | Yes | Yes | Yes |
| Moderate channel content and reports (future) | Yes | Yes | Yes | No |

Reports and channel-content moderation are not implemented. The owner cannot
leave while still owner; ownership transfer is required first. Any member may
leave. Public directory responses do not reveal membership rosters, invite
tokens, or member counts.

## 3. Product specification and user journeys

### Foundation scope

- Create a Space with a required name and purpose and an optional description.
- Start every Space as private; an owner or administrator may switch it to
  discoverable or private later.
- Let anyone view discoverable Space metadata. Do not expose member-only
  content, rosters, or counts to visitors.
- Let authenticated users request access to discoverable Spaces. Pending
  requests do not grant content access. Owners and administrators approve or
  deny requests.
- Let authenticated invitees join immediately through an active Space invite.
  Invitees always receive the Member role.
- Let owners and administrators review membership, manage roles within their
  authority, and remove members subject to the role matrix.
- Let a member leave. Preserve the owner invariant; ownership must be
  transferred before the owner can leave.
- Create one default `general` channel for new Spaces and backfill existing
  Spaces through the Channels migration.
- Let all active Space members list channels, read history, and send messages.
  Keep channel management to the owner and administrators.
- Archive channels to preserve history while preventing new messages. Permit
  hard deletion only when a channel has no messages.

### Key journeys

1. **Create and configure:** an authenticated user creates a private Space,
   reviews it, then may enable public metadata discovery.
2. **Discover and request:** a visitor browses discoverable metadata, signs in,
   requests access, and sees no Space content until approval.
3. **Invite and join:** an owner/admin shares an active invite. An authenticated
   recipient joins and becomes a Member; rotating/revoking the invite prevents
   future joins but does not remove current members.
4. **Manage membership:** an owner/admin reviews requests and the roster,
   assigns permitted roles, or removes a member. The backend enforces every
   action regardless of UI visibility.
5. **Leave or transfer:** a member leaves; an owner first transfers ownership.

### Explicitly deferred

Structured discussions, moderation reports, resource uploads, search,
notifications, learning content, and AI assistance remain deferred. Private
direct messages are not Space knowledge and must not be indexed as shared
Community content. The UI must not show nonfunctional destinations or sample
content for deferred capabilities.

## 4. Architecture assessment

Keep the Django modular monolith and the current chat contract. The dedicated
`community` Django app contains:

- `Space`: UUID identifier, owner, name, description, purpose, visibility,
  active invite token/expiry, and timestamps.
- `SpaceMembership`: one row per Space/user, role (`administrator`,
  `moderator`, or `member`), and joined timestamp. The Space owner is held in
  `Space.owner` and is treated as the Owner role; do not duplicate the owner
  in the membership table.
- `SpaceJoinRequest`: one request per Space/user, status and review metadata.
  Approval creates membership transactionally; a pending request grants no
  content access.
- `Channel`: a Space-owned channel with a one-to-one `ChatSession`, description,
  creator, archive timestamp, and per-Space unique slug. The conversation
  reuses existing chat messages and notifications; its `ChatSession.owner` is
  not an authorization grant.

Use database uniqueness for membership and request identity. Use transactions
for Space and default-channel creation, invitation rotation, request approval,
role changes, and ownership transfer where multiple records change. The
Channels migration backfills existing Spaces with `general`. Do not copy
Space members into `ChatSessionMember`; direct-chat membership and invitations
remain a separate access path.

Channel list, history, send, and WebSocket boundaries verify current Space
membership against application data. Direct-chat APIs and the optional bridge
exclude channel-backed sessions. The default ASGI consumer rechecks
membership before inbound frames and outbound message events. No
`ChannelMember` model is needed while all Space members share access.

Channel deletion returns a conflict if messages exist. Space deletion returns
a conflict if any channel history exists; empty channel conversations are
deleted with the Space. Ownership transfer updates the owner of linked
conversations without changing the Space-membership authorization model.

The invite is a bearer credential: use a cryptographically unpredictable
token distinct from the Space ID, require authentication to redeem it, keep it
out of API query strings, and never expose it to non-managers. The first
foundation implementation uses one active reusable invite per Space;
rotation replaces the prior token. New deployment migrations must be applied
through the intended environment; never apply them to production or the
tracked local database during development validation.

## 5. Implemented API surface

All management operations require DRF authentication and enforce role checks
server-side. Public reads return only discoverable metadata.

| Endpoint | Responsibility and access |
|---|---|
| `GET /api/spaces/` | Public list of discoverable Space metadata only. |
| `POST /api/spaces/` | Authenticated Space creation; creator becomes owner; private by default. |
| `GET /api/spaces/mine/` | Authenticated caller's owned and active-member Spaces. |
| `GET /api/spaces/{id}/` | Public metadata for discoverable Spaces; private Spaces and member content are hidden from non-members. |
| `PATCH /api/spaces/{id}/` | Owner/admin updates name, description, purpose, or visibility. |
| `DELETE /api/spaces/{id}/` | Owner-only deletion, subject to safe lifecycle checks. |
| `GET /api/spaces/{id}/members/` | Active Space members only; usernames and roles, no email/legal-name fields. |
| `PATCH /api/spaces/{id}/members/{user_id}/` | Owner/admin role change, constrained by the role matrix. |
| `DELETE /api/spaces/{id}/members/{user_id}/` | Owner/admin removes an eligible member; owner/admin self-removal rules apply. |
| `POST /api/spaces/{id}/leave/` | Member leaves; owner must transfer ownership first. |
| `GET /api/spaces/{id}/requests/` | Owner/admin views join requests. |
| `POST /api/spaces/{id}/requests/` | Authenticated non-member requests to join a discoverable Space. |
| `DELETE /api/spaces/{id}/requests/` | Requester cancels their pending request. |
| `POST /api/spaces/{id}/requests/{request_id}/approve/` | Owner/admin approves; membership is created atomically. |
| `POST /api/spaces/{id}/requests/{request_id}/deny/` | Owner/admin denies without granting access. |
| `GET/POST/DELETE /api/spaces/{id}/invite/` | Owner/admin reads, rotates, or revokes the active invitation. |
| `POST /api/spaces/invites/join/` | Authenticated invitee submits token in the request body and joins as Member. |
| `POST /api/spaces/{id}/transfer/` | Owner transfers ownership to an active member. |
| `GET /api/spaces/{id}/channels/` | Active Space member lists channels, including archived channels. |
| `POST /api/spaces/{id}/channels/` | Owner/admin creates a channel. |
| `GET/PATCH/DELETE /api/spaces/{id}/channels/{channel_id}/` | Active member reads channel details; owner/admin edits, archives, restores, or deletes an empty channel. |
| `GET/POST /api/spaces/{id}/channels/{channel_id}/messages/` | Active Space member reads history or sends a message; archived channels are read-only. |
| `WS /ws/spaces/{id}/channels/{channel_id}/` | First-frame token authentication; active Space membership is checked on connection and before delivery. |

Use serializers for new input and output contracts, validate field lengths and
visibility, return non-disclosing `404` responses for inaccessible private
Spaces, and keep public and member payloads separate.

## 6. Implemented frontend scope

- Add a public `/spaces` directory and public metadata route for discoverable
  Spaces. Require sign-in to request access or redeem an invite.
- Add an authenticated "My Spaces" view and a Space creation form.
- Add a Space details/management view for profile, members, requests, and
  owner/admin invite controls.
- Add channel navigation and a message view at
  `/spaces/{id}/channels/{channel_id}`. Reuse the chat message and composer
  components; provide owner/admin create, edit, archive, restore, and empty
  channel deletion controls.
- Add one "Spaces" destination to the existing shell. Preserve Home, direct
  chat, invite, sign-in, and message behavior.
- Follow `.agents/skills/fuego-design/SKILL.md` and the relevant
  design-token, component, responsive, interaction, accessibility, and review
  references. Reuse the current CSS variables and shell primitives; avoid
  dashboard card grids and fake activity.
- Provide truthful loading, empty, error, request-pending, invite-expired, and
  access-denied states. Use visible focus, semantic forms, and keyboard/touch
  operability.

## 7. Implementation roadmap

1. **Space foundation (implemented):** model/migration, private creation,
   discoverable metadata directory, membership, requests, invite lifecycle,
   role checks, owner/admin management, UI, and permission tests.
2. **Channels and participation (implemented):** default `general` channel,
   existing chat message infrastructure, Space-aware REST and WebSocket
   authorization, channel lifecycle, and responsive navigation.
3. **Knowledge preservation:** validate resource/discussion lifecycle,
   attribution, correction, search, and notification policies before models
   or indexing.
4. **Community intelligence:** only after content permissions and data
   boundaries are stable, evaluate contextual summaries and retrieval. No
   generic chatbot or autonomous execution infrastructure.

## 8. Testing and acceptance strategy

- Model tests: defaults, constraints, role changes, owner invariants, invite
  expiry/rotation/revocation, and request lifecycle.
- API permission matrix: anonymous, non-member, requester, member, moderator,
  administrator, owner; include private-resource non-disclosure and public
  metadata minimization.
- Transaction tests: request approval and membership creation; invite joining;
  ownership transfer.
- Migration checks: `makemigrations --check`, fresh test-database migration,
  and rollback behavior review. The channel data migration is intentionally
  irreversible to avoid orphaning conversations. Do not apply migrations to
  the tracked database during development validation.
- Frontend tests: public directory/detail, auth redirect/return, create,
  request/cancel/approve, invite join/expiry, role controls, and failures.
- Full validation: `scripts/validate-fuego.ps1 -Scope all` passed with 56
  backend tests and 12 frontend tests, plus type checking, production build,
  Django system checks, migration consistency, and whitespace validation.
- Browser/accessibility review: desktop, tablet, mobile, 320px width, no
  horizontal overflow, keyboard focus/order, semantic announcements, and
  reduced-motion behavior remains outstanding. Automated checks do not prove
  full WCAG conformance.

## 9. Security, privacy, and remaining risks

- Existing chat hardening now minimizes user payloads, separates invite
  tokens from chat IDs, uses first-frame WebSocket authentication, and
  revalidates the default Channels path before events.
- The optional uWSGI bridge still lacks per-event token/account/membership
  revalidation. This remains open by the user's follow-up choice and must be
  addressed before that bridge is used for private Space content.
- Production TLS/WSS termination, deployment settings, logging, rate limits,
  backups, and operational procedures are not verified.
- Public directory data is limited to Space name, description, and purpose.
  Search or AI retrieval must preserve the same membership boundary.
- New Space invitations are authenticated, seven-day, reusable, revocable,
  and separate from the stable Space identifier. Membership and role checks
  remain server-side.

## 10. Decision log

| Decision | Status |
|---|---|
| Private by default; owner/admin may enable public metadata discovery; content remains member-only | Approved by user |
| Discoverable Space access is request/approval or authenticated invite | Approved by user |
| Four roles; owner/admin permissions as listed above; moderation actions await content/report features | Approved role model; detailed moderation workflow deferred |
| All members share all initial channels; no private channels/ChannelMember in first release | Approved by user |
| Owner/admin-only reusable seven-day invitations, authenticated redemption, revocable and rotatable | Approved by user |
| Reuse persistent chat message streams for channels; defer separate Discussion entities | Approved by user |
| One active reusable invitation per Space; rotation invalidates the previous link | Initial implementation assumption, matching the existing chat invite pattern |
| Community content and public listing have no search, resources, or AI in this slice | Deferred per roadmap |
| Optional bridge event-by-event revalidation | Open; user selected not to implement in this task |
