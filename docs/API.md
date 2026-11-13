# Rehlko / Kohler Energy Management API

This document describes the cloud API behind the **Energy Mgmt.** mobile app
(`com.kohlerpower.homeownerApp`, previously "KOHLER Energy Management"), and how this
integration authenticates to and uses it. It was reconstructed by reverse‑engineering the
iOS app bundle installed on the owner's Mac; nothing here depends on an official SDK.

> **Status: unofficial.** Rehlko publishes no public API. Endpoints, fields and enums can
> change without notice. Everything here reflects app version **1.6.202610** (build 21111).

## How this was reconstructed

The app is a Flutter app. Its Dart code is compiled to an ARM64 AOT snapshot in
`Energy Mgmt..app/Wrapper/Runner.app/Frameworks/App.framework/App`. The method and
reproducible scripts live in [`docs/reverse-engineering.md`](reverse-engineering.md); in
short:

1. The app's configuration (`flutter_assets/.env`) gives the hosts, the OAuth issuer, the
   app's OAuth client, and the API key.
2. The Dart snapshot's object pool holds every string constant. Walking the AOT code and
   recording which pool strings each function loads recovers the endpoint paths, their HTTP
   verbs, the request/response field names, and the enum constant tables.

The recovered enum vocabularies are committed verbatim as
[`custom_components/rehlko_energy/api/vocabulary.py`](../custom_components/rehlko_energy/api/vocabulary.py).

## Hosts

| Purpose | URL |
| --- | --- |
| API (current) | `https://api.hems.rehlko.com` |
| API (alternate) | `https://api.rk-prod.energymanagement.dev` |
| OAuth issuer (Okta) | `https://auth.home.kohlergenerators.com/oauth2/default` |

Both API hosts serve the same `/kem/api/v3` surface and sit behind Kestrel/ASP.NET. The app
chooses between them with a remote‑config flag (`useRehlkoUrl`); this integration tries the
first and falls back to the second during setup, then stores whichever answered.

Errors use a consistent envelope:

```json
{ "errorVersion": "V3", "timestamp": "…", "statusCode": 401, "message": "Unauthorized", "details": null, "exception": null }
```

## Authentication

### Model

Authentication is **OAuth 2.0 / OpenID Connect against Okta** (the `default` authorization
server at the issuer above). The app itself signs in with the authorization‑code + PKCE flow
in a browser tab (via AppAuth). That same Okta client also permits the **resource‑owner
password grant**, which is what a headless Home Assistant uses — there is no browser to drive.

Discovery (`/.well-known/openid-configuration`) confirms the grants the server supports,
including `password` and `refresh_token`, and `client_secret_basic` client authentication.

The app identifies itself with three values from `flutter_assets/.env`. They identify the
*app*, not any account, and every install ships the same ones:

| `.env` key | Use |
| --- | --- |
| `CLIENT_ID` | Okta OAuth client id |
| `CLIENT_SECRET` | Okta OAuth client secret (the client is confidential; HTTP Basic at the token endpoint) |
| `API_KEY` | Sent as the `ApiKey` header on every `/kem/api/v3` call |

This integration does **not** bundle those three values. You provide them during setup (the
config flow has an **App credentials** section), and they are stored with the config entry.
To read them from the copy of the app installed on a Mac:

```bash
grep -E '^(CLIENT_ID|CLIENT_SECRET|API_KEY)=' \
  "/Applications/Energy Mgmt..app/Wrapper/Runner.app/Frameworks/App.framework/flutter_assets/.env"
```

Each line reads `NAME='value'`. The quotes are not part of the value; the setup form removes
them if you paste them.

(If a future app release rotates them, re‑read the file and use **Reconfigure** on the entry.)

### Token endpoint

`POST https://auth.home.kohlergenerators.com/oauth2/default/v1/token`
with `Authorization: Basic base64(CLIENT_ID:CLIENT_SECRET)` and a form body.

Sign in (first time):

```
grant_type=password
username=<account email>
password=<account password>
scope=openid profile offline_access email
```

Refresh (subsequently — `offline_access` yields a refresh token):

```
grant_type=refresh_token
refresh_token=<stored refresh token>
scope=openid profile offline_access email
```

A success returns `access_token` (a ~1‑hour JWT), `id_token`, `refresh_token`, `expires_in`
and `scope`. Okta may **rotate** the refresh token on each use, so the client persists the new
one whenever it changes (`CONF_REFRESH_TOKEN` on the entry).

Token errors come back as `{"error": "...", "error_description": "..."}`. The client maps
`invalid_client` / `unauthorized_client` → "check the app client id/secret", and other errors
(e.g. `invalid_grant`) → "check the email/password or re‑authenticate".

### Multi-factor sign-in

The app signs in through Okta's hosted page, so any second factor would be handled there and
the app itself contains no multi-factor screens. This integration uses the password grant,
which cannot answer a second factor. The tenant runs Okta Identity Engine and its discovery
document lists Okta's one-time-code grants (`…/mfa-otp`, `…/mfa-oob`), but that list describes
the server, not what Rehlko's app client is allowed to use, and no homeowner account is known
to have multi-factor sign-in. If Okta answers a password sign-in with `mfa_required` or
`access_denied`, the integration reports that the sign-in was refused, not that the password
is wrong.

### Calling the API

Every `/kem/api/v3` request carries two headers:

```
Authorization: bearer <access_token>
ApiKey: <API_KEY>
```

Note the lowercase `bearer` scheme — that is the literal the app sends. On a `401` the client
refreshes the access token once and retries; a second `401` triggers Home Assistant
re‑authentication.

Device‑scoped reads also take a `sourceDeviceHost` query parameter equal to the device's
`deviceHost` (`Hub`, `REC`, or `RET`), which routes the request to the correct telemetry
backend.

## Endpoints

All paths are prefixed with `/kem/api/v3`. `{id}` is the numeric device id from
`/homeowner/homes`.

### Account & homes

| Method | Path | Notes |
| --- | --- | --- |
| GET | `/homeowner/me` | The signed‑in user (`id`, `email`, name, consents). |
| PUT | `/homeowner/me` | `{firstName, lastName, hasAcceptedTC, hasAcceptedMarketingOutreach}`. |
| DELETE | `/homeowner/me` | Delete the account (not used here). |
| GET | `/homeowner/homes` | Homes, each with `devices[]` (the generator summaries), weather, users. |
| POST | `/homeowner/homes` | Add a generator: `{serialNumber, controllerPin, displayName, address}`. |
| DELETE | `/homeowner/homes/{id}` | Remove a generator from the account. |
| GET | `/homeowner/settings/notification` | Per‑category push/email flags (see below). |
| POST | `/homeowner/settings/notification` | Write the full settings object. |
| GET | `/homeowner/detectedDevices` | Generators detected nearby during commissioning. |
| GET/POST | `/homeowner/invites/{code}/claim`, `/homeowner/homes/{id}/users/invite` | Share access. |
| GET | `/notifications?DeviceId=&Offset=&Limit=` | The app's notification feed. |
| POST/DELETE | `/notifications/token`, `/notifications/token/deviceid/{id}` | Push registration (not used here). |

### Device — read

| Method | Path | Notes |
| --- | --- | --- |
| GET | `/devices/{id}?sourceDeviceHost=` | Full generator **details** (telemetry, exercise, loadShed, pim, ats, …). The richest payload; see the field map below. |
| GET | `/devices/{id}/events?sourceDeviceHost=` | Activity log (device events). |
| GET | `/devices/{id}/alerts?sourceDeviceHost=` | Currently active alerts. |
| GET | `/devices/{id}/maintenance_notes` | Maintenance history. |
| GET | `/devices/cellplan/{id}` | Cellular data plan (`remainingDataMb`, `totalDataMb`, `expiryDate`). |
| GET | `/devices/{id}/generators/{serial}/parameters/definitions` | Controller parameter catalogue. |
| GET | `/devices/{id}/ats/{serial}/parameters/definitions` | Transfer‑switch parameter catalogue. |
| GET | `/devices/verification2?serialNumber=&controllerPin=` | Validate a serial/PIN when adding. |
| GET | `/devices/address?address=` | Validate/geocode an address. |

### Device — write

| Method | Path | Body | Action |
| --- | --- | --- | --- |
| PUT | `/devices/{id}` | `{displayName, address, connectionType, installProgressType, autoFirmwareUpdateEnabled, completedInstallProgressSteps}` | Edit generator details. |
| PUT | `/devices/{id}/exercise` | `{frequency, nextStartTimestamp, mode, durationMinutes}` | Create/update the exercise schedule. |
| DELETE | `/devices/{id}/exercise` | — | Delete the schedule. |
| POST | `/devices/{id}/exercise/start` | `{mode}` | Start an exercise now. |
| POST | `/devices/{id}/exercise/stop` | — | Stop the running exercise. |
| POST | `/devices/{id}/set_controller_clock` | `{controllerClockTimestamp}` | Set the controller clock. |
| POST | `/devices/{id}/maintenance_notes` | `{contents}` | Add a maintenance note. |
| POST | `/devices/{id}/peripherals/{definitionId}/set_value` | `{value}` | Write a load‑module / PIM parameter. |
| PUT | `/devices/{id}/peripherals/{definitionId}` | `{displayName}` | Rename a load / PIM item. |

### What the app does not do

The table above is every `/kem/api/v3` call in app version 1.6.202610; `scripts/reverse_engineering/xref.py`
lists them with their verbs. Two things people look for are absent:

- **No fault reset.** Alerts carry `canRemoteResetFault` and the details carry
  `remoteResetCounterSeconds`, but the app never writes either and has no reset route. Its
  "Clear Alerts & Reset" text is a checklist for the mode switch on the generator itself.
- **No firmware installation.** The app reads `firmwareUpdate` and writes only the
  `autoFirmwareUpdateEnabled` flag (through `PUT /devices/{id}`).

## Key payloads (field map)

Field names below are exactly as the API uses them. The integration keeps every payload as
received, so any field not listed here is still exposed (as a diagnostic entity and in the
`rehlko_energy.get_generator_data` service).

**Device summary** (`/homeowner/homes` → `devices[]`): `id, serialNumber, displayName,
deviceHost, address, product, productDisplayName, controllerType, firmwareVersion,
currentFirmware, isConnected, lastConnectedTimestamp, connectionType, deviceIpAddress,
hubData, macAddress, shutdownReason, status, statusUpdateTimestamp,
latestParameterUpdateTimestamp, dealerOrgs, alertCount, model, modelDisplayName,
lastMaintenanceTimestamp, nextMaintenanceTimestamp, maintenancePeriodDays,
hasServiceAgreement, totalRuntimeHours, serviceAgreementStatus, cellularExpiryDate,
cellularDataPercentage, cellularDataStatus, cellKitPaymentStatus, uptimePercent, engineState,
engineStateDisplayNameEn`.

**Device details** (`/devices/{id}`): the summary under `device`, plus `generators[],
powerSource, switchState, coolingType, connectionType, serverIpAddress, serviceAgreement,
exercise, lastRanTimestamp, totalRuntimeHours, totalOperationHours,
runtimeSinceLastMaintenanceHours, remoteResetCounterSeconds, addedBy, associatedUsers,
controllerClockTimestamp, fuelType, fuelLevelPercent, batteryVoltageV, engineCoolantTempF,
engineFrequencyHz, engineSpeedRpm, lubeOilTempF, controllerTempF, engineCompartmentTempF,
engineOilPressurePsi, engineOilPressureOk, generatorLoadW, generatorLoadPercent,
generatorVoltageAvgV, setOutputVoltageV, utilityVoltageV, engineState, engineStateDisplayNameEn,
loadShed, pim, cellularExpiryDate, cellularInstallationDate, cellularDataPercentage,
cellularDataStatus, cellularKitOnline, ats, installProgress, autoFirmwareUpdateEnabled,
scheduledFirmwareUpdateTimestamp, firmwareUpdate`.

**Exercise** (`details.exercise`): `frequency, nextStartTimestamp, mode, runningMode,
durationMinutes, lastStartTimestamp, lastEndTimestamp, supportsNextExerciseDateTimeParam`.

**Load module / PIM** (`details.loadShed`, `details.pim`): `{isConnected, parameters[]}`,
each parameter `{definitionId, displayName, value, isReadOnly}`.

**Event / alert** (`/events`, `/alerts`): `id, name, level, deviceEventIntId, deviceEventId,
event, fmi, parameterId, parameter, timestamp, type, isCriticalFault, canRemoteResetFault`.

**Notification** (`/notifications`): `id, tag, type, message, timestamp, deviceId,
serialNumber, displayName, ctaText, ctaLink, isEStopEvent`.

**Maintenance note** (`/maintenance_notes`): `id, timestamp, contents, authorIsDealer,
dealerAuthor`.

**Parameter definition** (`/parameters/definitions`): `id, name, dataType, enumId, access,
defaultValue, minValue, maxValue, unit, changeStep` (and `registerMapIds, parameters`).

**Notification settings** (`/homeowner/settings/notification`): `sendShutdowns, sendWarnings,
sendGeneratorRunningNotices, sendNotices, sendConnectionNotices, sendMaintenanceNotices,
sendLongRunningNotices, sendNotificationEmails, sendPushNotifications`.

## Enumerations

The wire values for every enum are in
[`api/vocabulary.py`](../custom_components/rehlko_energy/api/vocabulary.py). The important ones:

- **DeviceStatus**: `ReadyToRun, Shutdown, SwitchStateOff, Running, RunningExercise, Offline`
- **GensetState** (engine): `Off, CrankOn, CrankPause, Idle, Running, CoolDown, Stopping,
  Shutdown, PerformingLoadedTest, PerformingUnloadedTest, PerformingVariableSpeedExercise,
  PerformingLoadedExercise, PerformingUnloadedFullSpeedExercise, …`
- **PowerSource**: `Unknown, Utility, Generator`
- **SwitchState**: `Off, Auto, Manual`
- **ExerciseMode**: `None, Unloaded, UnloadedFullSpeed, LoadedFullSpeed, EcoExercise`
- **ExerciseFrequency**: `Weekly, EveryOtherWeek, Monthly`
- **DeviceEventLevel**: `None, Status, Warning, Fault, Shutdown, Notice, SystemStatusChange`
- **FuelType**: `NaturalGas, LiquidPropane, Gasoline, Diesel, UnknownUndefined`
- **ConnectionType**: `Unknown, Ethernet, KohlerWifi, OtherWifi, Cellular, KohlerCellKit`
- **DeviceEventId**: 400 values — the full fault/warning/status catalogue (used for alert and
  activity names).

The generated client maps any unrecognised string to an "unknown" value, so this integration
tolerates values newer than the ones captured here.

## Timestamps

The service mixes ISO‑8601 forms: `…Z`, `…+00:00`, seven‑digit .NET fractional seconds, and
naive local wall‑clock times (notably the controller clock and exercise times). The client
parses all of these; for writes it mirrors the form the service last used for that field, so a
naive controller clock is written back in the site's local wall‑clock time without an offset.

## Responsible use

This is the owner's own account and their own generator. Keep the polling intervals
reasonable (the defaults are 60 s in standby, 15 s while running, feeds every 120 s) and avoid
hammering the service. Starting a generator or an exercise is a physical action — the
integration refuses when the generator is offline, not ready to run, or has the emergency stop
engaged, mirroring the app's own guards.
