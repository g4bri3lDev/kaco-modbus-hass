# KACO blueplanet for Home Assistant

A custom integration for Home Assistant that monitors KACO blueplanet inverters via Modbus TCP using the new shared-Modbus framework. Built on the [kaco-modbus](https://github.com/g4bri3lDev/kaco-modbus) device library, this integration provides 15 sensors including real-time power and energy metrics compatible with Home Assistant's Energy Dashboard.

## Prerequisites

To use this integration, you need:

1. **modbus_connection provider integration**: This custom integration depends on the `modbus_connection` component, which is currently available as a custom component and will be included in Home Assistant core in a future release.

2. **A Modbus Connection config entry**: You must configure a "Modbus Connection" entry in Home Assistant that points to your inverter:
   - **Host**: Your inverter's IP address
   - **Port**: 502 (standard Modbus TCP port)

3. **Enable Modbus TCP on the inverter**: Before adding this integration, you must enable Modbus/SunSpec on the inverter itself:
   - Access the inverter's menu via local GUI or WebGUI
   - Navigate to **MODBUS / SunSpec protocol**
   - Enable the protocol (default Modbus TCP port is 502)
   - Refer to your inverter's documentation or KACO's Modbus Protocol Application Note for details

### Install the kaco-modbus library (until it's on PyPI)

This integration's `manifest.json` declares a dependency on the
[`kaco-modbus`](https://github.com/g4bri3lDev/kaco-modbus) device library
(`kaco-modbus>=0.1,<1`). Home Assistant normally resolves `manifest.json`
requirements by installing them from PyPI when the integration loads —
**but `kaco-modbus` isn't published to PyPI yet**, so on a stock HA install
the integration will fail to load with a requirements error until you
install the library into HA's Python environment yourself:

- For a **venv install** (e.g. a development HA instance), install
  straight from the repo:
  ```bash
  pip install git+https://github.com/g4bri3lDev/kaco-modbus.git
  ```
  or, for a local checkout you're iterating on:
  ```bash
  pip install -e /path/to/kaco-modbus
  ```
  Run this inside the same Python environment Home Assistant uses.
- For **HA OS / Supervised / containers**, HA's requirement installer
  needs the `kaco-modbus` wheel to be resolvable, which these managed
  environments don't give you an easy way to influence by hand. The
  simplest path today is a development HA instance (venv or local
  checkout) where you control the Python environment directly.

Once `kaco-modbus` is published to PyPI this step disappears.

## Installation

### Option 1: HACS (Custom Repository)

1. Add this repository as a custom repository in HACS:
   - Go to **HACS** → **Integrations** → **⋯** (menu) → **Custom repositories**
   - Add URL: `https://github.com/g4bri3lDev/kaco-modbus-hass`
   - Category: Integration
2. Search for "KACO blueplanet" in HACS
3. Click **Install**
4. Restart Home Assistant

### Option 2: Manual Installation

1. Download the `custom_components/kaco` folder from this repository
2. Copy it to your Home Assistant config directory: `<config>/custom_components/kaco`
3. Restart Home Assistant

## Setup

Once the integration is installed and a Modbus Connection is configured:

1. Go to **Settings** → **Devices & Services**
2. Click **Add Integration**
3. Search for and select **"KACO blueplanet"**
4. Select your **Modbus Connection** from the dropdown
5. Enter the **Modbus Unit ID** (default is 1; check your inverter configuration)
6. The integration will probe the inverter to verify connectivity
7. After successful setup, entities will appear in your device

## Entities

The integration exposes 15 sensors:

| Entity | Unit | Enabled by Default | Notes |
|--------|------|-------------------|-------|
| AC Power | W | ✓ | Real-time AC output power |
| Lifetime Energy | Wh | ✓ | Total energy produced; Energy Dashboard compatible |
| Operating State | — | ✓ | Current inverter state (off, sleeping, mppt, throttled, fault, standby, …) |
| AC Frequency | Hz | ✓ | Grid frequency |
| AC Current | A | ✓ | Real-time AC output current |
| DC Power | W | ✓ | Real-time DC input power |
| DC Voltage | V | ✗ | Input voltage from PV array |
| DC Current | A | ✗ | Input current from PV array |
| Voltage Phase A | V | ✗ | Three-phase output voltage (A) |
| Voltage Phase B | V | ✗ | Three-phase output voltage (B) |
| Voltage Phase C | V | ✗ | Three-phase output voltage (C) |
| Apparent Power | VA | ✗ | Apparent power output |
| Reactive Power | VAR | ✗ | Reactive power output |
| Temperature (Cabinet) | °C | ✓ | Cabinet temperature (diagnostic) |
| Temperature (Heatsink) | °C | ✓ | Heatsink temperature (diagnostic) |

Disabled-by-default entities can be enabled in **Settings** → **Devices & Services** → select the device → click entities to toggle them.

## Troubleshooting

### "Cannot Connect" Error During Setup

If setup fails with a "cannot_connect" error:

1. **Verify Modbus is enabled on the inverter**: In the inverter menu, check that MODBUS / SunSpec protocol is enabled (enabled by default on most models, but may be disabled after reset)
2. **Verify the unit ID**: Ensure the Modbus Unit ID you entered matches your inverter (default is 1)
3. **Test connectivity manually**: From the machine running Home Assistant, use the kaco-modbus library's dump CLI:
   ```bash
   uv run --extra cli python -m kaco_modbus.dump <inverter-ip>
   ```
   This will attempt to connect and print live inverter data if successful, or show a connection error
4. **Check network**: Ensure your Home Assistant machine can reach the inverter on port 502

### Integration fails to load with a requirements error

The `kaco-modbus` library isn't installed/resolvable in Home Assistant's
Python environment. See [Install the kaco-modbus library](#install-the-kaco-modbus-library-until-its-on-pypi)
under Prerequisites.

See the [kaco-modbus repository](https://github.com/g4bri3lDev/kaco-modbus) for more debugging information.

## Development

### Setup

```bash
git clone https://github.com/g4bri3lDev/kaco-modbus-hass
cd kaco-modbus-hass
uv sync
```

### Testing & Linting

```bash
uv run pytest -v
uv run ruff check
uv run ruff format --check
```

### Status

- **Version**: 0.1.0
- **Monitoring only**: This integration reads inverter data and does not send commands
- **Tested against**: KACO blueplanet 8.6 TL3 M2

## License

Apache License 2.0. See [LICENSE](LICENSE) for details.
