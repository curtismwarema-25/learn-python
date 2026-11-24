# Fuego Knowledge Preservation Policy

## Foundation scope

The first knowledge-preservation slice makes only explicitly selected messages
from Space channels reusable. Direct-chat messages, join requests, drafts,
profile data, and external link targets are not eligible. A channel message is
eligible when it belongs to the requested Space and the requester is an active
Space member.

Any active member may preserve a message. The preserved item is owned by the
Space, inherits the Space membership boundary, and records the preserving user
and timestamp. The message author remains the source author. A private direct
message can never enter this collection.

## Traceability and lifecycle

`PreservedKnowledge` stores a one-to-one foreign key to the original
`ChatSessionMessage` and points to an immutable `KnowledgeVersion` snapshot.
The snapshot stores the authoritative reusable content, while the source
message, channel, author, and timestamps remain traceable.

Preservation can be withdrawn by the preserver or a Space owner/administrator.
Withdrawal is a tombstone state, not physical deletion, so the source and
audit relationship remain traceable. A withdrawn item may be explicitly
preserved again.

Channel messages support explicit editing by the author or a Space owner or
administrator. Before an edit, the previous content is captured in an
immutable `ChatSessionMessageRevision`; this source history is deliberately
separate from curated `KnowledgeVersion` history. Active preserved knowledge
is marked `needs_review` after a source edit and excluded from normal
knowledge search until an authorized correction reactivates it.

Message deletion is a soft delete recorded with `deleted_at` and
`deleted_by`. Deleted messages are hidden from ordinary channel retrieval and
discussion search. Dependent active or needs-review knowledge is marked
`source_deleted` and excluded from active knowledge search. Withdrawn
knowledge remains withdrawn. Members can inspect source revisions through the
explicit revision-history endpoint, including for deleted messages.

## Search and corrections

Space search returns active preserved messages as `knowledge` results when
the content type is `all` or `knowledge`. In an `all` search, the preserved
message replaces its ordinary discussion result so the same source appears
only once. `discussions` remains backward-compatible and includes ordinary
messages; active preserved messages carry their knowledge metadata there.
Withdrawn records are never returned as knowledge results.

Search uses the current version snapshot and excludes historical versions.
Corrections create the next version number transactionally, retain the prior
content, record the correction author and optional explanation, and move the
stable knowledge record's current-version pointer. Search marks versions
after V1 as corrected. A source-message edit does not silently rewrite a
snapshot; the source revision remains available for comparison. Source
deletion similarly does not turn stale content into verified knowledge.

Space deletion is blocked while any preserved item exists. Account deletion,
channel-specific ACLs, moderation review, and permanent purge are unresolved
product/operations decisions and are intentionally not silently inferred by
this foundation. Soft-deleted source rows and revisions are retained because
the current audit policy does not define a purge window.

## Data model and authorization

`PreservedKnowledge` contains:

- the owning `Space`;
- the protected one-to-one source `ChatSessionMessage`;
- `preserved_by`, status, and preservation timestamp;
- withdrawal actor and timestamp.

Every list, preserve, and withdraw operation resolves the Space role live.
Preserved content is returned only to current members of that same Space.
Cross-Space message IDs and non-channel messages return not found, avoiding
disclosure of private conversation existence.

This model is deliberately separate from the link-only `Resource` model.
External embedding providers, extraction, global semantic search, and AI
retrieval remain out of scope until source eligibility, retention, consent, and
deployment decisions are approved. The local indexing and embedding
foundation is documented below.

## Indexing foundation

Only active `PreservedKnowledge` with a current `KnowledgeVersion` and a
non-deleted source message is indexed. Ordinary conversation messages never
enter this pipeline automatically. Version content is normalized with Unicode
NFKC and collapsed whitespace, then split into deterministic word-boundary
chunks of at most 1,000 characters with a 120-character overlap target.

`KnowledgeIndexingJob` records one materialization attempt per knowledge and
version, including pending, indexed, failed, and obsolete states, retry count,
timestamps, and failure details. `KnowledgeIndexChunk` stores the normalized
content, offsets, chunk position, Space, knowledge, version, source message,
source author, channel, and source timestamp. Chunks are rebuildable database
materializations; immutable knowledge and source histories remain authoritative.

Lifecycle operations invalidate indexed chunks transactionally: corrections
obsolete the prior version, withdrawal and source deletion obsolete all
materializations, and source edits invalidate active knowledge before marking
it for review. Retrieval rechecks active knowledge, current-version identity,
non-deleted source state, indexed job status, and Space membership on every
request, so stale rows cannot become eligible through a missed event. SQLite
is the initial store; an embedding provider or vector index can later consume
the retrieval interface without changing these lifecycle rules.

## Embedding and asynchronous processing

The default embedding provider is the deterministic local `fake` provider.
Provider selection, model name, dimensions, and batch size are configured with
`FUEGO_EMBEDDING_*` settings. No API key is required and tests make no paid
provider calls. External providers are intentionally not implemented until an
explicit adapter, credential policy, transmission review, and consent decision
are approved; any future adapter must receive only eligible chunk text and
must not log that text or credentials.

`KnowledgeChunkEmbedding` stores vectors separately from chunk content and
records provider, model, dimensions, and generation time. A provider/model
change creates a new materialization and makes the previous embedding
obsolete. The database vector-store contract returns candidate chunk IDs and
similarity scores without exposing vectors through the public API.

Celery processes durable indexing jobs with bounded retries. Local development
uses eager execution; deployment may run a normal Celery worker against an
approved broker/backend configuration. No Redis or other new infrastructure is
required by this foundation. Eligibility is checked again immediately before
embedding persistence, protecting against withdrawal, source deletion, or
version changes during provider work.
