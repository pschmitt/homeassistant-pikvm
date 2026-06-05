"""Constants for the PiKVM integration."""

from __future__ import annotations

from homeassistant.const import Platform

DOMAIN = "pikvm"
PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.CAMERA,
    Platform.SENSOR,
    Platform.SWITCH,
]

CONF_SSH_ENABLED = "ssh_enabled"
CONF_SSH_USERNAME = "ssh_username"
CONF_SSH_PORT = "ssh_port"
CONF_SSH_KEY_PATH = "ssh_key_path"
CONF_OCR_ENABLED = "ocr_enabled"
CONF_OCR_SCAN_INTERVAL = "ocr_scan_interval"
CONF_OCR_LANG = "ocr_lang"
CONF_KEYMAP = "keymap"

DEFAULT_VERIFY_SSL = False
DEFAULT_SSH_ENABLED = True
DEFAULT_SSH_USERNAME = "root"
DEFAULT_SSH_PORT = 22
DEFAULT_SSH_KEY_PATH = "/config/.ssh/id_ed25519"
DEFAULT_SCAN_INTERVAL = 30
MIN_SCAN_INTERVAL = 10
DEFAULT_OCR_ENABLED = True
DEFAULT_OCR_SCAN_INTERVAL = 30
DEFAULT_OCR_LANG = "eng"
DEFAULT_KEYMAP = "de"
DEFAULT_REQUEST_TIMEOUT = 20
DEFAULT_SSH_TIMEOUT = 15

ATTR_FULL_TEXT = "full_text"

SERVICE_SEND_TEXT = "send_text"
SERVICE_SEND_KEY = "send_key"

ATTR_TEXT = "text"
ATTR_KEY = "key"
ATTR_SLOW = "slow"
ATTR_DELAY = "delay"
ATTR_KEYMAP = "keymap"
ATTR_DEVICE_ID = "device_id"

# Maximum entity state length is 255; leave some headroom.
OCR_STATE_MAX_LENGTH = 250
