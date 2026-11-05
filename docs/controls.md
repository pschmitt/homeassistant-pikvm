# PiKVM controls

The integration uses the kvmd API for online status, captured-screen camera,
OCR text, CPU temperature, kvmd version, model/hardware identification, stream
reset, ATX power control and keyboard input. The online binary sensor reports
`off` rather than `unavailable` when the API is unreachable. OCR uses the
snapshot endpoint and exposes full results in the `full_text` attribute.
ATX buttons and the target-power binary sensor appear only with ATX enabled.

Optional SSH access enables status LEDs, OLED control, update status and host
shutdown. Enter an SSH username (default `root`) and a private-key file path
readable by Home Assistant (default `/config/.ssh/id_ed25519`). Authorize the
matching public key on the PiKVM host, or disable SSH features in the config
flow if they are not needed. The update interval defaults to 30 seconds;
OCR enablement, interval and language and the keyboard keymap (default `de`)
are configurable in the options.

## Keyboard actions

Use `pikvm.send_text` to type through the virtual keyboard:

```yaml
action: pikvm.send_text
data:
  text: "hello there"
```

Set `slow: true` to type character by character when early-boot prompts do
not accept text sent all at once. Use `pikvm.send_key` for an individual key:

```yaml
action: pikvm.send_key
data:
  key: CTRL-ALT-DEL
```
