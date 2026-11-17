# Fuego Community Implementation Specification

**Status:** Spaces, Channels, and the link-resource foundation are implemented; migrations are pending on the tracked local database. File uploads remain deferred.
**Product authority:** [Fuego Master](FUEGO_MASTER.md), especially §§5–7, 13–17, 21  
**Technical evidence:** [Technical Baseline](TECHNICAL_BASELINE.md) and current source  
**Scope:** Spaces, shared channels, Space link resources, metadata search, and
structured channel references are implemented. File uploads, structured
discussions, semantic search, notifications, and AI remain later milestones.

## 1. Current-state assessment

The verified application is a Django 6.1 / Django REST Framework backend with
`chat` and `community` apps, Django Channels WebSockets, SQLite, and a React +
TypeScript frontend. The `community` app contains Space, membership, request,
Channel, Resource, and ResourceReference models and APIs. Separate Discussion
models and uploaded-file storage are not implemented.

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
| Product boundary | Spaces, channels, link resources, metadata search, and structured channel references are implemented. Do not add placeholder destinations or imply that file uploads or AI retrieval exist. |

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
| Create a Space link resource | Yes | Yes | Yes | Yes |
| Edit or archive own resource | Yes | Yes | Yes | Yes |
| Edit any resource (not only own) | Yes | Yes | No | No |
| Restore own resource | Yes | Yes | Yes | Yes |
| Restore any resource (not only own) | Yes | Yes | No | No |
| Archive any resource (not only own) | Yes | Yes | Yes | No |
| Permanently remove resource content (retain tombstone) | Yes | Yes | No | No |
| Moderate channel content and reports (future) | Yes | Yes | Yes | No |

Reports and channel-content moderation are not implemented. Resource
moderation is limited to the archive permission above. The owner cannot leave
while still owner; ownership transfer is required first. Any member may leave.
Public directory responses do not reveal membership rosters, invite tokens,
or member counts.

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
- Let active Space members add and find external link resources. Search only
  the resource title, description, and URL; do not fetch previews or introduce
  tags, folders, or a separate search service.
- Let creators edit, archive, and restore their own resources; moderators may
  archive any resource; owners/admins may manage any resource and remove its
  content.
- Preserve deleted-resource identity as a minimal tombstone so existing
  channel references remain understandable. A Space with active or archived
  resources cannot be deleted until those resources are removed.
- Let members reference existing resources from channel messages through a
  separate relation. Do not duplicate links as message attachments or expose
  resource references through direct-chat APIs.

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

Uploaded documents/images, structured discussions, moderation reports,
notifications, learning content, and AI assistance remain deferred. Resource
search is limited to metadata and is not semantic retrieval. Private direct
messages are not Space knowledge and must not be indexed as shared Community
content. The UI must not show nonfunctional destinations or sample content
for deferred capabilities.

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
- `Resource`: a UUID-identified Space link with title, description, creator,
  active/archived/deleted lifecycle, URL, and timestamps. Deleted resources
  clear their descriptive content and URL while retaining a minimal
  Space-scoped tombstone.
- `ResourceReference`: a unique message-to-resource relation. The channel API
  verifies that both objects belong to the same Space and that newly
  referenced resources are active.

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
deleted with the Space. Space deletion also returns a conflict while active
or archived resources remain. Ownership transfer updates the owner of linked
conversations without changing the Space-membership authorization model.

Resource list/detail/create/update/archive/restore/delete operations are
scoped to the URL Space and require current membership. Link URLs accept only
HTTP/HTTPS without embedded credentials; Fuego never fetches the destination.
All URL-bearing output is returned only to an active member. Metadata search
uses the application database, with no external search engine.

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
| `GET/POST /api/spaces/{id}/channels/{channel_id}/messages/` | Active Space member reads history or sends a message; POST accepts up to 20 optional `resource_ids`, each of which must identify an active Resource in the same Space. Archived channels are read-only. |
| `GET/POST /api/spaces/{id}/resources/` | Active member lists/searches Space links or creates a link. Archived resources are available through the status filter to their creator and authorized moderators/managers. |
| `GET/PATCH/DELETE /api/spaces/{id}/resources/{resource_id}/` | Active member reads a Space-scoped resource; PATCH updates metadata or lifecycle status according to creator/moderator/manager permissions. DELETE is owner/admin-only, clears resource content, and retains a tombstone. |
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
- Add `/spaces/{id}/resources` and `/spaces/{id}/resources/{resource_id}` for
  member-only link discovery, search, creation, metadata editing, archive,
  restore, deletion, and tombstone display.
- Allow the channel composer to select existing Space links; render references
  as links to the original Resource. Direct messages remain unchanged.
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
3. **Link-resource foundation (implemented):** Space-scoped links, metadata
   search, creator/moderator/manager lifecycle controls, deletion tombstones,
   and structured channel references.
4. **Secure file resources (deferred):** select a private storage provider,
   deployment configuration, allowlist, size limit, content validation, and
   protected download path before adding uploads. Current Django settings have
   no media storage or private download service.
5. **Knowledge retrieval (future):** update the approved RAG architecture only
   after supported content extraction, opt-in/eligibility, and a production
   data plan are reviewed. Private direct messages remain excluded.

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
- Current validation: `scripts/validate-fuego.ps1 -Scope all` passed with 62
  backend tests, 13 frontend tests, frontend type checking/build, Django
  system checks, migration consistency, and Git whitespace checks.
- Browser review: the resource library was inspected with a local browser
  fixture at desktop and mobile widths. Full 320px, keyboard, screen-reader,
  reduced-motion, and WCAG conformance reviews remain outstanding.

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
