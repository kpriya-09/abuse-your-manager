# Verification record

Date: 2026-10-02. These are observed local results, not production guarantees.

## Header search and popular threads revision

Supersedes the dedicated Search tab layout below. Verified broad header search, immediate feed, removal of the decorative path/heading, and the coffee-mug SVG logo at 1440 x 1000 and 390 x 844. Partial-title query `MEET` returns the matching thread; Back to feed restores all five examples. Popular-thread links open the public detail dialog. Mobile has no horizontal overflow, and browser errors were empty. Screenshots refreshed.

All 14 app tests pass, including real-activity popularity, distinct repliers, zero-activity fallback and hidden-post exclusion. JavaScript syntax, all 105 repository tests and six learning-directory validations pass. Database justification is included directly in the HLD; no production database was provisioned.

## Feed-first revision checks

### Server-owned feed foundation

13 app tests pass after introducing `feed.py` and `/api/feed`. New checks cover rank decay, deterministic ties, snapshot pagination despite changed timestamps, suppression of newly hidden posts, invalid/expired cursors, independent search, and public identity filtering. JavaScript syntax, all 105 repository tests and all six learning validations pass. Browser read-back shows one Account button, no Latest/Most relatable controls, a populated feed, a working partial-title Search tab, and authentication prompted by Let it out. Desktop/mobile previews refreshed. This is a global baseline, not a verified geographic or personalized feed.

### Dedicated Search tab

Verified Feed is selected on initial load and the search field is absent from its visible controls. Search for `meet` returns the matching title in the Search panel. Returning to Feed restores all five starter posts; switching back (including ArrowRight keyboard navigation) preserves the query and result. Desktop/mobile screenshots were updated, mobile overflow check returned false, and browser errors were empty. JavaScript syntax, 105 repository tests and six learning validations passed again. No API changes in this revision.

### Subsequent terminal-style revision

Replaced the visual theme and font with warm charcoal, muted olive and locally hosted IBM Plex Mono. Visually inspected 1440 x 1000 desktop, 390 x 844 mobile, and the mobile signup dialog. Mobile overflow check returned false; `MEET` still selected the matching story; the posting CTA opened the signup gate. No browser page errors were reported. JavaScript syntax check, 105 repository tests and all six learning validations passed. This revision did not change the API. The eight app tests from the previous revision remain the latest backend test run.

After the owner's design/search correction, **8 app tests passed**, JavaScript syntax validation passed, and all **105 repository tests** plus all six learning-directory validations passed again. Browser search for `MEET` returned the title containing `meeting`; searching `spreadsheets`, present only in a story body, returned the empty state. The intro, topic sidebar, category badges and composer category field were removed. Desktop and mobile previews were refreshed with the tonal palette. These results supersede the earlier UI-specific checks below; earlier lifecycle checks are retained as history.

## Original automated checks

| Check | Result |
|---|---|
| `python -m unittest discover -s tests -v` inside this project | **7 tests passed** |
| `node --check static/app.js` | **Passed** |
| `python scripts/brain.py validate --all` at repository root | **All 6 learning directories passed** |
| `.venv/Scripts/python.exe -m unittest discover -s tests -v` at repository root | **105 tests passed** |

The first repository test run used the ambient Python environment and reported four missing-dependency errors (`openpyxl`, `reportlab`). Re-running with the repository's existing `.venv` resolved all four without changing repository code.

App tests cover public reads and unauthorized mutations; API identity privacy; persistent aliases across login and app recreation; logout token revocation; invalid credentials; CSRF rejection; malformed input and contact-detail screening; idempotent voting; replies; duplicate reports; hidden stories; literal search and SQL injection strings; write rate limits; and labeled seeds with zero fabricated engagement.

## Browser checks

Used `agent-browser` with Chrome at **1440 × 1000** and **390 × 844**.

- Loaded the page, local fonts and all five starter stories with no account.
- Opened the posting gate, created a synthetic account and received a random alias.
- Continued from signup to the composer, published a story, and opened its detail URL.
- Added a reply, voted once, and observed the count become one.
- Filed a report and read it back through `python moderate.py reports`.
- Hid the synthetic post through the CLI; read back its hidden state, confirmed absence from the public feed and a **404** for its detail API.
- Signed out and opened `/post/1`; the story remained public and the reply CTA requested sign-in.
- Chose “Small victories” on mobile; the feed contained the matching story only.
- Checked mobile document width: no page-level horizontal overflow.
- Inspected desktop and mobile screenshots; fixed logo wrapping, signed-in header crowding and mobile memo overlap.
- Browser error command reported no page errors in the checked flows.

Synthetic browser-test account and contributions were removed after verification. Starter stories remain untouched. Screenshots: [desktop](../desktop-preview.png), [mobile](../mobile-preview.png).

## Limits of these results

No public deployment, load test, penetration test, continuous moderation, password recovery, or assistive-technology certification was performed. Current coverage does not prove every browser, concurrent interaction, or abusive-content case. See the HLD for launch work.
