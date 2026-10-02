# Architecture decisions

Date: 2026-10-02. Status: implemented for local review; human review pending.

These are reasoned design choices, not claims that a particular stack is universally best. External facts are linked in the HLD and source register.

| ID | Decision | Why / consequence | Alternative and revisit trigger |
|---|---|---|---|
| ADR-001 | Flask + Waitress, vanilla browser UI | One runtime, no frontend build, real server authorization and persistence. Works on the existing Python/Windows environment. More manual UI state management than a component framework. | React/Next.js if app complexity or team conventions justify a frontend toolchain. |
| ADR-002 | Local SQLite with WAL and foreign keys | No cloud setup; transactional writes; straightforward backup and inspection. Single persistent host, limited write concurrency. | Postgres when measured write contention or multiple hosts become necessary. |
| ADR-003 | Public reads, authenticated mutations | Matches the requested browse-first experience. Server checks apply even if the UI is bypassed. Replies, votes and reports also require an account. | Anonymous voting increases manipulation risk; not chosen. |
| ADR-004 | Private login + password; random persistent alias | No email or real name is needed. Public persona is separate from credentials and stable across sessions. Password recovery is absent and the UI says so. | Managed identity if recovery and anti-abuse justify external dependencies; email/OAuth would collect additional identity. |
| ADR-005 | Opaque server-side session tokens | Expiry and logout revocation are enforceable. Hashes of tokens are stored, not usable bearer tokens. Adds a database lookup. | Self-contained JWTs complicate immediate revocation; unnecessary here. |
| ADR-006 | Same-origin JSON mutation API | Custom-header requirement, Origin checks and SameSite cookies reduce browser CSRF risk without a separate form-token flow. Assumes no permissive CORS. | Reassess if adding cross-origin clients or form POST endpoints. |
| ADR-007 | Text-only stories, topic taxonomy, no employee/company directory | Keeps the first product focused on experiences. No image uploads, searchable target profiles or identity fields. Identifying prose can still appear. | Add media only with upload isolation and moderation capacity. |
| ADR-008 | Human report queue, trusted local moderation CLI | A real persisted report path without exposing an admin interface. No automatic punishment from report counts; avoids simple brigading takedowns. | Admin UI with roles and audited actions before operating a public community. |
| ADR-009 | Per-account write limits, per-address auth limit | Stops simple accidental floods and slows basic abuse. Not a comprehensive bot defense, particularly across accounts or proxies. | Edge limits and shared counters at internet launch. |
| ADR-010 | Editorial office-stationery design | DM Serif Display + DM Sans + typewriter metadata; paper, ink, rust and sage; original memo illustration. Implements the request for a distinct look. | Tune after human review and observed mobile use; avoid adding decorative clutter. |
| ADR-011 | Local font assets and zero analytics | No font-provider request at runtime, no trackers, fewer external failures. Slightly larger repository. Fonts retain OFL licenses. | Add measurement only with explicit privacy/retention decisions. |
| ADR-012 | Labeled fictional seed stories | Makes the opening experience reviewable without pretending there is a community. No seeded votes or replies. | Turn off seeding with `AYM_SEED_DEMO=0` for an empty installation. |
| ADR-013 | Real database counts and idempotent vote state | Unique vote key prevents double-counting; setting the same state twice is safe. Correlated count queries are simple at this scale. | Cached counts or aggregation when profiling identifies feed queries as a bottleneck. |

## Revision following owner feedback — 2026-10-02

ADR-010's original paper/rust/sage direction is superseded by a tonal mauve, pearl and lavender palette. The hero, ticker and sidebar are removed; the page opens directly to the feed. Patterned avatar tiles and subtly layered cards provide visual character without strongly contrasting section colors.

ADR-007's category taxonomy is no longer exposed in the product. Category navigation, labels and composer selection are removed. The existing database column and optional API filter remain for compatibility, and new posts default to General. No destructive migration is needed.

ADR-014: search uses escaped literal substring matching against titles only. Partial words and phrases work; body-only matches are excluded. SQLite LIKE supports ASCII case-insensitive matching; full Unicode case folding or fuzzy search is not claimed. Regression assertions cover partial words, mixed case, a fragment spanning words, body-only exclusion and literal wildcard escaping.

## Further visual revision — terminal-inspired

The owner requested CLI-like colors and type, without making the site an exact terminal replica. This supersedes the mauve/pearl theme: IBM Plex Mono replaces the serif/sans pairing, with dark charcoal surfaces and muted olive highlights. Bracketed sort controls, path-like metadata, a static cursor motif and a slash search prompt supply the terminal cues. Normal web forms, native dialogs and visible action buttons remain. No backend or search behavior changed.

## Feed as primary navigation

Owner requested a separate Search tab. Feed now opens by default, with no search input or query filtering. Search has its own panel and blank-query prompt, keeps its query across tab switches, and retains partial-title matching. Both panels use the same post rendering and API but independent query rules; in-flight list responses are invalidated when switching. No new route or backend service is required.

## Questions intentionally left for launch review

Updated owner direction: one Account button, authentication at posting, and no Latest/Most relatable controls. Feed policy is now server-owned and versioned (`freshness-support-v1`) through `/api/feed`; stable snapshots preserve scrolling order and recheck hidden content. Search remains a distinct endpoint. Regional and history-based ranking are the target, not implemented claims. [Production plan and database comparison](PRODUCTION-PLAN.md) recommends managed PostgreSQL; no provider has been provisioned or migration executed. The existing SQLite decision applies only to local development.

1. Is the audience a closed beta or the open internet? That changes abuse controls and moderation staffing.
2. Should account recovery use optional personal email, recovery codes, or a managed provider?
3. What retention/deletion policy should apply to accounts, reports and infrastructure logs?
4. Who reviews reports, how quickly, and how are appeals handled?

None of these blocks local use. They should be resolved before representing the service as ready for public operation.


## Header search and popular threads

The latest reference supersedes the separate Search tab: use a broad header search, default feed, and a Popular threads sidebar (below the feed on mobile). Remove the decorative path and Off the record heading. Preserve terminal-inspired typography and muted colors. Use an original SVG coffee mug with a crooked tie as the logo.

Popular threads ranks visible posts by votes plus distinct repliers, with recency as the tie-breaker. Repeated replies by one account do not inflate ranking. With no engagement, explicitly describe the list as recent threads to explore. Title-only literal substring search remains unchanged. Managed PostgreSQL justification is now directly in ARCHITECTURE.md; this is a proposal, not a completed migration.


Owner simplified the layout: remove the public Account button, visible Feed heading and Popular threads sidebar. Let it out is the sole header action and authenticates when needed. Signed-in account/sign-out access remains in the footer. The reading column is centered; header title search remains. This supersedes the preceding sidebar design.

## Mobile composer and optional Google sign-in

The composer dialog now uses the mobile viewport width explicitly and permits every grid/form child to shrink, preventing intrinsic input width from pushing the dialog beyond an iPhone viewport. Google Identity Services is an optional sign-in path; server-side ID-token verification uses the configured web client ID, stores no Google profile fields, and maps the stable Google subject to the existing random-alias/session model. Private login remains available. The Google script is loaded only after the account dialog opens and only when `GOOGLE_CLIENT_ID` is configured.

## Optimistic votes and replies

Votes and replies update the in-memory post cache and existing DOM immediately. The client sends the PostgreSQL mutation in the background without refetching the feed or thread. Failed writes roll the optimistic state back; failed replies also restore the draft. This keeps the interface responsive while preserving the database as the source of truth. The client does not maintain an offline write queue, so a failed request is never presented as permanently saved.

## Full terminal palette

The earlier muted olive treatment is superseded. The active UI now uses near-black surfaces, phosphor green text and borders, square controls, and a subtle scanline texture. Amber is reserved for errors, pending state, and the mascot's tie. IBM Plex Mono and the existing reading layout remain.

## Editorial grid revision

The phosphor terminal palette is superseded by the owner's grid-system reference. The interface now uses warm paper texture, black display headlines, vermilion structural lines, staggered feed blocks, and hard-edged controls. IBM Plex Mono remains for metadata and body copy, while headings use a heavy system sans face. The reference's blue was intentionally replaced with vermilion.
