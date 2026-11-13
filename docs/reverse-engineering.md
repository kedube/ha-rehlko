# How the API was reverse‑engineered

This integration was built without any official SDK or documentation, by reading the
**Energy Mgmt.** iOS app. This page records the method so the work is reproducible and so the
field/enum catalogue can be refreshed when Rehlko ships a new app version.

Everything here operates on a copy of the app the owner already has a licence to; it only
reads constant data (strings, enum tables, endpoint paths). No DRM is circumvented and the
app is not modified or redistributed.

## The app

`Energy Mgmt..app` is a Flutter app (`com.kohlerpower.homeownerApp`). The parts that matter:

- `Wrapper/Runner.app/Frameworks/App.framework/flutter_assets/.env` — plaintext configuration:
  API hosts, the Okta issuer, the app's OAuth `CLIENT_ID` / `CLIENT_SECRET`, and the `API_KEY`.
- `Wrapper/Runner.app/Frameworks/App.framework/App` — the Dart code, compiled to an ARM64 AOT
  snapshot (Dart **3.5.4**, iOS, uncompressed pointers). This is where the endpoints, the DTO
  field names and the enum tables live.

The snapshot is a Mach‑O dylib. Its `__TEXT` segment is mapped so that file offset equals the
virtual address, so the four Dart snapshot symbols (`kDartVmSnapshotData`,
`kDartIsolateSnapshotData`, and the two instruction symbols) can be read straight from the
file. The section offsets used by the scripts come from:

```bash
otool -l "/Applications/Energy Mgmt..app/Wrapper/Runner.app/Frameworks/App.framework/App" | less
```

## Approach

Two complementary techniques, both in `scripts/reverse_engineering/`:

1. **String mining.** `strings` on the `App` binary yields the whole constant pool: endpoint
   paths (`/kem/api/v3/...`), DTO field names (`batteryVoltageV`, `engineSpeedRpm`, …), enum
   value names, and the English UI copy. This alone reveals most of the surface.

2. **Object‑pool cross‑referencing.** Strings on their own are unordered. To recover *which
   endpoint uses which fields* and *which enum a value belongs to*, the scripts parse the Dart
   snapshot enough to:
   - rebuild the global **object pool** (the table every compiled function indexes into for its
     constants), mapping each pool slot to its string; and
   - scan the AOT machine code for the `ldr Xt, [x27, #off]` instructions that load pool
     slots (`x27` is the pool pointer; `x15` is Dart's stack pointer, so function boundaries
     are the `stp x29, x30, [x15, #-16]!` prologues). Grouping the loaded strings by function
     reconstructs each REST call (path + verb + body fields) and each generated model.

   Enum tables are recovered separately by walking the snapshot's `Instance` cluster fills and
   reading each enum constant's `(index, _name, value)` triple — the `value` is the exact wire
   string. Every enum conveniently starts with a `swaggerGeneratedUnknown` sentinel, which
   makes the tables easy to find.

The snapshot parser (`dartsnap.py`) implements just the clustered‑snapshot *allocation* pass
from `runtime/vm/app_snapshot.cc` in the Dart SDK at tag `3.5.4` — enough to assign object
reference ids and locate RO‑data strings, not a full deserializer.

## Running it

```bash
cd scripts/reverse_engineering
# (optional) export REHLKO_APP="/path/to/Energy Mgmt..app"

python3 pool.py  pool.pkl            # find + decode the object pool  -> pool.pkl
python3 xref.py  pool.pkl xref.txt   # per-function string xrefs       -> xref.txt
python3 enums.py enums.txt           # enum constant tables            -> enums.txt
```

Then read the outputs:

- `xref.txt` — one line per function, e.g.
  `@0x4fc334 | /kem/api/v3/devices/ ¦ /exercise/start ¦ POST`, and the DTO field lists.
- `enums.txt` — one line per enum, e.g.
  `… swaggerGeneratedUnknown=null, unloaded='Unloaded', unloadedFullSpeed='UnloadedFullSpeed', …`.
- `recovered_enums.json` — the labelled enum tables, the source for
  `custom_components/rehlko_energy/api/vocabulary.py`.

## Refreshing for a new app version

1. Install the new app (or copy the `.app`), and point `REHLKO_APP` at it.
2. Check the Dart version: `strings .../Flutter.framework/Flutter | grep -E '^[0-9]+\.[0-9]+\.[0-9]+ \(stable\)'`.
   If it changed, update the class‑id list and `ReadAlloc` handling in `dartsnap.py` against
   that tag of `runtime/vm/app_snapshot.cc`, and refresh the three `ISO_*`/`VM_*` offsets from
   `otool -l` on the new `App` binary.
3. Re‑run the three scripts. Diff `xref.txt` for new or changed endpoints and
   `recovered_enums.json` for new enum values; update `api/vocabulary.py`, `api/client.py` and
   the entity descriptions as needed.
4. If `.env` changed hosts or rotated the OAuth client / API key, note it in `docs/API.md`;
   users update their entry with **Reconfigure**.

## Alternative: live capture

`dartsnap` reconstructs the *contract*. To see real payloads from the owner's own account,
run an authenticated request directly (the integration's own client works):

```bash
python3 scripts/capture.py --help     # see scripts/capture.py
```

`capture.py` signs in with the password grant and dumps selected endpoints to JSON for one
generator. Treat the output as sensitive — it contains the serial number, address and tokens —
and never commit it (`captures/` is git‑ignored).
