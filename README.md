# PiKVM for Home Assistant

`pikvm` is a Home Assistant custom integration for [PiKVM](https://pikvm.org/) that talks to
the [kvmd API](https://docs.pikvm.org/api/) directly — and optionally to the PiKVM host over
SSH for system-level features (status LEDs, OLED screen, update status, shutdown).

## Features

- **Binary sensors**
  - `Online`: whether the kvmd API is reachable (an unreachable/powered-off PiKVM shows
    as `off`, not `unavailable`)
  - `Updating`: whether a pacman update is in progress (SSH)
  - `Target power`: ATX power LED of the attached host (only when ATX is enabled)
- **Sensors**
  - `OCR`: periodically OCRs the captured screen via the kvmd snapshot OCR endpoint —
    handy to detect boot prompts (LUKS passphrase, GRUB rescue, ...). The full text is
    available in the `full_text` attribute.
  - `CPU temperature` and `kvmd version` (diagnostic)
- **Camera**: `Screen` — snapshot of the captured screen
- **Switches** (SSH)
  - `LEDs`: Raspberry Pi status LEDs
  - `OLED`: kvmd OLED screen services
- **Buttons**
  - `Reset stream`: reset the streamer + HID subsystems
  - `Shutdown`: shut down the PiKVM host (SSH)
  - `ATX power on/off/reset` (only when ATX is enabled)
- **Services**
  - `pikvm.send_text`: type text on the target via the virtual keyboard. With `slow: true`
    the text is typed character by character via key events — slower, but reliable for
    early-boot prompts (e.g. typing LUKS passphrases).
  - `pikvm.send_key`: press a single key (`Escape`, `Enter`, `F2`, `CTRL-ALT-DEL`, ...)

## Installation

### HACS

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=pschmitt&repository=homeassistant-pikvm&category=integration)

1. Click the badge above, or open HACS and add `https://github.com/pschmitt/homeassistant-pikvm`
   as a custom repository of type **Integration**.
2. Install **PiKVM**.
3. Restart Home Assistant.

### Manual

Copy `custom_components/pikvm` from this repository into your Home Assistant
`custom_components/pikvm` directory and restart.

## Configuration

The integration is configured from the Home Assistant UI:

1. Go to **Settings → Devices & services**.
2. Add **PiKVM**.
3. Enter the PiKVM host and the kvmd (web UI) credentials.

### SSH features

LEDs, OLED, update status and shutdown require SSH access to the PiKVM host. Provide an
SSH username (default `root`) and the path to a private key readable by Home Assistant
(default `/config/.ssh/id_ed25519`). The matching public key must be in
`/root/.ssh/authorized_keys` on the PiKVM. Disable SSH features in the config flow if you
do not want this.

### Options

- Update interval (default 30 s)
- OCR sensor enable/interval/language
- Keyboard layout of the target (`keymap`, default `de`) used by `pikvm.send_text`

## Service examples

```yaml
service: pikvm.send_text
data:
  text: "echo hello-there\n"
```

```yaml
# Reliable typing into a LUKS prompt
service: pikvm.send_text
data:
  text: !secret luks_passphrase
  slow: true
```

```yaml
service: pikvm.send_key
data:
  key: CTRL-ALT-DEL
```

## License

GPL-3.0. PiKVM and related marks belong to their respective owners.
