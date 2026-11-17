# Fuego Product and Development Master

| Field | Value |
|---|---|
| Status | Consolidated strategic draft; detailed capabilities remain proposals |
| Version | 0.5 |
| Updated | 17 November 2026 |
| Product | Fuego |
| Purpose | Single reference for product direction, learning strategy, roadmap, and development guardrails |

This document combines the current Fuego product direction with the practical
AI-in-everyday-work strategy. It is intentionally clear about what is in the
repository and what is a future idea. The high-level direction is
conversation-first; individual features, launch scope, and architecture
decisions still need validation.

## 1. Executive summary

Fuego is a conversation-first technology and learning platform. It starts
with chat and should grow by connecting people, useful knowledge, learning,
and practical work:

**Chat -> Community -> Knowledge -> Learning -> Creation**

The product helps people move from curiosity to understanding, from
understanding to capability, and from capability to creation. It should make
technology understandable, accessible, and useful to more people.

Fuego has three connected dimensions:

- **People:** conversations, communities, relationships, and collaboration.
- **Knowledge:** explanations, resources, discussions, and technical learning.
- **Work:** practical workflows, projects, and real-world outcomes.

Fuego's initial audience is non-technical people eager to enter technology
but unsure where to begin. They are interested in AI's potential but have not
experienced it hands-on; they want to learn along the way and finish by making
something of their own.

AI should connect these dimensions, not define the entire identity of Fuego.
One important broader learning strategy is helping people apply AI to work
they already do. The starting question is:

> What are people doing today, what are they trying to achieve, and where can
> AI meaningfully help?

Python is an important foundation and learning area, but it does not limit
Fuego to programming education. Learning hubs may cover AI foundations,
Python, algorithms, data, machine learning, practical AI, and other topics as
real learner needs are validated.

**Current implementation:** a Django chat backend and React + TypeScript
single-page frontend, including the approved Community Space foundation
(private Spaces, discoverable metadata, membership requests/invites, roles,
ownership management, and shared `general`-first channel conversations).
Knowledge, learning, and AI-workflow capabilities remain proposed or deferred;
see the
[Community implementation specification](./COMMUNITY_IMPLEMENTATION_SPEC.md)
and [Technical Baseline](./TECHNICAL_BASELINE.md) for verified scope.

## 2. Document purpose and status labels

Use this document to align product planning and development. It is not a
claim that every proposed feature is approved or built.

The following labels are used throughout:

- **Verified:** confirmed in the repository inspected for this document.
- **Proposed:** a candidate product or technical direction, not yet committed
  for implementation.
- **Deferred:** intentionally postponed until need, safety, and dependencies
  are clearer.
- **Open:** requires a product or technical decision.

This document is the product reference. The repository implementation,
verification results, and operational findings are recorded separately in
[`docs/TECHNICAL_BASELINE.md`](./TECHNICAL_BASELINE.md); refresh that snapshot
after material code or configuration changes.

## 3. Product identity, vision, and promise

### Product definition

> Fuego is a conversation-first platform that helps people make sense of
> technology, learn from one another, use AI effectively, and turn curiosity
> into practical capability.

### Vision

> Make technology understandable, accessible, and useful to more people.

### Product promise

> Move people from curiosity to understanding, from understanding to
> capability, and from capability to creation.

Fuego should not become a collection of disconnected courses or tool
demonstrations. Conversations, community, durable knowledge, learning, and
practical application should reinforce one another.

### The problem Fuego addresses

People encounter technology and AI in education, work, business, creative
practice, and everyday life. Exposure alone does not ensure understanding or
the ability to apply it. Fuego aims to address connected gaps:

- **Awareness:** unfamiliar terms and claims make technology difficult to
  understand; people may hear that AI is powerful without having a first-hand
  experience of using it.
- **Starting point:** aspiring technology learners may not know where to begin,
  what to learn first, or which tools matter for their goal.
- **Application:** knowing about a tool is different from improving a real
  task or workflow with it.
- **Technical access:** people may want to build but lack programming, data,
  or systems foundations.
- **Confidence:** technology can seem inaccessible to beginners or people
  without powerful devices and paid tools.
- **Opportunity:** learners need practice, collaboration, and ways to
  demonstrate capability by making something, not consuming information
  alone.
- **Knowledge retention:** useful explanations and solutions can disappear
  inside chat histories and fragmented discussions.

Fuego should address these needs as a connected experience rather than
separate products.

## 4. Product philosophy and principles

1. **Conversation comes first.** Chat and natural discussion are the entry
   point, not a compulsory course flow.
2. **Do not turn every conversation into a lesson.** People must remain free
   to ask, share, debate, explore, and connect without being forced into a
   curriculum.
3. **Community creates belonging.** Different experience levels and lived
   experience should be useful to one another.
4. **Knowledge should outlive a conversation.** Preserve useful information
   with context, attribution, and a way to correct it.
5. **Learning should be practical and accessible.** Start with the learner's
   goal and explain technical concepts when they become useful.
6. **AI should increase capability, not dependency.** Keep human judgement,
   creativity, relationships, and accountability central.
7. **Teach work and workflows, not only tools.** Understand the task before
   suggesting AI or automation.
8. **Evaluate outcomes, not output volume or time spent.** A better workflow,
   demonstrated skill, or useful project matters more than generated content.
9. **Respect different paths and paces.** Participation should not require
   enrolment in a formal pathway.
10. **Design for inclusion.** Consider digital literacy, language, device
    capability, connectivity, cost, and disability.
11. **Validate in stages.** Build from evidence and user needs rather than
    speculative feature accumulation.
12. **Human contributions remain valuable.** AI must not erase attribution,
    expertise, or community experience.

## 5. The conversation-to-capability model

The intended product progression is:

1. **Chat:** people ask questions, exchange ideas, and collaborate.
2. **Community:** conversations gather around topics, interests, and shared
   goals.
3. **Knowledge:** useful answers and resources become discoverable and
   reusable.
4. **Learning:** knowledge can be organized into explanations, pathways, and
   practice when that structure adds value.
5. **Creation:** people apply what they learn to tasks, workflows, and
   projects.

This is a product model, not a required linear journey. A user may enter at
any point, skip formal learning, or return to ordinary conversation after
completing an activity.

A repeatable learning loop is:

**Ask -> Discuss -> Discover -> Understand -> Practise -> Apply -> Contribute
-> Build**

Fuego should make it possible for a conversation to lead to a useful resource
or practical learning experience without automatically converting every
message into structured content.

## 6. Community strategy

Spaces are proposed focused environments for a topic, interest, project, or
learning community. Each should have a clear purpose, description, rules, and
onboarding. Avoid creating many empty spaces before there is a community to
support them.

Potential community capabilities include questions and replies, topic
discussions, member profiles, basic roles, moderation and reporting, discovery,
and eventually events or live discussions. These are proposals, not current
features.

### Product inspiration

Study product behaviours, not interfaces or feature lists:

| Reference | Useful behaviour to learn from | Fuego adaptation | Guardrail |
|---|---|---|---|
| Reddit | Topic-centred communities, questions, peer answers | Let people ask and answer within focused spaces; make useful discussions reusable | Popularity is not proof; avoid low-quality volume |
| X Communities | Open conversation and discovery | Make valuable discussions discoverable beyond a user's existing circle | Avoid outrage incentives and engagement farming |
| Substack | Short and long-form publishing connected to contributor relationships | Let useful conversations grow into guides with original context | Do not make access depend on a small set of creators or paid subscriptions |
| Discord | Real-time interaction, channels, roles, onboarding | Organize discussion clearly and help newcomers find relevant spaces | Avoid channel overload and unexplained community jargon |
| Discourse | Structured questions, searchable discussions, marked solutions | Preserve useful knowledge and connect it to learning | Keep entry approachable; do not make all conversation feel like support tickets |

The combination should be coherent, not an attempt to become several existing
products at once.

### Community health

Community safety is a product requirement. Future community design should
consider clear guidelines, spam prevention, reporting, moderation, blocking,
privacy controls, member roles, and transparent enforcement. The exact
moderation model is open.

## 7. Knowledge architecture

Knowledge objects are proposed structured records that preserve useful
information from conversations without assuming every message is educational
content. Examples include:

- Questions and answers.
- Accepted or community-validated solutions.
- Guides, explanations, tutorials, and case studies.
- Learning activities and references.
- Related discussions and source links.

Where appropriate, each item should retain author attribution, source
conversation, date, and correction history. Quality signals may include
references, contributor identity, moderation or peer review, last-verified
date, compatibility information, and corrections. Popularity alone must not
be presented as correctness.

Discovery may include topic and keyword search, related conversations,
learning resources, contributors, pathways, and saved content. Avoid reliance
on a single engagement-ranked feed. Privacy and access permissions must be
preserved when indexing or retrieving content.

## 8. Learning philosophy and pathways

Learning is one layer of Fuego, not the only permitted way to use it. A
learner should be able to move between conversation, explanation, practice,
and independent work at an appropriate depth.

### Proposed pathways

- **AI Awareness:** understand basic concepts, common applications, the
  high-level flow from data and inputs to outputs, limitations, and
  responsible use. Outcome: explain a simple AI flow in everyday language and
  identify where AI may or may not help.
- **AI Fluency:** use AI in meaningful tasks, verify results, and evaluate
  quality. Outcome: complete and assess practical work with AI assistance.
- **AI Building:** learn programming, Python, APIs, data handling, model
  integration, testing, and deployment. Outcome: build and maintain a
  practical AI-enabled solution.
- **AI Mastery and Stewardship:** explore evaluation, architecture, security,
  governance, advanced systems, and responsible deployment. Outcome: reason
  about and develop more complex systems responsibly.

These are flexible routes, not academic levels or prerequisites for community
participation. Non-technical, professional, student, creative, and technical
learners may have different goals.

### Subject hubs and applied work domains

Learning subjects and work domains are related but distinct:

- **Subjects:** AI foundations, Python foundations, algorithms and data
  structures, data analysis, machine learning, AI development, and future
  technical topics.
- **Work domains:** social media, marketing, sales, customer service,
  creative production, business operations, and decision-making.
- **Workflows:** repeatable processes within a domain.
- **Tools:** capabilities that may support a workflow.
- **Projects:** outcomes learners create or improve.
- **Communities:** people who discuss and support these activities.
- **Knowledge resources:** information the community preserves.

One learner could join an AI community, study a marketing pathway, practise a
social-media workflow, and share a campaign project. Shared concepts can be
reused across contexts without duplicating entire curricula.

### Learning content structure

Proposed hierarchy:

**Learning hub -> Pathway -> Unit -> Lesson -> Activity**

A lesson may include objectives, explanations, examples, sources, related
conversations, practical exercises, knowledge checks, and reflection
questions. Activities may include code exercises, research tasks, short
responses, projects, and peer feedback. A learner should be able to discover a
lesson through a conversation and return to that discussion afterward.

The learning cycle is:

**Discover -> Discuss -> Learn -> Practise -> Apply -> Reflect -> Share**

Every significant experience should explain what the learner will understand,
why it matters, where it can be used, what they can practise, how they can
check understanding, and how to share or build on the result.

### Founder hypothesis: first AI learning journey

The initial learning experience may help a beginner move through this sequence:

1. Start with a problem described in everyday language.
2. Broaden it into a general idea or pattern before choosing a tool.
3. Show two related but distinct visual flows:
   - building or adapting a system: select and prepare data, train or adjust a
     model, then evaluate it;
   - using a trained system: provide input and context, receive an output, and
     review it before deciding what to do next.
4. Narrow the broader idea to one specific task or context, map its current
   steps, and identify where AI could help or where it should not be used.
5. Improve and test that workflow, then make something tangible that shows
   what the learner understood.

Keep the explanation non-technical and grounded in examples, without implying
that every AI system works the same way. The two flows are connected but are
not one continuous operation: a normal prompt does not necessarily retrain the
model. The exact first problem, pathway, and project remain open; this is a
founder hypothesis to validate with learners.

## 9. AI literacy and responsible use

Fuego should explain what AI can do, how it works at a useful level, where it
is limited, and how to apply it responsibly. It must not become an AI-hype
platform. Distinguish established capabilities, emerging developments,
experimental features, and speculation.

Potential learning areas include:

- Generative and multimodal AI.
- AI-assisted software development.
- Agents and automation.
- Data science and machine learning.
- AI-assisted research.
- Privacy, security, bias, copyright, evaluation, transparency, reliability,
  and human oversight.

### AI limitations to teach

- AI may generate incorrect or fabricated information.
- Outputs require verification and source checking.
- Generated code may be insecure or unreliable.
- Automation may fail on exceptions or changed conditions.
- Sensitive information should not be shared indiscriminately.
- AI does not replace domain expertise, accountability, or human judgement.
- Using AI is not the same as understanding a subject.
- Generated output alone does not demonstrate a learner's competence.

### AI as a learning companion

AI assistance may explain concepts at different levels, help find relevant
resources, generate practice questions, give feedback, or connect related
ideas. It should be optional, disclose uncertainty, cite sources when
appropriate, and distinguish verified material from community opinion. It
must not silently turn unverified discussion into authoritative lessons.

## 10. Practical AI in the work people already do

Fuego should help people improve real tasks and workflows, not merely teach
them to use a tool or write prompts. Start with a recognizable problem and
understand the human work before introducing AI. Not every task should be
automated.

The workflow-first model is:

**Understand the work -> Map the workflow -> Identify opportunities -> Apply
AI -> Evaluate results -> Improve the process**

For each workflow, ask:

1. What is the person trying to achieve?
2. How is the task done now?
3. What is difficult, costly, repetitive, or slow?
4. Which parts need human judgement, creativity, or relationships?
5. Where could AI assist, accelerate, improve, or automate?
6. What tools and skills are required?
7. How will output be verified?
8. How will improvement be measured against the original process?

### Eight-stage practical AI method

1. **Observe** the task as it is currently performed.
2. **Break it down** into stages, inputs, decisions, and outputs.
3. **Identify opportunities** for AI assistance or automation.
4. **Choose a tool** based on the task, cost, privacy, reliability, and user
   capability.
5. **Work with AI** using context, constraints, and examples.
6. **Verify** factual accuracy, quality, privacy, and suitability.
7. **Measure** the outcome against a baseline.
8. **Improve** the workflow using the results.

Possible measures include time, cost, quality, response time, conversion,
customer satisfaction, error rate, or administrative effort. The goal is a
better workflow, not more generated content.

### Practical learning experience

A workflow-centered experience may contain:

1. Situation.
2. Challenge.
3. Current workflow.
4. AI opportunity.
5. Demonstration.
6. Exercise.
7. Evaluation.
8. Discussion.
9. Application to the learner's own context.

Connect experiences to relevant conversations, communities, and resources.

### Proposed work domains

These domains are candidate learning areas. Each needs validation with people
who do the work.

#### Social media and digital presence

- **Work and challenges:** audience building, content planning and creation,
  publishing, engagement, and performance measurement.
- **Possible AI assistance:** ideation, audience research, calendars, draft
  captions and scripts, repurposing, translation, comment categorization, and
  reporting.
- **Human responsibility:** brand identity, originality, cultural context,
  relationships, and final editorial judgement.
- **Skills and practice:** audience and objective definition, format and
  schedule selection, measurement, and evaluation. Example: plan a
  seven-day campaign and explain where AI was useful.

#### Marketing and brand growth

- **Work and challenges:** market and customer understanding, positioning,
  campaigns, channel selection, leads, and performance.
- **Possible AI assistance:** research synthesis, messaging drafts,
  variations, landing-page feedback, email drafting, segmentation support,
  and analysis.
- **Human responsibility:** product truth, strategy, customer understanding,
  brand decisions, and budget accountability.
- **Skills and practice:** connect product, audience, message, channel, and
  outcome. Example: design a campaign within a defined budget and evaluate
  its assumptions.

#### Sales and customer acquisition

- **Work and challenges:** identify prospects, conduct outreach, prepare
  proposals, follow up, handle objections, and maintain relationships.
- **Possible AI assistance:** prospect research, outreach drafts, proposal
  preparation, call summaries, reminders, CRM organization, and forecasting
  support.
- **Human responsibility:** trust, consent, negotiation, relationship
  building, and accountable decisions.
- **Skills and practice:** map the process from enquiry to follow-up and
  identify appropriate assistance without automating sensitive interactions.

#### Customer service and client management

- **Work and challenges:** enquiries, complaints, bookings, updates,
  resolution, feedback, and continuity of service.
- **Possible AI assistance:** draft responses, categorize requests, summarize
  history, find support information, prepare FAQs, and identify recurring
  issues.
- **Human responsibility:** empathy, context, exception handling, sensitive
  decisions, and escalation.
- **Skills and practice:** design a process that handles common questions
  while routing unusual or high-impact cases to a person.

#### Content production and creative work

- **Work and challenges:** research, briefs, writing, photography, design,
  video, presentation, editing, and delivery.
- **Possible AI assistance:** brainstorming, research organization,
  storyboards, script drafts, editing support, transcription, adaptation, and
  production planning.
- **Human responsibility:** taste, authorship, creative direction, originality,
  consent, and rights.
- **Skills and practice:** document where AI contributed and assess the final
  work against the original brief.

#### Business operations and administration

- **Work and challenges:** documents, records, scheduling, reports,
  coordination, and repetitive processes.
- **Possible AI assistance:** drafting, extraction, spreadsheet support,
  summaries, task organization, classification, and workflow automation.
- **Human responsibility:** permissions, exceptions, records accuracy,
  approval, and accountability.
- **Skills and practice:** map the current process and its exceptions before
  automating any step.

#### Data, analytics, and decision-making

- **Work and challenges:** collect, clean, interpret, report, and act on
  operational or customer data.
- **Possible AI assistance:** cleaning support, spreadsheet analysis,
  visualization suggestions, summaries, natural-language queries, and
  anomaly exploration.
- **Human responsibility:** data quality, interpretation, context, and
  decision accountability.
- **Skills and practice:** verify analysis against underlying data and
  distinguish correlation, interpretation, and evidence.

## 11. Proposed practical-work capabilities

These are future options, not first-release requirements:

- **Workflow library:** searchable tasks with the problem, audience, current
  process, AI-assisted process, tools, instructions, examples, risks,
  verification, expected outcome, and related discussion.
- **Guided AI workspace:** contextual instructions, explanations, drafting
  help, templates, references, and evaluation for a defined task. It should
  not be an unrestricted automation system by default.
- **Community playbooks:** practitioner explanations of a process, with
  context and evidence rather than prompt lists alone.
- **Practical challenges:** campaigns, lead workflows, data analysis,
  customer-service processes, or small automations reviewed by peers.
- **Tool discovery:** recommendations based on the job, capability, cost,
  privacy, device, connectivity, and alternatives—not trendiness.

Prefer integrations and guided workflows over rebuilding mature external
products without a validated reason.

## 12. User journeys

These journeys illustrate the intended end-to-end product model. Some Space
foundation flows exist, but these complete journeys are not implemented.

- **Curious beginner:** asks a question in chat, joins a topic community,
  finds an explanation, tries an optional activity, and shares what helped.
- **Working professional:** describes a task, maps the current workflow,
  learns where AI may help, verifies the result, and compares outcomes with a
  baseline.
- **Technical learner:** starts with a practical problem, follows relevant
  Python or AI material, builds a small solution, and gets community
  feedback.
- **Contributor:** answers a question, improves an explanation, links it to
  sources, and may help turn it into a reusable guide.

No learner should be forced through the same route.

## 13. Verified repository baseline

Repository inspected: `fuego/`, including backend, frontend, requirements,
settings, routes, models, and tests. The findings below describe the current
checkout, not a production deployment.

See [`docs/TECHNICAL_BASELINE.md`](./TECHNICAL_BASELINE.md) for the detailed
implementation inventory, verification commands, and open operational risks.

### Verified

- The backend is a Django 6.1.3 project using Django REST Framework 3.18.0,
  Djoser, Django Channels, Daphne, and SQLite as listed in
  [`fuego/requirements.txt`](../fuego/requirements.txt).
- The Django project exposes Djoser authentication under `/auth/` and chat
  endpoints under `/api/`; DRF token authentication is configured.
- The `chat` app defines chat sessions, messages, and membership. API views
  support chat creation, owner-managed membership, invite joining, message
  retrieval, and message creation. Message access checks ownership or
  membership. Channel-backed conversations are excluded from direct-chat
  APIs.
- The `community` app defines Spaces, membership, join requests, Channels,
  external-link Resources, and structured ResourceReferences from channel
  messages. New Spaces receive a `general` channel; existing Spaces are
  backfilled by a data migration. Channel messages reuse chat message storage
  and are authorized by current Space membership. Resource links have
  metadata search and role-aware lifecycle controls; file uploads, private
  storage, text extraction, and RAG are not implemented.
- The ASGI application routes HTTP to Django and WebSockets through separate
  direct-chat and Space-channel consumers. Both authenticate a DRF token from
  the first frame and recheck authorization before frames and message events.
- The normal channel layer is `InMemoryChannelLayer`, suitable for local
  single-process use rather than multi-process production delivery.
- Optional RabbitMQ publishing and a uWSGI WebSocket bridge exist behind
  settings and separate deployment requirements. Treat this path as
  experimental; it is not the default Windows development setup.
- The frontend is React + TypeScript with Vite and React Router, not Vue. It
  contains direct-chat, Space directory/management, and Space-channel routes,
  sign-up/sign-in, invite joining, message history, REST message sending, and
  WebSocket updates. WebSocket credentials are sent in the first frame rather
  than the connection URL.
- Frontend dependencies include Bootstrap CSS bundled locally. Frontend
  tests cover authentication flows; backend tests cover authentication,
  chat access control, invitation joining, and WebSocket behavior.
- A `notes` directory exists but is a placeholder: it has no substantive
  models or views and is not included in the installed Django apps or root
  URL configuration.
- The repository's root README documents a one-command local start using
  `npm --prefix .\fuego\fuego-frontend run dev:all`.

### Risks and incomplete baseline

- **Development-only settings:** `DEBUG` is enabled, `ALLOWED_HOSTS` is empty,
  and CORS is permissive. A development-marked secret key is hard-coded in
  settings. Do not use these settings or commit real secrets for production.
- The optional uWSGI/RabbitMQ WebSocket bridge is excluded from channel-backed
  sessions. For direct chats it authenticates from the first frame but does
  not revalidate token, account, or membership before each forwarded event.
  It is experimental and was not verified against a live uWSGI deployment.
- The database is SQLite and the default channel layer is in-memory; scaling
  and production deployment have not been established here.
- The RabbitMQ/uWSGI path has code and tests but should not be considered
  production-ready without deployment and failure-mode validation.
- This inspection did not establish production hosting, monitoring,
  backup/recovery, formal privacy policy, or operational support arrangements.
  Their status is **unknown**.
- The `notes` app is not a learning-content implementation.

The older planning material mentioned a possible Vue discrepancy. Current
source files and `package.json` verify React + TypeScript, so that discrepancy
is resolved for this checkout.

## 14. Proposed architecture and boundaries

Preserve the working stack unless repository evidence justifies a change.
Prefer a modular monolith over premature service separation.

Potential logical domains, to introduce only when needed:

- Identity and authentication.
- Conversations, chat sessions, and messages.
- Communities, spaces, memberships, and moderation.
- Knowledge resources, references, search, and corrections.
- Learning hubs, pathways, lessons, activities, and progress.
- Work domains, workflows, tools, and practical projects.
- AI integrations, usage controls, and evaluation.

These are design boundaries, not instructions to create every app or model
now. The current Community foundation uses `Space`, `SpaceMembership`,
`SpaceJoinRequest`, `Channel`, `Resource`, and `ResourceReference`. RAG
indexing, embeddings, and retrieval models remain proposals. Other possible
concepts include `LearningHub`, `LearningPathway`, `Lesson`, `Activity`,
`LearnerProgress`, `Workflow`, and `Project`; these remain proposals, not
existing Django models.

Keep API responsibilities aligned with existing conventions. Future endpoint
families for communities, knowledge, learning, progress, and projects are
proposals; inspect existing URLs and permission patterns before selecting
routes.

### AI integration boundary

Keep model providers replaceable. Before adding an AI integration, define
purpose, privacy, retention, cost limits, rate limits, output evaluation,
source handling, and human review. Manage provider secrets outside source
control. Never execute arbitrary AI-generated code in the Django process. If
code execution becomes a validated need, design a separate isolated
environment with explicit resource and network limits.

## 15. Security, privacy, accessibility, and inclusion

Future work must:

- Enforce authentication and permissions at API and WebSocket boundaries.
- Keep private conversations and community content out of unauthorized
  search, recommendations, summaries, and AI retrieval.
- Define consent, retention, deletion, and data-sharing behavior before
  sending user content to external AI providers.
- Teach verification, privacy, consent, copyright, bias, and responsible use.
- Treat AI output as untrusted until checked.
- Make moderation, reporting, blocking, and community rules understandable.
- Use responsive, keyboard-accessible interfaces with readable language and
  adequate contrast.
- Consider low bandwidth, affordable devices, regional context, and
  accessibility needs.
- Avoid requiring a paid AI subscription for foundational learning.
- Provide human escalation for sensitive or high-impact workflows.

The current development settings are not a production security baseline.
Production security settings and WSS termination remain unverified. The
optional uWSGI bridge still needs per-event authorization checks before it
should be considered for deployment.

## 16. Unified roadmap

Phases are a sequence for validation and planning, not a commitment to build
every proposed capability. Each phase should be reviewed before expanding the
next.

### Phase 0 — Repository discovery and product stabilisation

- **Problem:** planning depends on accurate knowledge of a changing codebase.
- **Objective:** record actual functionality, gaps, risks, and user needs.
- **Capabilities/deliverables:** maintain this master document; produce
  `docs/TECHNICAL_BASELINE.md`; inventory current chat behavior, tests,
  permissions, configuration, and deployment assumptions.
- **Dependencies:** none.
- **Outcome/acceptance:** working chat flows can be demonstrated; verified,
  partial, experimental, proposed, and unknown items are separated; security
  and operational gaps are recorded; no rewrite is proposed without evidence.
- **Out of scope:** new learning features, AI integrations, or broad redesign.

### Phase 1 — Reliable chat foundation

- **Problem:** community and learning need dependable conversation primitives.
- **Objective:** stabilize existing chat and preserve its useful behavior.
- **Capabilities:** authentication, chat creation, invitation/joining,
  history, real-time messaging, failure states, responsive usability, and
  appropriate tests.
- **Dependencies:** Phase 0.
- **Outcome/acceptance:** owners and authorized members can use conversations;
  permissions are enforced; messages persist; failures and reconnects are
  understandable; tests cover critical access behavior.
- **Out of scope:** a full social feed, formal learning system, or advanced AI.

### Phase 2 — Community foundation

- **Problem:** people need topic-based belonging and peer support.
- **Objective:** validate spaces and shared-interest discussion.
- **Current status:** the approved Space foundation and initial shared
  channels are implemented. Content moderation/reporting and knowledge
  features remain deferred. See the
  [Community implementation specification](./COMMUNITY_IMPLEMENTATION_SPEC.md).
- **Capabilities:** topic Spaces, membership, descriptions, basic roles,
  onboarding, shared channel conversations, and metadata discovery.
- **Dependencies:** Phase 1.
- **Outcome/acceptance:** a newcomer can find a relevant space, understand
  its purpose, participate safely, and get basic help.
- **Out of scope:** many empty spaces, complex recommendations, and
  monetization.

### Phase 3 — Knowledge preservation

- **Problem:** useful answers disappear or are repeatedly recreated.
- **Objective:** make selected discussions reusable without over-structuring
  chat.
- **Capabilities:** searchable discussions, saved items, structured Q&A,
  marked solutions, referenced guides, attribution, corrections, and links
  back to conversations.
- **Dependencies:** Phase 2.
- **Outcome/acceptance:** users can find and reuse an answer with its context
  and source; permissions remain intact; corrections can be made.
- **Out of scope:** autonomous AI facts, or presenting unverified summaries
  as authoritative.

### Phase 4 — First learning pathways

- **Problem:** people need a route from curiosity to structured practice.
- **Objective:** test a small learning model connected to community.
- **Capabilities:** learning hubs, pathways, units, lessons, objectives,
  activities, simple knowledge checks, progress, and related discussions.
  AI Foundations and Python Foundations are candidates, not fixed launch
  requirements. Favor learning-by-doing with a tangible outcome; the first
  pathway and project still need validation.
- **Dependencies:** Phases 2 and 3.
- **Outcome/acceptance:** a beginner can choose a pathway, complete an
  activity, see meaningful progress, find relevant discussion, and
  demonstrate what was learned through something they make.
- **Out of scope:** a large course catalogue, complex grading, and
  credentials.

### Phase 5 — Practical AI and workflow learning

- **Problem:** people hear about AI but may not know how to apply it to real
  work.
- **Objective:** validate workflow-first learning in one or a few domains.
- **Audience note:** the initial audience may not have a professional
  workflow to improve. Validate beginner-friendly, hands-on AI experiences
  and buildable challenges before selecting the first work domain.
- **Capabilities:** workflow lessons, examples, exercises, community
  playbooks, verification, outcome baselines, and practical challenges.
- **Dependencies:** Phases 3 and 4; evidence from people who do the work.
- **Outcome/acceptance:** a learner can explain the original task, identify
  suitable AI assistance, verify results, and compare the workflow against a
  baseline.
- **Out of scope:** full CRM/marketing tools, advanced automation, or chasing
  trending products.

### Phase 6 — Contextual AI learning companion

- **Problem:** learners may need explanations and guidance at different
  levels.
- **Objective:** test optional assistance grounded in approved resources.
- **Capabilities:** explanations, relevant resource discovery, practice
  generation, feedback, citations where appropriate, and cost/usage controls.
- **Dependencies:** Phases 3-5; privacy and evaluation design.
- **Outcome/acceptance:** assistance is optional, uncertainty is visible,
  source quality can be checked, privacy controls work, and learners can
  complete work without depending on the assistant.
- **Out of scope:** unrestricted agents or automatic publication of AI
  content.

### Phase 7 — Practical building and specialisation

- **Problem:** learners need opportunities to demonstrate independent
  capability.
- **Objective:** connect learning to projects and advanced pathways.
- **Capabilities:** projects, submissions, peer review, Python/API exercises,
  AI integrations, showcases, and more specialized hubs.
- **Dependencies:** Phases 4-6.
- **Outcome/acceptance:** projects map to learning outcomes, demonstrate
  meaningful work, and can receive useful feedback; any code execution is
  isolated and safely bounded.
- **Out of scope:** a cloud IDE or every technical specialization before
  demand is validated.

## 17. Priorities and deferred capabilities

### Current direction

- Keep chat as the first product experience and current foundation.
- Connect people, knowledge, learning, and practical work progressively.
- Treat AI in real workflows as a major strategic pillar, not the whole
  product identity.
- Prioritize non-technical people who want to enter technology but lack a
  starting point, including people curious about AI who have not tried it
  hands-on. Do not assume prior technical or AI experience.
- Let learners understand as they practice and create a tangible outcome.
- Keep other learners and practitioners in scope for the broader platform;
  they are not the initial audience.
- Validate needs before expanding architecture or content scope.

### Decide after Phase 0

- First-release problem, first learning goal, and the tangible thing learners
  should make.
- How the initial audience approaches technology and AI today; validate rather
  than assume specific barriers or preferred tools.
- First community model and permissions.
- Initial learning hub and first work domain.
- Knowledge-resource lifecycle and moderation.
- Search and discovery approach.
- Deployment, scaling, and production security requirements.

### Defer unless evidence changes

- Public algorithmic social feed.
- Creator monetization and paid memberships.
- Certificates.
- Advanced autonomous agents.
- Unrestricted code execution.
- Full collaborative IDE.
- Native mobile applications.
- Complex recommendation algorithms.
- A large catalogue of learning hubs.
- Rebuilding mature marketing, sales, or CRM products.

## 18. Success measures

Measure capability, usefulness, and safety rather than time-on-site alone.

- **Chat/community:** successful conversations, useful replies, onboarding,
  returning contributors, unanswered questions, and moderation outcomes.
- **Knowledge:** search success, reused solutions, cited resources, freshness,
  corrections, and repeat questions resolved.
- **Learning:** activity completion, improved attempts, independent
  problem-solving, ability to explain concepts, and application to real tasks.
- **Practical AI:** ability to identify appropriate use cases, verify output,
  recognize limitations, and improve a measured workflow.
- **Creation:** meaningful completed projects, outcome quality, peer feedback,
  and continued independent work.

Use qualitative learner feedback alongside quantitative measures. Avoid
vanity metrics as the primary definition of success.

## 19. Development standards and task management

Every significant task should record:

- Task ID, phase, title, and status.
- User problem and learning objective.
- Dependencies and expected files or modules.
- Acceptance criteria and required tests.
- Size estimate where useful.
- Evidence of completion and remaining issues.

Suggested statuses: `NOT_STARTED`, `IN_PROGRESS`, `BLOCKED`, `IN_REVIEW`,
`DONE`.

A task is `DONE` only when acceptance criteria are met and relevant
verification evidence is recorded. Keep the roadmap and this master document
as product references; implementation status must be verified from code and
tests.

## 20. Fuego Master Development Instruction

Use this section independently as the operating instruction for a
development assistant:

> You are working on Fuego, a conversation-first technology and learning
> platform. Before proposing or implementing product changes, read
> `docs/FUEGO_MASTER.md` and read `docs/TECHNICAL_BASELINE.md` if it exists.
>
> Fuego starts with chat and should connect community, knowledge, learning,
> and practical creation. The current repository is a Django chat backend
> with a React + TypeScript frontend. Verify this and all other assumptions
> against the current code. Distinguish verified, incomplete, experimental,
> proposed, deferred, and unknown capabilities.
>
> Follow the validated roadmap. Preserve working behavior and established
> conventions. Make small, focused, type-safe changes; avoid unnecessary
> rewrites, dependencies, services, and scope expansion. Do not implement
> later-phase capabilities just because they are described here.
>
> Consider permissions, privacy, security, accessibility, responsiveness, and
> performance. Treat AI output as untrusted, explain its limitations, and
> never execute arbitrary generated code in the main application. Do not
> expose secrets or private conversations.
>
> For each task, explain the user problem, relevant product layer and phase,
> repository findings, approach and trade-offs, learning concepts, tests,
> verification results, and documentation updates. Do not claim completion
> without evidence. If a requirement conflicts with this document or the
> implementation, explain the conflict and ask for a decision rather than
> inventing one.
>
> Update this master document only when an approved product or architectural
> decision materially changes the direction. Keep it aligned with actual
> implementation and record unresolved decisions explicitly.

## 21. Open decisions and assumptions

| ID | Decision | Current position |
|---|---|---|
| D-001 | Product identity | Fuego; current repository and README use this name |
| D-002 | Core product direction | Conversation-first; Chat -> Community -> Knowledge -> Learning -> Creation |
| D-003 | Initial audience and first release scope | Audience decided: non-technical aspiring technology learners who are new to hands-on AI and want to learn by making. Founder hypothesis: explain simply how data is used to build/adapt a model and how a trained model turns input into output, then help learners narrow a broad problem to a specific use and make something. Validate with learners; exact first problem, pathway, project, and scope remain open. |
| D-004 | Initial community model and public/private defaults | Approved for the foundation slice: private by default; owner/admin may enable discoverable metadata-only listings; content stays member-only; discoverable Spaces accept approval requests or authenticated invites; roles are owner/admin/moderator/member; all initial channels share Space membership; channels reuse chat message streams and separate Discussions are deferred. Detailed moderation/report workflow remains open. |
| D-005 | First learning pathway | Founder hypothesis: begin with non-technical AI Awareness, distinguish model preparation from model use, then narrow a problem into a practical use and tangible project. Validate before committing; Python Foundations remains a candidate pathway. |
| D-006 | First practical AI work domain | Open; select through user research |
| D-007 | Knowledge object lifecycle and verification | Proposed; moderation and correction process needed |
| D-008 | Search and discovery | Open; preserve permissions and avoid popularity-as-truth |
| D-009 | AI provider, privacy, budget, retention, and evaluation | Deferred until use case and controls are defined |
| D-010 | Production database, channel layer, hosting, and operations | Unknown; assess against actual deployment needs |
| D-011 | Monetization and creator economics | Deferred |
| D-012 | Progress, credentials, and project assessment | Open; prioritize demonstrated capability over completion badges |
| D-013 | MCP or other planning automation | Not required for the initial roadmap; consider only for a validated workflow |

### Assumptions

- The product direction in this document is a planning baseline, not evidence
  of completed product features.
- The repository snapshot is the source for implementation claims.
- AI-workflow examples and proposed categories need practitioner and learner
  validation.
- Research links are starting points, not automatic evidence for curriculum
  claims.

## 22. References and source material

The following references were carried forward from the source planning
documents as product-inspiration or research starting points. Verify current
content, publication details, methodology, and relevance before using them to
support educational claims.

### Community product inspiration

- Reddit: <https://www.reddit.com/>
- X Communities: <https://help.x.com/en/using-x/communities>
- Substack features: <https://substack.com/features>
- Discord Community Onboarding FAQ:
  <https://support.discord.com/hc/en-us/articles/11074987197975-Community-Onboarding-FAQ>
- Discourse, “Your Community as Your AI Knowledge Layer”:
  <https://blog.discourse.org/2026/02/your-community-as-your-ai-knowledge-layer/>

### AI, education, and regional context

- Stanford AI Index 2026:
  <https://hai.stanford.edu/ai-index/2026-ai-index-report>
- McKinsey QuantumBlack insights:
  <https://www.mckinsey.com/capabilities/quantumblack/our-insights>
- Caribou:
  <https://caribou.global/>
- Kenya Ministry of Information, Communications and the Digital Economy:
  <https://www.ict.go.ke/>
- UNESCO AI resources:
  <https://www.unesco.org/en/artificial-intelligence>

The supplied McKinsey, Caribou, Kenya, and UNESCO URLs are broad landing
pages, not necessarily the exact reports named in the source material. The
McKinsey page did not respond during this consolidation check, and UNESCO
rejected automated retrieval; neither result establishes that the sites are
unavailable to ordinary readers. Confirm the exact source before citing a
specific report or strategy.

### Source material and repository documentation

This document consolidates the supplied Fuego master-direction draft and the
supplied practical-AI-in-workflows proposal. Their read-only snapshots remain
unchanged. Current setup instructions are in the [root README](../README.md)
and [Fuego frontend guide](../fuego/fuego-frontend/README.md).

## 23. Final product definition

Fuego begins with people talking. It should help them find one another,
understand technology, use AI meaningfully, preserve useful knowledge, and
learn together. As the platform grows, conversations can lead to resources,
resources to learning, and learning to practical work and creation.

Fuego should help people become more capable without making technology feel
inaccessible or making AI the authority. Its value comes from connecting
people, knowledge, and work in a coherent experience.

**Start with a conversation. Leave with capability.**
