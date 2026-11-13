# Moving from Home Assistant's built-in Rehlko integration

Home Assistant ships its own **Rehlko** integration (domain `rehlko`, since 2025.5). This
project, **Rehlko Energy Management** (domain `rehlko_energy`), talks to the same Rehlko cloud
service with the same account, but does a good deal more. This page says how the two differ
and what you have to change when you switch.

The comparison is with the built-in integration as it stands in Home Assistant's development
branch in November 2026.

## At a glance

| | Built-in **Rehlko** | **Rehlko Energy Management** |
| --- | --- | --- |
| Comes from | Home Assistant itself; reviewed and updated with it | This repository, added to HACS or the Marketplace as a custom repository; unofficial |
| Needs | Home Assistant 2025.5 | Home Assistant 2026.2 |
| Sign-in | Rehlko account email and password | The same |
| How it is added | Offered automatically when Home Assistant sees the generator on your network, or by hand | By hand |
| Readings refreshed | Every 10 minutes, fixed | Every 60 s in standby and every 15 s while the generator runs or the utility is out; both adjustable |
| Readings | 25 sensors, 3 binary sensors, load-shed states | Those, plus about 45 more sensors and 17 more binary sensors, and an entity for any field without one of its own |
| Control | None; it only reads | Start and stop an exercise, the exercise schedule, the controller clock, maintenance notes, load-module and PIM settings, the generator's name, notification settings, automatic firmware updates |
| Activity, alerts, notifications | No | Event entities and events for automations, read every 2 minutes |
| Actions | None | 15 `rehlko_energy.*` actions, for administrators and automations |
| Sidebar panel | No | **Generator**, for administrators |
| Energy dashboard | Nothing to add | **Energy produced** (kWh), estimated from the load |
| Calendar, firmware | No | A calendar of exercises and maintenance; a firmware update entity (it shows availability, it does not install) |
| Devices | One per generator | The generator, its transfer switch, and the account |
| Options | None | Polling intervals, the panel, the catch-all entities |
| Download diagnostics | No | Yes, with personal details removed |

Some things are the same in both. Neither talks to the generator directly: both read Rehlko's
cloud, so both stop when it is unreachable. Neither can sign in to an account that asks for a
second factor. Temperatures and pressures follow your Home Assistant unit system in both.

## What you give up

- **An official integration.** The built-in one is maintained and reviewed by the Home
  Assistant project and updates with Home Assistant. This one is a reverse-engineered,
  unofficial project that you update separately.
- **Automatic discovery.** After you remove the built-in integration, Home Assistant may go on
  listing **Rehlko** under *Discovered*. Choose **Ignore** there.
- **A read-only setup.** The built-in integration cannot change anything on the generator.
  This one can start an exercise, and its buttons and switches can be used by every Home
  Assistant user who can control entities, not only administrators. Keep them off shared
  dashboards if that matters to you. The panel and the `rehlko_energy.*` actions are for
  administrators.
- **A light touch on Rehlko's service.** One request per generator every 10 minutes becomes
  one or more a minute. You can raise the intervals under **Configure**.
- **The "Auto run" binary sensor.** There is a replacement with the opposite sense; see the
  table below.
- **The network link on the device.** The built-in integration records the controller's MAC
  address on the device, so a router integration's entry for the generator joins the same
  device. This one shows the MAC address as a sensor only.

## Switching

Entities do not move across by themselves: this is a different integration, so Home Assistant
creates a new device and new entities. Most keep the entity ID they had, as long as the
built-in integration is removed **first**. If both are set up at once, every entity whose ID
is already taken gets `_2` on the end.

1. **Note what uses the old entities.** Open the generator's device page under
   **Settings → Devices & services → Rehlko**. It lists the automations, scripts and scenes
   that use the device. Check your dashboards and anything exposed to a voice assistant too.
2. **Remove the built-in integration.** On the same page, open the ⋮ menu of the entry and
   choose **Delete**.
3. **Install this one** ([README](../README.md#install)) and add it with the same email and
   password.
4. **Fix what refers to an entity that changed**, using the tables below.
5. **Redo what belonged to the old device**: its area, labels, and any automation that used a
   *device* trigger, condition or action. Those point at the old device and have to be made
   again. Automations that refer to entity IDs need no change beyond step 4.
6. **Redo entity settings**: custom names and icons, entities you had enabled, disabled or
   hidden, and what you exposed to voice assistants.

Home Assistant keeps history by entity ID. An entity that keeps its ID carries on where it
left off; one whose ID changes starts fresh, and the old history stays under the old ID until
it expires. You can avoid the edits in step 4: once the built-in integration is gone, open
the new entity's settings and change its entity ID to the old one. New readings are then
recorded under that ID again.

### Entity IDs

`<generator>` is your generator's name as Home Assistant writes it in entity IDs, for example
`home_generator`. These are the defaults; yours differ if you renamed entities.

**These keep their ID** when the built-in integration is removed first:

| Entity | ID | Note |
| --- | --- | --- |
| Battery voltage | `sensor.<generator>_battery_voltage` | |
| Controller temperature | `sensor.<generator>_controller_temperature` | |
| Engine compartment temperature | `sensor.<generator>_engine_compartment_temperature` | |
| Engine speed | `sensor.<generator>_engine_speed` | |
| Engine state | `sensor.<generator>_engine_state` | The values change; see below |
| Generator load | `sensor.<generator>_generator_load` | |
| Last maintenance | `sensor.<generator>_last_maintenance` | Now enabled from the start |
| Last run | `sensor.<generator>_last_run` | |
| Lube oil temperature | `sensor.<generator>_lube_oil_temperature` | |
| Next exercise | `sensor.<generator>_next_exercise` | Now enabled from the start |
| Next maintenance | `sensor.<generator>_next_maintenance` | Now enabled from the start |
| Power source | `sensor.<generator>_power_source` | The values change; see below |
| Server IP address | `sensor.<generator>_server_ip_address` | Disabled until you enable it, as before |
| Total operation | `sensor.<generator>_total_operation` | Now enabled from the start; a running total, see below |
| Total runtime | `sensor.<generator>_total_runtime` | Now enabled from the start; a running total, see below |
| Utility voltage | `sensor.<generator>_utility_voltage` | |
| Oil pressure (problem) | `binary_sensor.<generator>_oil_pressure` | |

**These get a new ID:**

| Built-in | This integration | Note |
| --- | --- | --- |
| `sensor.<generator>_generator_status` | `sensor.<generator>_status` | The values change; see below |
| `sensor.<generator>_voltage` | `sensor.<generator>_generator_voltage` | The generator's average voltage, which the built-in integration names only "Voltage" |
| `sensor.<generator>_engine_frequency` | `sensor.<generator>_generator_frequency` | |
| `sensor.<generator>_engine_oil_pressure` | `sensor.<generator>_oil_pressure` | |
| `sensor.<generator>_engine_coolant_temperature` | `sensor.<generator>_coolant_temperature` | |
| `sensor.<generator>_generator_load_percentage` | `sensor.<generator>_generator_load_of_rated` | |
| `sensor.<generator>_runtime_since_last_maintenance` | `sensor.<generator>_runtime_since_maintenance` | Now enabled from the start |
| `sensor.<generator>_last_exercise` | `sensor.<generator>_last_exercise_started` | Now enabled from the start |
| `sensor.<generator>_device_ip_address` | `sensor.<generator>_ip_address_seen_by_rehlko` | The address alone, without the port; disabled until you enable it |
| `binary_sensor.<generator>_connectivity` | `binary_sensor.<generator>_cloud_connection` | |
| `binary_sensor.<generator>_auto_run` | `binary_sensor.<generator>_not_in_auto` | **Opposite sense**: on means the generator will *not* start by itself. Or use `sensor.<generator>_mode_switch`, which is `auto`, `off` or `manual` |
| `binary_sensor.<generator>_load_shed_<load>` | `sensor.<generator>_load_module_<load>` | State `on` or `off`. Loads you can switch also get `switch.<generator>_load_module_<load>` |

### Values that changed

**Status, engine state and power source** used to report the service's own wording, such as
`ReadyToRun`. They are now lower case with underscores, and Home Assistant shows a translated
name for each ("Ready to run"). Dashboards need nothing; automations and templates that
compare the state do.

| Sensor | Built-in | This integration |
| --- | --- | --- |
| Status | `ReadyToRun`, `Running`, `RunningExercise`, `Shutdown`, `SwitchStateOff` | `ready_to_run`, `running`, `running_exercise`, `shutdown`, `switch_state_off` |
| Engine state | `Standby`, `CrankOn`, `Running`, `Stopping`, `Off`, `PerformingUnloadedFullSpeedExercise`, … | `standby`, `crank_on`, `running`, `stopping`, `off`, `performing_unloaded_full_speed_exercise`, … |
| Power source | `Utility`, `Generator` | `utility`, `generator` |

For example, a trigger for the home going onto generator power:

```yaml
# Before
- trigger: state
  entity_id: sensor.home_generator_power_source
  to: "Generator"

# After
- trigger: state
  entity_id: sensor.home_generator_power_source
  to: "generator"
```

Often you no longer need to compare states at all. There are binary sensors for **Running**,
**Exercising**, **Ready to run**, **Utility power** and **On generator power**, and a
`rehlko_energy_power` event when the utility is lost or restored and when the generator starts
or stops ([user guide](user_guide.md)).

**Total operation and Total runtime** are recorded as running totals rather than plain
measurements. If you had enabled them before, Home Assistant may flag the change to their
long-term statistics under **Developer tools → Statistics** and offer to fix it.

**The IP address** is the address alone (`203.0.113.7`), where the built-in integration shows
what the service sends, port included (`203.0.113.7:2402`). In both it is the address Rehlko's
servers saw the connection come from, not the generator's address on your network.

Everything else reads the same fields and gives the same numbers.

## Running both for a while

You can, to compare them: they are separate integrations and both can sign in with your
account. Expect `_2` on the entity IDs of whichever you add second, and twice the requests to
Rehlko's service. Remove one when you have decided.

## Going back

Delete the **Rehlko Energy Management** entry, remove it in HACS or the Marketplace, restart
Home Assistant, and add **Rehlko** again. The same rules apply the other way round: entities
with the same name get their ID back, and the rest need the tables above read from right to
left.
