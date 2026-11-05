<p align="center">
  <img src="logo.png" width="128" alt="PiKVM logo">
</p>

<p align="center">
  <a href="https://my.home-assistant.io/redirect/marketplace_repository/?owner=pschmitt&amp;repository=homeassistant-pikvm&amp;category=integration"><img src="https://my.home-assistant.io/badges/marketplace_repository.svg" alt="Open this integration in Home Assistant Marketplace"></a>
</p>

<h1 align="center">PiKVM for Home Assistant</h1>

<p align="center">Monitor a PiKVM screen and control its keyboard, ATX power and optional host features.</p>

The integration uses the [kvmd API](https://docs.pikvm.org/api/) for normal
operations and optional SSH for system-level controls.

## Features

- **Screen and OCR:** Capture a screen snapshot and expose recognized text from the kvmd OCR endpoint.
- **Device status:** Show online state, kvmd version, CPU temperature and optional ATX target power.
- **Controls:** Send virtual keyboard text or keys, reset the stream and operate ATX power. See [PiKVM controls](docs/controls.md).
- **Optional SSH:** Control LEDs and OLED, check update status, or shut down the PiKVM host.

## Install

Use the Marketplace badge above on Home Assistant 2026.11 or later to add this
repository as a custom integration. On older versions, add it as a HACS
custom repository of type **Integration**. Install and restart Home Assistant.
The badge does not imply a public catalog listing. For manual installation,
copy `custom_components/pikvm/` into Home Assistant's `custom_components/`
directory and restart.

## Quick start

1. Add **PiKVM** under **Settings → Devices & services → Add integration**.
2. Enter its host and kvmd web UI credentials; leave SSH disabled unless needed.
3. Open the Screen camera or use a supported keyboard or ATX control.

## Documentation

| Topic | Description |
|-------|-------------|
| [PiKVM controls](docs/controls.md) | API-backed entities, optional SSH and keyboard actions |

## License

[GPL-3.0](LICENSE). PiKVM logos belong to their respective owners and are not
relicensed under GPL.
