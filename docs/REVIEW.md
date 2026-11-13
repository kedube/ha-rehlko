# Integration and sidebar reviews

Two passes are recorded here, newest first.

# Review — 2026-11-13: translations, usability, best practices

Scope: the whole integration and panel, read for missing features, performance, security, bugs
and Home Assistant conventions, plus translation of both halves into the most widely used
languages. The panel was inspected in a browser this time (headless Chrome against the local
preview: light and dark themes, desktop and 390 px phone widths, every tab).

## Findings addressed

| Severity | Finding | Change |
| --- | --- | --- |
| High | English only. The panel had no localization at all: every label, unit and enum value was hardcoded. | Ten languages for the integration and the panel (en, de, es, fr, it, ja, nl, pl, pt-BR, zh-Hans). Catalogues in `scripts/locales/` generate `translations/`; the panel bundles `frontend/src/locales/` and reads enum values from the integration's translations through `hass.localize`. |
| High | The documented command for reading the app credentials printed nothing on macOS (GNU-only `sed` syntax), and pasting a value with the `.env` file's quotes failed sign-in. | The docs use a portable `grep -E`; the setup form strips matching quotes. |
| Medium | Every generator created an "Outside" area and every transfer switch a "Utility room" area in the user's home, in English regardless of language. | `suggested_area` removed. The account device is registered as a service. |
| Medium | The action editor showed raw option slugs (`unloaded_full_speed`): `services.yaml` named selector translation keys that did not exist. | Added the `selector` translations, and one for the controller choice. |
| Medium | The panel showed °F and psi to everyone, ignored the user's number format, clock and time zone, and read the API's offset-less timestamps in the browser's zone while the integration reads them in the server's. | The panel follows the user's profile and unit system, and parses offset-less times in the server's zone. The schedule editor round-trips in the zone being shown. |
| Medium | Starting the engine and deleting the schedule took one click with no confirmation. | Both ask first (keyboard- and screen-reader-friendly dialog). |
| Medium | A generator whose details request failed logged a warning on every poll. | Logged once, and once on recovery. |
| Medium | Feed items announced in the ten seconds before an account reload were not yet saved, so the reload announced them again. | The seen-store is flushed when the entry unloads. |
| Low | The power-flow arrows had no size and never rendered; the layout read as four unrelated boxes. Home load was the generator's load, shown even on utility power. | One row — utility, home, generator — with the active connection lit. Load is shown only while the generator runs. |
| Low | Warning and status text used fixed colours with poor contrast on dark and custom themes. | Status colours come from the theme; coloured text is mixed with the theme's text colour; banners use normal text on a tint. |
| Low | The sidebar menu button was always shown; tabs were not keyboard-navigable; long lists were cut at 100 rows with no way to see the rest; overview cards left a third of the width empty. | Menu button only where the sidebar is hidden, arrow-key tabs with `tabpanel` semantics, "Show more", full-width cards, a link to the device page. |
| Low | Calendar event titles, the firmware summary and the sidebar title were hardcoded English; calendar logic compared against the English title. | Rendered from the translations in the server's language; the last run is identified by its event id. |
| Low | Signal-strength sensors were free text. Blank generator/load names were sent to the service. `http` was used without being declared. Setup and options fields had no help text. | Enum sensors with translated states; blank names rejected; `http` declared; `data_description` added. Coordinator failures carry translation keys. |
| Low | The panel called the PIM a "Power interface module". | It is Kohler's Programmable Interface Module. |

## Checked and left alone

- **Concurrent refreshes.** A write's immediate refresh cannot overlap a scheduled poll and
  double-fire power events: Home Assistant 2026.2 serializes coordinator refreshes itself.
- **Secrets.** No credential, token or API key is committed; captures and `.env` files are
  ignored. Token and API requests refuse redirects. Diagnostics redact identity, location,
  network and free-text fields (a few more network identifiers were added defensively).
- **Authorization.** The panel, its WebSocket commands and the domain actions require an
  administrator; the panel renders all service text through Lit, which escapes it.

## Second pass, same day

The owner answered the first pass's recommendations; these were acted on.

| Request | Outcome |
| --- | --- |
| Create catch-all entities disabled | Done. They are registered, listed on the device page and not updated or recorded until enabled. |
| Per-account entity IDs | Done: `{entry id}-{generator id}-{key}`. Config entries move to minor version 2 and existing entities are migrated, keeping their entity IDs and history. |
| Trim the panel's snapshot | Done. The activity log, notifications, maintenance notes and entity list are sent to a subscriber only when they change. Measured on sample data at the caps (300 events, 100 notifications): 144.8 kB for the first snapshot, 4.4 kB for an unchanged poll. |
| Energy (kWh) sensor | Done, as an estimate: the load is integrated between polls (trapezoidal), restored across restarts, and not bridged across gaps in the readings. |
| Remove generators that leave the account | Done, conservatively: after three consecutive account readings without the generator, and never when the account lists nothing at all. |
| Panel editors for load-module and PIM settings | Done on the Profile tab: a switch for on/off settings, and a dialog for name and value. Read-only settings and unreachable generators show plain values. |
| Password stored properly, out of logs and diagnostics | Verified and tightened. It lives only in the config entry. Tests now drive every sign-in and API failure at debug level and assert that no password, client secret, API key or token reaches a log line, an error message, diagnostics or the panel. That test found the account ID in diagnostics, now redacted. Token and credential objects no longer print their contents, log lines no longer carry the account's email, and Reconfigure no longer sends the stored secret and API key to the browser. |
| Remote fault reset | **Not possible.** Every API call in app 1.6.202610 was mapped to its verb; none resets a fault. The app's "Clear Alerts & Reset" is a checklist for the mode switch on the generator. The panel's misleading "resettable at generator" label, drawn from `canRemoteResetFault`, was removed. |
| Multi-factor sign-in | **Not added; reported accurately instead.** The app signs in through Okta's hosted page and contains no multi-factor screens; the tenant is Okta Identity Engine and advertises one-time-code grants, but whether Rehlko's app client may use them cannot be read from outside, and no homeowner account is known to use multi-factor. A refused password sign-in (`mfa_required`, `access_denied`) is now reported as refused, not as a wrong password. Building the one-time-code flow needs an account that has it enabled to test against. |
| Firmware installation | Excluded at the owner's request. |

## Still open

- **Brand images** were added afterwards from Rehlko's Brand Portal
  (`custom_components/rehlko_energy/brand/`, built by `scripts/build_brand_images.py`): the
  symbol as the icon and the horizontal logo, in midnight blue with white versions for dark
  themes — the same artwork Home Assistant's own Rehlko integration uses. The portal states no
  terms of use; its guidelines document describes it as branding material for Rehlko's
  customers. Home Assistant shows local brand images from 2026.3; this was not checked in a
  running 2026.3, because the test environment is 2026.2.
- **Manufacturer photographs are redistributed in the bundle** (four KOHLER product images in
  `frontend/src/assets/`). Their source is recorded there; they are not covered by the Apache
  licence. The owner is deciding whether to keep them.
- **Repair issues** for conditions such as an expiring cellular plan are not raised.

## Verification

Run against Python 3.13.7, Home Assistant 2026.2.3 with its 20260128.6 frontend package, and
Node 26.13.1. The cloud is replaced with test responses throughout.

- **215 Python tests passed**, 87% statement coverage. New coverage includes Home Assistant set
  to Spanish end to end (entity name, calendar event title and firmware summary come out
  translated), the sidebar title per language, translation structure and placeholders for every
  language, log-once availability, the unload flush, quoted credentials, the unique-ID
  migration, stale-device removal, the energy sensor, snapshot trimming over a real WebSocket,
  and credential-leak checks on logs, errors, diagnostics and the panel.
- **89 frontend tests passed**; ESLint, TypeScript and the production build are clean and
  `npm audit` reports no vulnerabilities. New coverage includes language selection and
  fallback, enum names from `hass.localize`, metric conversion, time-zone handling across
  daylight-saving changes, the confirmation dialogs, keyboard tabs, paging, merging trimmed
  snapshots, and the load-module and PIM editors.
- `python3 scripts/build_translations.py --check --strict` passes: all nine catalogues are
  complete (429 of 429 texts each), and every panel locale has all 170 messages.
- Ruff lint and format checks pass.
- The Release workflow (added after this review, see the README's Releases section) passes
  `actionlint`, and its shell steps were run against a throwaway repository with a stand-in for
  the GitHub CLI: first release, minor and major releases, a run with nothing new, a publish
  that fails after the tag was pushed, and the branch moving during the checks. It has not run
  on GitHub.
- The panel was viewed in headless Chrome at 1280 px and 390 px, light and dark, in English,
  German, French, Italian, Polish, Japanese and Simplified Chinese.

## Remaining limits

- Translations were written by the same model that wrote the code and checked mechanically
  (complete, placeholders intact, no stale keys) and by reading; none has been reviewed by a
  native speaker. Alert names, notification text and generator names come from Rehlko's service
  untranslated. European Portuguese and Traditional Chinese fall back to English.
- Accounts with multi-factor sign-in cannot use the password grant this integration relies on.
- Everything in the first review's limits still holds: no live account or generator was used,
  and hassfest and the HACS action have not been run locally.

# Integration and sidebar review — 2026-11-12

The integration has a reasonable foundation: asynchronous I/O, Home Assistant's shared HTTP
session, typed config-entry runtime data, coordinator-backed entities, unique IDs, device
relationships, reauthentication, and a self-contained Lit panel. The main problems were
failure handling, permissions, lifecycle coverage, and incomplete development tooling.

## Findings addressed

| Severity | Finding | Change |
| --- | --- | --- |
| High | The sidebar exposed raw account, address, and device payloads to every authenticated user. Domain services also bypassed entity permission checks. | The panel, its WebSocket commands, and domain services require an administrator. Automations remain supported; entity controls retain Home Assistant's entity permissions. |
| High | Optional frontend dependencies could leave static serving uninitialized, permanently skipping panel registration during that run. | `panel_custom` is a required dependency; it initializes Home Assistant's frontend, HTTP and WebSocket components. Registration is idempotent. |
| High | A failed device-details request retained old telemetry while leaving actions and entities available. | Track the success of each generator's details request, mark affected entities unavailable, disable controller actions, and label stale data in the panel. |
| High | An activity history larger than the 400-ID cache repeatedly announced evicted historical events. | Compare and remember the newest bounded window. A 600-event regression test verifies that unchanged histories stay quiet. |
| High | Critical/high advisories affected development tools including Happy DOM, Vitest, Tinypool and Vite. | Update supported tools and the lockfile. Override Minimatch to its patched release; remove the override when upstream tools adopt it. The final npm audit reports no known vulnerabilities. These tools are development dependencies. |
| Medium | A failed initial feed request seeded an empty history, causing a later successful request to announce historical items as new. Malformed alert payloads could be treated as cleared alerts. | Only process feeds successfully fetched during that poll; validate list responses and retain the prior feed after failures. |
| Medium | Concurrent notification updates could replace each other's changes because the API writes the full settings object. | Serialize settings reads and writes and merge against the latest confirmed state. |
| Medium | Navigating away before a subscription completed could leak it; connection replacements and subscription failures were mishandled. | Track pending subscriptions, release late completions, replace connections cleanly, show errors, retry, and clear timers on disconnect. |
| Medium | A failed maintenance-note action erased the draft; Home Assistant's structured error objects were hidden. | Preserve unsuccessful drafts, display service error messages, validate schedule inputs, restore failed notification toggles, and prevent duplicate submissions. |
| Medium | Several platforms only discovered generators during initial setup. | Discover buttons, events, calendars, selects, datetime and firmware entities after new generators or required details appear. |
| Medium | Controller-definition requests accepted arbitrary device/serial pairs. | Require a loaded entry, a generator on that account, and a serial reported by that generator. |
| Medium | Redirects could forward the app's custom API-key header. Token rate limits could request unnecessary reauthentication. | Disable redirects for API and token requests; classify redirects and HTTP 429 as transient connection failures. Validate token response shapes and expiry values. |
| Medium | Calendar recurrences drifted after short months and could shift local exercise times across daylight saving changes. | Preserve the original monthly day and recur in Home Assistant's local timezone. Use exclusive calendar query boundaries. |
| Low | No working local preview existed: `npm run dev` referenced a missing configuration file. | Add a localhost preview that imports the production bundle, with sample standby, running, offline, stale, fault and empty states. Actions are simulated. |
| Low | The panel lacked a sidebar menu control, scroll containment, and several form labels. Unknown power source appeared as utility power. | Add the Home Assistant menu event, scrolling, focus styles and labels; show unknown power as unknown. |
| Low | Unrelated Home Assistant entity changes caused full panel rendering. Cloud polling could create an unbounded number of simultaneous HTTP requests. | Render on panel data, connection or language changes; limit API requests to six concurrently per account. |
| Low | Diagnostics included free-form notes/messages and names that may contain personal information. Documentation incorrectly claimed MIT licensing and complete app parity. | Redact those diagnostic fields and align the documentation/package metadata with the existing Apache-2.0 license and implemented API surface. |

## Verification

Tests run against Python 3.13.7, Home Assistant 2026.2.3 and its 20260128.6 frontend package.
Frontend checks run under Node 26.13.0. The real cloud is replaced with test responses.

Final results: **129 Python tests passed**, **83.83% integration statement coverage**,
**20 frontend tests passed**, and **zero known npm vulnerabilities**. Ruff, ESLint,
TypeScript, translation generation and the production build passed.

- Integration setup, reload and unload; entities created for generators added after startup.
- Sidebar registration, option changes, account removal, static JavaScript serving, and a live
  initial snapshot through Home Assistant's HTTP/WebSocket test servers.
- Administrator authorization, read-only user rejection, subscription cleanup, controller
  ownership checks, and config-flow account identity checks.
- Telemetry failures, feed deduplication, malformed API/token responses, redirect handling,
  HTTP 429, concurrent notification writes, and calendar recurrence behavior.
- Frontend DOM interactions, subscription races, error/retry states, stale controls, failed
  drafts, notification rollback, and rendering the exact production JavaScript bundle.
- Ruff lint/format checks, TypeScript, ESLint, translation generation, production build,
  and npm dependency audit.

CI now selects the actual Home Assistant 2026.2 test harness and uses Python 3.14 for its
separate latest-version job. Frontend CI builds before testing the production bundle and runs
when the bundled JavaScript changes.

## Remaining limits

- Cloud authentication and generator commands have not been exercised against a live account
  or physical generator. The private API, app credentials, product-specific behavior, and
  delayed controller updates still require that validation. Passing mocked tests does not
  establish vendor compatibility or successful physical operation.
- Local verification covers Home Assistant 2026.2.3. The latest-version CI job has been
  configured, but was not executed against a second Home Assistant release in this session.
- No browser was connected for visual inspection. DOM and production-bundle tests passed,
  but actual desktop/mobile rendering still needs a browser check.
- Calendar projections use Home Assistant's configured timezone. Generator sites in a different
  timezone need separate site-timezone support before their schedules can be assumed accurate.
- Event history is intentionally bounded: 400 IDs are remembered per event/notification feed,
  and at most 25 new items per feed are announced in one update. This is not a complete cloud
  history archive.
- The panel's Profile tab displays peripheral parameters. Parameter writes and generator
  naming are available through entities/services; they do not have dedicated panel editors.
- This custom integration has not been certified at a Home Assistant quality-scale tier;
  statement coverage remains below the 95% target for Silver.

## Panel URLs

Installed integration: `/rehlko-energy` on the same origin as Home Assistant. Sign in as an
administrator, configure an account, and enable the sidebar option.

Local sample preview: run `cd frontend && npm run dev`, then open
`http://127.0.0.1:5173/frontend/dev/index.html`. It uses the production bundle and never sends
commands to the cloud.

## Home Assistant references checked

- [Custom panels](https://contributors.home-assistant.io/frontend/custom-ui/panel/)
- [Panel registration implementation](https://github.com/home-assistant/core/blob/dev/homeassistant/components/panel_custom/__init__.py)
- [WebSocket authorization decorators](https://github.com/home-assistant/core/blob/dev/homeassistant/components/websocket_api/decorators.py)
- [Integration quality scale](https://contributors.home-assistant.io/core/quality-scale/)
