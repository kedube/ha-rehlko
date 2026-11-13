# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## Unreleased

## [1.00] - 2026-11-13

### Added

- Translations for German, Spanish, French, Italian, Japanese, Dutch, Polish, Brazilian
  Portuguese and Simplified Chinese, covering the integration (setup, options, entities, states,
  actions, errors) and the sidebar panel. Catalogues live in `scripts/locales/`; the build
  script generates and validates every language.
- The panel follows each user's language, number format, clock, time zone and unit system
  (°C and kPa on metric installations), and names enum values with the integration's own
  translations. The sidebar title and calendar event titles use Home Assistant's language.
- Confirmation before starting an exercise or deleting the schedule; "Show more" for long
  activity and notification lists; a link from the panel to the generator's device page;
  keyboard navigation between tabs.
- Translated dropdowns for the exercise mode, frequency and controller in the action editor,
  and field help in the setup and options dialogs.
- Wi‑Fi, cellular and transfer-switch signal strength are enum sensors with translated states.
- Brand images: Rehlko's icon and logo, with white versions for dark themes, built from the
  files on Rehlko's Brand Portal. Home Assistant 2026.3 and later show them for the
  integration; 2026.2 shows its placeholder.
- An **Energy produced** sensor (kWh), estimated from the generator's load between polls and
  kept across restarts, for the Energy dashboard.
- Load-module and PIM settings can be switched, changed and renamed from the panel's Profile
  tab.
- Devices of generators that leave the account are removed once they have been missing from
  three consecutive account readings.

### Changed

- Setup asks only for your email and password. The Energy Mgmt. app's own client ID, client
  secret and API key are built into the integration and are no longer saved with the account.
  A form for entering them by hand appears only if Rehlko refuses them, and **Reconfigure**
  keeps a section for them. An entry that holds a copy of the same values drops it the next
  time it loads.
- Versions are numbered `MAJOR.NN` from 1.00 (1.01 … 1.99, then 2.00), and releases are
  published by the repository's Release workflow.
- Catch-all diagnostic entities are created disabled. They are still listed on the device
  page; enable the ones you want.
- Entity unique IDs include the account, so a generator shared with two configured accounts no
  longer collides. Existing entities are migrated and keep their IDs, names and history.
- The panel's subscription sends the activity log, notifications, maintenance notes and entity
  list only when they change. With a full activity log (300 events, 100 notifications) an
  update measured on sample data drops from about 145 kB to about 4 kB.
- Reconfigure no longer sends the stored client secret and API key to the browser; leave those
  fields empty to keep them.
- The panel's power flow is one row — utility, home, generator — with the active source's
  connection highlighted. Generator load is shown only while the generator runs.
- The panel uses Home Assistant's theme variables for cards and status colours, so custom and
  dark themes apply; warning and error banners keep readable text on any theme.
- The sidebar menu button shows only where Home Assistant hides its sidebar.

- Authentic manufacturer generator images, selected by model with labeled representative
  images for other models. Images ship in the panel bundle and preserve their aspect ratios.
- Model and light/dark theme selectors in the local preview.

### Fixed

- After the host restarts, the account details and notification settings are read on the first
  poll. They used to wait until the machine had been up for fifteen minutes, which left the
  notification switches missing after a reboot, and the activity feeds could be read twice.
- The firmware update's summary passes Home Assistant's validation: it reads "Released:
  2026-11-01. Scheduled installation: …" in every language.
- No deprecation warnings on Home Assistant 2026.10: devices are looked up, linked and removed
  in the way newer versions expect, and sign-in no longer uses a retired aiohttp helper.
- A password sign-in that Rehlko's sign-in service refuses (for example because the account
  requires multi-factor authentication) is reported as such, not as a wrong password.
- Diagnostics no longer include the account's ID. Log lines name the integration, not the
  account's email address. Credentials and tokens are excluded from object representations, so
  they cannot reach a log or traceback by accident.
- The panel no longer labels alerts "resettable at generator" from a flag that means the
  opposite and that the homeowner API cannot act on.
- Devices no longer create "Outside" and "Utility room" areas in every home; the account device
  is registered as a service.
- A generator whose details request keeps failing is logged once, and once more when it
  recovers, instead of on every poll.
- Announced feed items are saved when an account unloads, so a reload within the ten-second save
  delay cannot fire the same events twice.
- The panel reads the API's offset-less timestamps in the server's time zone, as the integration
  does, so times are right when the browser is in another zone.
- The panel's flow arrows had no size and never rendered; overview cards now use the full width.
- Blank generator and load names are rejected instead of being sent to the service.
- Initialize panel dependencies before registering its JavaScript route; recover subscriptions
  on reconnect and display connection failures. Add a working local sample preview.
- Restrict raw account WebSocket data and domain actions to administrators; validate controller
  ownership and prevent credentials from following HTTP redirects.
- Disable controller actions on failed telemetry, deduplicate long feeds correctly, preserve
  feed history across failures, serialize notification writes, and discover new generators
  across all platforms.
- Preserve failed note drafts, restore notification toggles after errors, add sidebar navigation
  and scrolling, avoid unrelated renders, and correct calendar recurrence drift.
- Replace the inaccurate SVG generator drawing and invented hardware/colour effects with
  unmodified product imagery; keep operating state in the status indicator.
- Update vulnerable development dependencies and add real Home Assistant lifecycle, HTTP,
  WebSocket, configuration-flow, DOM and production-bundle tests.

## [0.1.0] - 2026-11-12

Initial release.

### Added

- Cloud integration for Rehlko (formerly Kohler) home standby generators via the Energy Mgmt.
  app's `/kem/api/v3` API, with Okta (OAuth 2.0 password grant + refresh token) authentication.
- A device per generator, a sub-device per automatic transfer switch, and an account device for
  notification preferences.
- Full entity coverage — sensors, binary sensors, buttons, selects, numbers, datetime, switches,
  text, event entities, a calendar, and a firmware update entity — plus a catch-all that exposes
  any API field without a dedicated entity.
- Writes: start/stop exercise, create/edit/delete the exercise schedule, sync the controller
  clock, add maintenance notes, set and rename load-module / PIM parameters, rename the
  generator, toggle automatic firmware updates, and toggle account notification categories.
- Bus events and `event` entities for the activity log, alerts (raised/cleared), app
  notifications, and derived power events; adaptive polling (faster while running or during an
  outage).
- A **Generator** sidebar panel (Lit + Vite) with a state-aware generator rendering, live power
  flow, operating statistics, and tabs for overview, controls, activity, maintenance, profile
  and diagnostics.
- Services, including read-only ones that return the activity log, alerts, maintenance history,
  notifications, raw payloads and the controller parameter catalogue.
- Diagnostics with personal data redacted.
- Documentation of the API and authentication model, and the reverse-engineering method used to
  reconstruct them, under `docs/`.

[0.1.0]: https://github.com/kedube/ha-rehlko/releases/tag/0.1.0
