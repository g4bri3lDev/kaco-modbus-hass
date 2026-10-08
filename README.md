# KACO for Home Assistant

Monitor and control KACO solar inverters over SunSpec Modbus TCP.

Built on [`kaco-modbus`](https://github.com/g4bri3lDev/kaco-modbus), which does all the
protocol work; this repository is only the Home Assistant side. Developed against a
**KACO blueplanet 8.6 TL3 INT** on firmware V5.53.

## Requirements

Modbus TCP must be enabled **on the inverter itself** — look for the SunSpec or Modbus
protocol setting in its web interface. Port 502 unless you changed it.

KACO's current range is entirely three-phase (`NX3`, `TL3`, `NH3`), which is what this
targets. Older *Powador* units speak a proprietary RS485 protocol and are not supported.

## Install

Copy `custom_components/kaco_modbus` into your Home Assistant `config/custom_components/`
directory and restart, then add **KACO Modbus** from Settings → Devices & services.

You will be asked for the inverter's address. The unit ID can almost always stay at 1 —
KACO inverters are TCP-native and ignore it. It matters only behind an RS485-to-TCP
gateway.

## What you get

The inverter appears as one device.

**Enabled by default** — AC power, AC current, per-phase voltage, grid frequency, DC
power, temperature, operating state, and per-MPPT-string power, voltage and current.
Plus **total energy produced**, which is a `TOTAL_INCREASING` sensor suitable for the
Energy dashboard.

**Disabled by default** — apparent and reactive power, power factor, DC voltage and
current, per-phase current, and the nameplate diagnostics. Enable them per entity if you
want them.

### Night-time behaviour

Unlike most inverters, a KACO keeps answering Modbus after dark — it just stops
*measuring*, parking the registers it no longer reads at zero. Left alone it would
report 0 Hz and 0 V for a grid that is plainly still live, and 0 °C for a cabinet that
was at 46 °C in the afternoon.

So grid frequency, the three phase voltages, temperature and power factor go **unknown**
overnight rather than reporting a false zero. Power, current and energy stay at zero,
because for those zero is simply the truth.

The rest of the handling covers inverters that *do* go silent:

- readings go unavailable, and come back at sunrise without a reload;
- **total energy produced holds its last value** rather than going unavailable, so the
  Energy dashboard does not get a gap every night;
- after three silent polls the connection is dropped so the next one reconnects cleanly;
- the log is not filled — only newly failing sub-systems are reported, at warning level
  once each.

## Control

> [!WARNING]
> These write to a live grid-tied inverter. Curtailment and disconnection can take your
> plant off the grid, and may be subject to your interconnection agreement. Every control
> entity is **disabled by default** — you have to opt in deliberately.

Once enabled, you get a power limit (percent of nameplate), a power factor setpoint, a
reactive power setpoint and its mode, and a grid connection switch.

Setpoints on this hardware carry a revert timer — the inverter drops back to default
after five minutes unless the value is rewritten. The library clears that timer on every
write so a limit holds indefinitely; if a device refuses, it reports the fact rather than
silently letting the setpoint expire.

The volt-var, volt-watt and ride-through curve models are deliberately **read-only**.

## Diagnostics

Downloading diagnostics includes the full raw register map, which can be replayed into
`modbus_connection.mock` to reproduce a problem without the hardware. The serial number
and host are redacted — including the model 1 registers that carry the serial, so it
cannot be recovered from the dump.

## Development

```bash
uv sync
uv run pytest
uv run ruff check .
uv run mypy custom_components/
```

`kaco-modbus` is wired in as an editable path dependency, so changes to the library are
picked up without a release. The whole suite runs against a 920-register image captured
from a real 8.6 TL3, shipped in `kaco_modbus.testing` — no hardware needed.

Translations live in `custom_components/kaco_modbus/translations/`. `strings.json` is the
source; keep `translations/en.json` identical to it. Do not use `[%key:...%]` references
in either — those are resolved by Home Assistant core's translation build, which a custom
integration never goes through, so they would be shown to users verbatim. There are tests
for this.

## License

Apache-2.0
