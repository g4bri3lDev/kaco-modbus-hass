# kaco — Home Assistant integration

Monitors and controls KACO solar inverters over SunSpec Modbus TCP. All the
protocol work lives in the
[kaco-modbus](https://github.com/g4bri3lDev/kaco-modbus) library, published to
PyPI; this repository is only the Home Assistant side.

```bash
uv sync
uv run pytest              # 57 tests, coverage must stay >= 90%
uv run ruff check .
uv run ruff format .       # CI checks formatting; run it before pushing
uv run mypy custom_components/
```

CI also runs **hassfest** and the **HACS action**, which validate the manifest
and the repository the way Home Assistant and HACS will.

## Domain

The domain is `kaco`, not `kaco_modbus` — named for the device, not the
transport, per Home Assistant guidance. **A domain cannot be changed**: it is
also the `custom_components/` directory name and must be importable.

`kaco_rs485` is the sibling integration, for KACO's proprietary serial
protocol. The split is by **transport, not by hardware generation**: a
blueplanet TL3 speaks both, and the legacy protocol reaches modern units too
(its specification covers the blueplanet 100/125 NX3).

Where an inverter offers both, **this integration is the one to use** — Modbus
TCP needs a LAN cable and a setting, where the serial route needs an adapter
wired to the bus. The serial integration is for inverters that have no Modbus
at all.

A site can therefore mix the two, in which case only the Modbus inverters
appear here and the Energy dashboard sees part of the plant.

## The library is pinned exactly

`manifest.json` and `pyproject.toml` both pin `kaco-modbus==<version>`, and
there is deliberately no editable path override: local tests run against the
same wheel a user gets. A library change therefore has to be released before
this repository can use it.

`tmodbus` is listed **explicitly** in the manifest requirements alongside
`modbus-connection[tmodbus]`. Home Assistant does not install extras when the
base package is already present, so relying on the extra alone gives
`ModuleNotFoundError: No module named 'tmodbus'` on a fresh install.

## Traps that have already caught this project

**Write, then write state.** After a control write, call
`self.async_write_ha_state()`. `async_request_refresh()` is debounced, so
relying on it alone means a second toggle inside the cooldown appears to do
nothing — the entity sticks at its old value.

**Timeouts arrive in the report, not as an exception.** The library polls each
component separately and records `ModbusError` per component, and
`ModbusTimeoutError` is one. A silent inverter therefore shows up as an
`UpdateReport` with nothing updated, *not* as a raised exception, so anything
counting timeouts has to inspect the report too.

**`SunSpecMapShiftError` is not a `ModbusError`.** It needs its own except
clause, and it means every bound register offset is stale, so the entry is
reloaded rather than retried.

**Never reload on a dropped connection.** Every request connects first, so a
broken link heals on the next poll.

## Night-time behaviour

A KACO keeps answering after dark but parks unmeasured registers at zero. The
library withholds those, so grid frequency, the three phase voltages,
temperature and power factor go **unknown** overnight rather than reporting a
false zero. Power, current and energy stay at `0`, which is the truth.

Lifetime energy is a `RestoreSensor` that holds its last value and is always
available, so the Energy dashboard does not gain a gap every night. It also
ignores a small backwards step, which `TOTAL_INCREASING` would otherwise read
as a meter reset.

## Translations

`strings.json` is the source; `translations/en.json` must be identical to it.
**Do not use `[%key:...%]` references in either** — those are resolved by
Home Assistant core's translation build, which a custom integration never goes
through, so a reference is shown to users verbatim. `tests/test_translations.py`
enforces this, along with every key being present in `de.json`.

## Controls

Every entity that writes to the inverter is **disabled by default**. These
write to a live grid-tied inverter, and curtailment or disconnection may be
subject to an interconnection agreement.

## Releasing

release-please, driven by conventional commits. The version lives in
`custom_components/kaco/manifest.json` and is updated by the release PR — do
not edit it by hand. HACS reads the latest GitHub **release**, so merging that
PR is what makes a version installable; tags alone are not enough.

Merges are **not** squashed, so individual commit messages reach the
changelog. A `feat!` whose breaking change a later commit undoes would leave a
false entry — collapse such a branch before merging.

## Open work

`use-core-shared-connection` (draft PR #3) migrates to core's shared Modbus
connection: `async_get_unit` for setup, `async_get_temporary_unit` for the
config flow probe. It is blocked until Home Assistant 2026.9.0 ships — the
pinned `pytest-homeassistant-custom-component` carries 2026.8.3, which has no
`connection.py`, so CI fails there by design.
