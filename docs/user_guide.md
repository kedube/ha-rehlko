# Rehlko Energy Management — user guide

Everything the integration creates, and how to use it.

If you are coming from the **Rehlko** integration that ships with Home Assistant, read
[Moving from the built-in integration](migrating_from_core.md) first: it lists the entity IDs
and state values that change.

## Devices

For each generator on your account you get:

- **The generator** — a device whose model, serial number, firmware and controller type come
  from the API. Most entities live here.
- **Its transfer switch** — a sub‑device, when the generator reports an automatic transfer
  switch (ATS). It carries the ATS entities.
- **The account** — a device that holds the notification‑preference switches (these are
  account‑wide, not per generator).

A generator that is removed from your Rehlko account loses its devices and entities here once
it has been missing from three consecutive readings of the account. An account that suddenly
lists no generators at all is treated as a fault of the service, and nothing is removed.

## The sidebar panel

The **Generator** panel appears for Home Assistant administrators at `/rehlko-energy` on your
Home Assistant instance. It shows, for the selected generator:

- Manufacturer product imagery selected from the reported model, with its original proportions.
  Models without a verified exact image use a labeled representative image from the closest
  available enclosure family. The status chip shows live operating state.
- A utility → generator → home **power flow** with live voltages and the home load.
- **Operating statistics** (engine state, speed, frequency, battery, oil pressure, coolant,
  fuel, total runtime).
- Tabs:
  - **Overview** — status, next exercise, active alerts.
  - **Controls** — start/stop an exercise, create/edit/delete the schedule, sync the clock,
    add a maintenance note, toggle notification categories.
  - **Activity** — the event log and app notifications.
  - **Maintenance** — schedule and note history.
  - **Profile** — model/serial/firmware, site, dealer, load module, PIM, transfer switch.
    Writable load‑module and PIM settings can be changed here: on/off settings have a switch,
    and the pencil opens an editor for a setting's name and value.
  - **Diagnostics** — connectivity, cellular, refresh times.

The panel streams the same data the entities use (over a websocket), so it updates in step with
polling. Turn it off per account under the integration's **Configure** options.

Starting an exercise and deleting the schedule ask for confirmation first. The **Diagnostics**
tab links to the generator's device page, where every entity and its history live.

## Languages and units

The integration and the panel are available in English, German, Spanish, French, Italian,
Japanese, Dutch, Polish, Brazilian Portuguese and Simplified Chinese. Anything not yet
translated shows in English.

- Entity names, states, the setup dialogs, actions and error messages follow the language of
  the user who is looking at them, as with any Home Assistant integration.
- The panel also follows that user's profile: number format, 12/24‑hour clock, and whether
  times are shown in the browser's or the server's time zone. On a metric installation it shows
  temperatures in °C and oil pressure in kPa; the API reports °F and psi.
- Calendar event titles and the sidebar title are written by the server, so they use Home
  Assistant's own language (**Settings → System → General**), not each user's.
- Names that come from Rehlko's service — alert and activity names, notification messages, your
  generator's name — are shown as the service sends them.

## Entities

Exact entities depend on what your generator reports. Headline ones:

### Sensors

Power & load: utility voltage, generator voltage, generator load (W and %), rated output
voltage, power source. Engine: speed, frequency, oil pressure, coolant / lube‑oil / compartment
temperature, engine state, fuel level. Controller: battery voltage, controller temperature,
controller clock, status, mode switch, shutdown reason, active alert count. Runtime &
maintenance: total runtime, total operation, runtime since maintenance, last run, last/next
maintenance, maintenance interval, latest note. Exercise: next exercise, last exercise
start/end, exercise in progress. Activity: last activity, last notification. Site: outdoor
temperature, weather.

Diagnostic sensors: model, controller product/type, firmware version/build, fuel type, cooling,
connection, the IP address Rehlko sees, MAC address, last connected, status/parameter update times, uptime %, Wi‑Fi/cellular
signal, dealer, service agreement, cellular plan status/usage/expiry, scheduled firmware update,
installation progress, and the transfer switch's position/link/signal.

**IP address seen by Rehlko** is where Rehlko's servers saw the controller's connection come
from; the service reports nothing else about the network. It is not the generator's address
on your own network (`192.168.x.x` or similar), which only your router knows, and it need not
be your public address either: one between `100.64.0.0` and `100.127.255.255` is a private
address inside a carrier's or the service's own network. To find the generator on your
network, look up its **MAC address** in your router's list of devices. The sensor (disabled
until you enable it) and the panel's Diagnostics tab show it the way your network does; the
service itself reports the six bytes in reverse order.

**Energy produced** (kWh) can be added to the Energy dashboard. Rehlko's service reports the
generator's load in watts, not energy, so the integration adds the load up between polls and
keeps the total across restarts. Treat it as an estimate: it is as fine‑grained as the polling
interval (15 s by default while the generator runs), and nothing is counted while Home Assistant
is stopped or the generator's readings are unavailable.

If a generator reports a field with no dedicated sensor, a diagnostic entity is created for it
automatically (toggle under options), so the full API payload is always within reach. These
catch‑all entities are created **disabled**: open the generator's device page, choose the
disabled entities, and enable the ones you want. Until then they are not updated or recorded.

### Binary sensors

Cloud connection, utility power, on generator power, running, exercising, ready to run, not in
Auto (problem), oil pressure (problem), maintenance due (problem), active alerts (problem),
critical fault (problem), emergency stop (safety), exercise scheduled, service agreement,
cellular kit / Wi‑Fi / cellular online, load module / PIM connected, firmware update available.

### Controls

- **Buttons:** start exercise, stop exercise, sync controller clock, refresh.
- **Selects:** exercise mode, exercise frequency.
- **Number:** exercise duration (and any writable numeric load‑module / PIM parameter).
- **Datetime:** next exercise start (only where the controller supports choosing it).
- **Switches:** account notification categories, automatic firmware updates, and any writable
  boolean load‑module / PIM parameter.
- **Text:** generator name, and any writable text load‑module / PIM parameter.

### Other

- **Event entities:** `activity`, `alerts`, `notifications`, `power` — each fires with the
  relevant attributes when something new arrives.
- **Calendar:** scheduled exercises (projected) and maintenance‑due dates.
- **Update:** controller firmware (shows availability; installation is handled by the dealer or
  the automatic‑update setting).

## Bus events

Fired on the Home Assistant event bus (use with an `event` trigger). Each includes
`generator_id`, `serial_number`, `generator_name`, the HA `device_id`, and a `type`.

| Event | When | Notable data |
| --- | --- | --- |
| `rehlko_energy_device_event` | New activity‑log entry | `code`, `name`, `level`, `fmi`, `is_critical_fault` |
| `rehlko_energy_alert` | Alert becomes active | same as above |
| `rehlko_energy_alert_cleared` | Alert clears | `id` |
| `rehlko_energy_notification` | New app notification | `message`, `notification_type`, `cta_link` |
| `rehlko_energy_power` | Derived power change | `type` = `utility_lost` / `utility_restored` / `generator_started` / `generator_stopped` / `transferred_to_generator` / `transferred_to_utility` |

## Services

Domain services require a Home Assistant administrator or an automation context. Entity
controls use the normal entity permissions. All services below take a `device_id` (the
generator or its transfer switch), except a refresh of all accounts. Action services:

- `rehlko_energy.start_exercise` — `mode` optional.
- `rehlko_energy.stop_exercise`
- `rehlko_energy.set_exercise_schedule` — `frequency`, `mode`, `duration`, `next_start` (all
  optional; omitted fields keep their current value).
- `rehlko_energy.delete_exercise_schedule`
- `rehlko_energy.add_maintenance_note` — `note`.
- `rehlko_energy.sync_controller_clock` — `timestamp` optional (defaults to now).
- `rehlko_energy.set_peripheral_value` — `definition_id`, `value`.
- `rehlko_energy.rename_peripheral` — `definition_id`, `name`.
- `rehlko_energy.refresh` — `device_id` optional (all accounts if omitted).

Read‑only services (return data):

- `rehlko_energy.get_activity_log` — `limit`.
- `rehlko_energy.get_alerts`
- `rehlko_energy.get_maintenance_history`
- `rehlko_energy.get_notifications` — `limit`.
- `rehlko_energy.get_generator_data` — the raw device/details payloads.
- `rehlko_energy.get_parameter_definitions` — `kind` (`generator` or `ats`); the controller's
  parameter catalogue.

## Safety guards

Mirroring the app, the integration refuses an action and raises a clear error when:

- live generator telemetry is unavailable, or the generator is **offline** (remote controller actions),
- the **emergency stop** is engaged (start / exercise),
- the generator is **not ready to run** (start exercise),
- the controller does not support remote scheduling (schedule changes), or
- a load‑module / PIM parameter is read‑only.

## Your credentials

- The integration keeps your account email and password and a refresh token in Home
  Assistant's config entry storage (`.storage/core.config_entries`), which is where every
  integration's credentials live. Home Assistant does not encrypt that file; it is protected
  by the file permissions of your Home Assistant installation, and it is included in backups
  (which can be encrypted).
- The Energy Mgmt. app's own credentials (its OAuth client ID and secret, and its API key)
  identify the app, not you, and are the same for everyone. They are built into the
  integration, so setup does not ask for them and they are not saved with your account. If
  Rehlko stops accepting them, setup shows an **App credentials** form, and **Reconfigure**
  has an **App credentials** section; a set you enter there is saved with the entry and used
  from then on.
- The password is kept so the integration can sign in again by itself if the refresh token
  expires. Nothing else uses it.
- None of these values is written to the log, included in **Download diagnostics**, sent to
  the sidebar panel, or returned by any action. Diagnostics also leave out your email, account
  ID, address, serial numbers and free‑text notes.
- If you entered app credentials yourself, **Reconfigure** shows the client ID only. The
  saved client secret and API key are not sent back to your browser; leave those fields empty
  to keep them, or clear all three to go back to the built‑in set.

## Troubleshooting

- **"Rehlko's sign‑in service refused a password sign‑in."** The email and password were not
  judged wrong; the account's sign‑in policy wants something a password alone cannot provide,
  usually multi‑factor authentication. The integration signs in with the password only and
  cannot complete a second step.
- **Re‑authentication requested.** Your password changed, or the refresh token was revoked.
  Follow the prompt and re‑enter the password.
- **"Signed in, but the API rejected the request."** The API key is wrong. If you entered app
  credentials yourself, update them with **Reconfigure** on the entry, or clear them there to
  use the built‑in set.
- **"The sign‑in service rejected the app's client ID or client secret."** Rehlko has changed
  the app's credentials. Update the integration; until a release has the new ones, open
  **Reconfigure** on the entry and enter them in **App credentials**
  ([API.md](API.md#authentication) says where to find them).
- **Stale data / offline.** Check the generator's own connectivity; the panel's Diagnostics tab
  shows the last successful refresh.
- **Diagnostics for a bug report:** the entry's **Download diagnostics** redacts serial numbers,
  addresses, contacts and tokens.

- **Panel missing or blank.** Install and configure the integration, sign in as an
  administrator, and enable **Show sidebar panel** in its options. Use `/rehlko-energy`
  on the same host and port as Home Assistant. After updating the integration, restart
  Home Assistant and reload the page. Connection failures appear in the panel and retry
  automatically. The local `npm run dev` preview uses sample data and simulated actions.
