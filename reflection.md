# Build reflection

2026-10-02. Local implementation; no human review recorded.

## Surprising errors and corrections

- Windows cp1252 stdout rejected the Unicode arrow in the startup message and prevented the server from starting. Changed the console message to ASCII. Reusable lesson: startup logging must not depend on terminal Unicode support.
- A test used SQLite's transaction context manager as if it closed the connection. Windows refused temporary database cleanup. Explicitly closed the handle; all seven tests then passed. Reusable lesson: a SQLite `with connection` block manages a transaction, not connection lifetime.
- Initial mobile illustration wrapped to three lines and overlapped its annotation. Preserved the memo width and increased the art container height. Screenshot inspection caught a defect invisible to API tests.
- The ambient Python interpreter lacked two existing repository test dependencies; the repository virtual environment had them. All 105 tests passed there. Reusable lesson: check the repository interpreter before diagnosing unrelated test failures as regressions.
- Bare `@eNN` browser references were parsed incorrectly by PowerShell. Semantic locators and quoted selectors worked. Reusable lesson: quote browser references in PowerShell.

## Outcome and review

Product clarification: user chose "One account button; authenticate when posting" and requested an evolving geographic/history-based feed rather than Latest/Most relatable controls. Preserved authentication, consolidated the header label and separated versioned feed ranking from search. Geographic/personalized ranking remains explicitly planned. Current Firebase documentation also showed why older blanket claims about missing geo/text support are unsafe: Enterprise now documents those capabilities, with geo marked Preview; SQL Connect is PostgreSQL-backed.

Navigation correction: "make search a seperate tab imo and feed should be primary". Made Feed the initial view and moved search to its own tab/panel. Preserved the search query across switches while keeping it out of feed requests. Browser checks confirmed the full feed returns after searching and keyboard tab navigation works.

Further owner correction: "make it CLI types and the fontface also ... not full exact, but it should look like that". Replaced the mauve/serif direction with IBM Plex Mono and a charcoal/olive terminal-inspired treatment. Kept conventional web controls and the existing feed-first flow. The earlier palette was not accepted; do not treat a successfully implemented visual direction as user approval.

Owner correction: "i dont want the intro section, or the categories one" and "we should seach with title ... partial search should be possible"; the original contrasting palette was also rejected. Revised the product to open directly to an uncategorized feed with title-only substring search and a tonal mauve/pearl palette. Lesson: a polished landing page and editorial contrast were assumptions, not an accepted direction; keep the requested reading workflow primary.

Measured: seven app tests, 105 repository tests, six learning-directory validations, browser read/write/report flows, desktop/mobile screenshots. No skill or kernel changes proposed or accepted. No unreviewed knowledge was promoted to `knowledge/`. Human visual and architecture review remains pending.


Latest layout correction: the supplied reference replaces the separate Search tab with header search and a popular-thread sidebar. Removed decorative terminal path and heading rather than adding more introductory content. Kept the terminal visual direction and added an original SVG mascot. Lesson: terminal styling should support the reading workflow; decorative shell text was not requested functionality. Verified 14 app tests and desktop/mobile navigation. Visual acceptance remains for the user to judge.


Owner simplified the layout: remove the public Account button, visible Feed heading and Popular threads sidebar. Let it out is the sole header action and authenticates when needed. Signed-in account/sign-out access remains in the footer. The reading column is centered; header title search remains. This supersedes the preceding sidebar design.


Production verification correction: SQLite's row object accepts positional access, while psycopg's configured `dict_row` does not. The feed and authentication rate limiter therefore failed only on PostgreSQL. Use named-column access in shared database paths and add a real PostgreSQL integration test before the next schema-sensitive release. A graceful health response also made a missing Vercel environment variable diagnosable without crashing the entire function.
