# Abuse Your Manager

An unofficial office watercooler. Public reading, authenticated writing, randomly assigned public aliases. A feed-first local MVP with a terminal-inspired interface: IBM Plex Mono, warm charcoal, muted olive accents and thin borders.

## Run

Python 3.11+:

```powershell
cd abuse-your-manager
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python app.py --port 5050
```

Open **http://127.0.0.1:5050**. The app binds to loopback only. No API keys or cloud accounts are required. The default database is `instance/aym.sqlite3`, created on first launch and ignored by Git.

For an existing Python environment: `python -m pip install -r requirements.txt`, then `python app.py`.

## Included

- Feed opens immediately, with partial-title search in the header. Body text is excluded from search. Read and open shareable stories without signing in.
- **Let it out** is the only header action and authenticates when needed. Feed ranking is server-owned, versioned and cursor-paginated, with freshness and bounded vote support. Geographic and history-based personalization are planned, not active.
- Create an account with a private login and a password of 12+ characters. Receive a persistent random alias. No email collected.
- Publish stories, reply, add/remove a “same here” vote, and report stories after signing in.
- SQLite persistence locally and PostgreSQL in production, scrypt password hashes, opaque server-side sessions, write protections and bounded inputs.
- Five fictional starter stories, visibly labeled Example; no fabricated engagement.
- Responsive desktop/mobile layouts, native accessible dialogs, keyboard focus states, reduced-motion support and local fonts.
- Operator CLI to inspect reports and hide/restore stories.

## Review the design

- [Architecture and HLD](docs/ARCHITECTURE.md) — implemented system, data model, write flow, boundaries and limitations.
- [Standalone HLD diagram](docs/hld.svg) — open directly in a browser.
- [Architecture decisions](docs/DECISIONS.md) — choices, alternatives and consequences.
- [Verification](docs/VERIFICATION.md) — test commands and observed results.
- [Production plan](docs/PRODUCTION-PLAN.md) — database comparison and staged regional/personalized feed architecture.
- [Desktop preview](desktop-preview.png) and [mobile preview](mobile-preview.png).

## Tests

```powershell
python -m unittest discover -s tests -v
node --check static/app.js
```

Tests create isolated temporary databases; they do not touch your stories.

## Operator review

```powershell
python moderate.py reports
python moderate.py hide 3
python moderate.py restore 3
```

Hidden stories disappear from the feed and detail API; new replies/votes/reports are rejected. Reports are not automatically adjudicated. The CLI assumes a trusted operator. It reads `DATABASE_URL` when set, otherwise the local SQLite file; never paste the production URL into shell history.

## Configuration and limits

`AYM_SEED_DEMO=0` disables starter stories when creating a fresh SQLite database. `DATABASE_URL` selects PostgreSQL and is required on Vercel. Use a TLS-enabled transaction-pooler URL for serverless traffic. `AYM_HTTPS=1` enables Secure cookies and HSTS.

## Deploy

The repository is ready for Vercel's Python runtime. Provision PostgreSQL, apply `migrations/001_initial.sql`, then set `DATABASE_URL`, `AYM_HTTPS=1`, and `AYM_SEED_DEMO=0` in Vercel. Deploy a preview first and verify `/api/health`, public feed/search, account creation, posting, and sign-out before promoting it to production. Never commit `.env` files or connection strings.

Aliases are pseudonyms, not a promise of untraceability. The operator can associate accounts with contributions. Password recovery and self-service deletion are not implemented. Never use a work password.

## Assets and references

IBM Plex Mono is locally hosted under SIL Open Font License; license text is in `static/fonts/`. Earlier DM Serif Display and DM Sans assets remain bundled but are no longer loaded. Framework security decisions follow the [Flask security documentation](https://flask.palletsprojects.com/en/stable/web-security/) and [Werkzeug password utilities](https://werkzeug.palletsprojects.com/en/stable/utils/#werkzeug.security.generate_password_hash); see `docs/sources.jsonl` for claim mapping.
