# Fuego AI Requirements

Status: requirements only. No AI provider, generated workflow, or semantic
retrieval feature is approved by this document.

## Purpose

AI should strengthen Fuego's existing path from conversation to knowledge,
learning, and practical work. It should help people understand technology,
make community knowledge useful, practise skills, accomplish real work, and
connect individual productivity with trusted community context. AI is an
assistive capability inside Fuego's Spaces, knowledge, learning, and future
work tools—not a disconnected chatbot or an authority that replaces people.

## Future use cases

Every use case must preserve the user's current Space and content permissions.
The following are product requirements, not implementation commitments.

| Area | User problem and journey | Inputs / output | Fuego feature, permission, and human control | Success criterion |
| --- | --- | --- | --- | --- |
| Community discussions | A member needs a clear answer from a long discussion. They ask in a channel, review a concise response, and open the cited messages. | Authorized channel context; draft answer with citations and uncertainty. | Channels and source-message links; member access only; no automatic posting. | Less time to find an answer without unsupported claims. |
| Knowledge discovery / RAG | Useful preserved knowledge is hard to find across Spaces. A member searches, inspects sources, and follows the original context. | Permission-filtered indexed chunks; cited synthesis. | Knowledge versions, indexing, embeddings, search; Space membership required. | Every material claim is traceable to currently eligible sources. |
| Learning assistance | A learner is stuck on a lesson. They ask for a hint, try it, and compare the explanation with the lesson and discussion. | Lesson, learner request, permitted discussion context; hint or explanation. | Enrolled pathway and linked Space access; learner controls whether to use the hint. | Improved activity completion and understanding, not merely longer sessions. |
| Research and analysis | A user needs to compare sources or frame a question. They gather authorized material, review a structured draft, and correct it. | Selected sources and explicit question; comparison, gaps, and citations. | Knowledge and resource library; read permissions; export requires review. | Clearer decisions with visible evidence and limitations. |
| Content creation | A creator wants a first draft of a lesson, resource, or discussion summary. They edit it before publishing. | User-provided brief and selected sources; editable draft. | Learning authoring and knowledge attribution; creator permission; publishing always explicit. | Faster drafting without loss of attribution or quality review. |
| Social media and marketing | A team adapts an approved idea for different channels. They review tone, claims, and variants before external use. | Approved source and audience/channel brief; variants and disclosure metadata. | Future planning/workspace tools; workspace role; external publication requires approval. | Reusable, accurate drafts with no unapproved external action. |
| Sales and customer relationships | A user needs a consistent response from approved product/customer context. They review and send it manually. | Authorized CRM or workspace records; suggested response and next step. | Future customer workflows; record-level permissions; sensitive actions require approval. | Faster response while preserving privacy and accountability. |
| Project and business operations | A team wants status, risks, and next actions from project material. They verify the summary and assign work. | Authorized project updates; draft status and actions. | Future projects/tasks; team role checks; assignments and changes are confirmed by a person. | Fewer missed actions and clearer ownership. |
| Repetitive task assistance | A user repeats a predictable transformation. They preview the result, adjust it, and run it on selected records. | Explicit inputs and bounded tool; preview and result log. | Future workflow runner; least privilege, limits, approval for writes. | Reliable time saving with recoverable failures and audit history. |

## Architecture requirements

1. Keep model providers behind a provider-independent interface. Provider,
   model, region, retention, and feature configuration must be explicit and
   replaceable.
2. Assemble context from typed, attributed records. Context must carry Space,
   channel, source message, knowledge version, lesson, and user identity where
   applicable.
3. Enforce authorization before retrieval and again before returning or using
   context. A vector match is never an access grant.
4. Treat embeddings as replaceable materializations of eligible immutable
   knowledge versions. Handle provider/model changes, retries, deletion, and
   invalidation without changing business records.
5. Require source attribution for retrieval-based output, with enough metadata
   to open the authorized original and identify version freshness.
6. Separate conversation context, task context, retrieved context, and tool
   permissions. Do not infer tool authority from a chat prompt.
7. Run expensive work asynchronously with durable status, idempotency keys,
   retry limits, dead-letter handling, and operator-visible failure state.
8. Add per-user, per-Space, and platform usage limits, cost estimates, budget
   alerts, and provider outage handling before production rollout.
9. Log model/provider, request class, authorization decision, source IDs,
   latency, token/cost estimates, tool calls, approvals, and failures while
   minimizing sensitive content and supporting retention/deletion policy.
10. Make privacy boundaries explicit for training use, telemetry, exports,
    deletion, and third-party providers. External providers are opt-in per
    deployment and must not receive unauthorized private content.

## Human control and safety

- Generated text must be visibly labelled as generated and must not appear as
  verified knowledge without human publication.
- Users retain control over publishing, sending messages, changing records,
  assigning work, and all external actions.
- Sensitive, irreversible, financial, moderation, or externally visible
  operations require explicit confirmation and an auditable approval record.
- AI must never bypass Space membership, channel access, withdrawn knowledge,
  deleted sources, or current version eligibility.
- Outputs must be reviewable, editable, rejectable, and attributable to their
  inputs. Uncertainty, missing evidence, and conflicts should be visible.
- Prompt injection and malicious source content must be treated as untrusted
  data; source text cannot grant tools or permissions.
- Provide abuse controls, rate limits, report paths, incident logging, and a
  rollback/disable switch for each AI capability.

## Deferred implementation roadmap

These phases must not start until the corresponding non-AI product surfaces
are usable and their permissions are tested:

1. **AI boundary and evaluation contract:** provider interface, policy checks,
   audit schema, budgets, redaction, and representative evaluation sets.
2. **Permission-aware retrieval:** local retrieval over current indexed
   knowledge with citations and source-opening tests; no generated answers yet.
3. **Learning assistance:** opt-in hints and explanations grounded in lesson
   context, with learner feedback and evaluation.
4. **Community and research assistance:** cited discussion summaries and source
   comparison with explicit review and no automatic posting.
5. **Drafting assistance:** editable lesson/resource/content drafts with
   provenance and human publication.
6. **Bounded workflows:** approved tools, previews, confirmations, retries,
   and audit logs for one narrow productivity workflow at a time.

Each phase requires privacy review, permission tests, quality evaluation,
failure recovery, usage limits, and a rollback plan before expansion.
