"""Async client for the PiKVM (kvmd) HTTP and WebSocket API."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp

from .const import DEFAULT_REQUEST_TIMEOUT

_LOGGER = logging.getLogger(__name__)

# Aliases for the kvmd web key names, mostly for backwards compatibility
# with the legacy pikvm.sh "sendtext-slow --special" interface.
KEY_ALIASES: dict[str, str] = {
    "ESC": "Escape",
    "ESCAPE": "Escape",
    "ENTER": "Enter",
    "RETURN": "Enter",
    "TAB": "Tab",
    "SPACE": "Space",
    "BACKSPACE": "Backspace",
    "DEL": "Delete",
    "DELETE": "Delete",
    "CTRL-ALT-DEL": "ctrl-alt-del",
    "CTRL+ALT+DEL": "ctrl-alt-del",
}

# QWERTZ fixup: kvmd web key names are layout-agnostic key positions, so on
# a German target keymap the Y and Z positions are swapped.
QWERTZ_SWAP = {"z": "y", "y": "z", "Z": "Y", "Y": "Z"}


class PiKVMApiError(Exception):
    """Raised when the PiKVM API cannot be reached or returns an error."""


class PiKVMAuthError(PiKVMApiError):
    """Raised when the PiKVM API rejects the credentials."""


def char_to_web_key(char: str, keymap: str) -> tuple[str, bool] | None:
    """Map a character to a (kvmd web key, needs shift) tuple.

    Returns None for characters that cannot be typed via key events.
    """
    if keymap.startswith("de"):
        char = QWERTZ_SWAP.get(char, char)

    if char == "\n":
        return ("Enter", False)
    if char == "\t":
        return ("Tab", False)
    if char == " ":
        return ("Space", False)
    if char == ".":
        return ("Period", False)
    if char == ",":
        return ("Comma", False)
    if char.isdigit():
        return (f"Digit{char}", False)
    if char.isalpha() and char.isascii():
        return (f"Key{char.upper()}", char.isupper())
    return None


class PiKVMApiClient:
    """Minimal async client for the kvmd API."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        host: str,
        username: str,
        password: str,
    ) -> None:
        """Initialize the client."""
        self._session = session
        self.host = host
        self.base_url = f"https://{host}"
        self._headers = {
            "X-KVMD-User": username,
            "X-KVMD-Passwd": password,
        }

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, str] | None = None,
        data: bytes | None = None,
    ) -> aiohttp.ClientResponse:
        """Perform an authenticated request against the kvmd API."""
        url = f"{self.base_url}{path}"
        try:
            response = await self._session.request(
                method,
                url,
                params=params,
                data=data,
                headers=self._headers,
                timeout=aiohttp.ClientTimeout(total=DEFAULT_REQUEST_TIMEOUT),
            )
        except (TimeoutError, aiohttp.ClientError, OSError) as err:
            raise PiKVMApiError(f"Error talking to {url}: {err}") from err

        if response.status in (401, 403):
            raise PiKVMAuthError(f"Authentication failed for {url}")
        if response.status >= 400:
            body = await response.text()
            raise PiKVMApiError(
                f"{method} {path} failed with HTTP {response.status}: {body[:200]}"
            )
        return response

    async def _request_json(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Perform a request and return the kvmd result payload."""
        response = await self._request(method, path, params=params)
        try:
            payload: dict[str, Any] = await response.json(content_type=None)
        except (aiohttp.ClientError, ValueError) as err:
            raise PiKVMApiError(f"Invalid JSON from {path}: {err}") from err

        if not payload.get("ok", True):
            raise PiKVMApiError(f"{path} returned ok=false: {payload}")
        result = payload.get("result", payload)
        if not isinstance(result, dict):
            raise PiKVMApiError(f"Unexpected payload from {path}: {payload}")
        return result

    async def async_get_info(self) -> dict[str, Any]:
        """Return the kvmd info payload."""
        return await self._request_json("GET", "/api/info")

    async def async_get_atx(self) -> dict[str, Any]:
        """Return the ATX state."""
        return await self._request_json("GET", "/api/atx")

    async def async_atx_power(self, action: str) -> None:
        """Send an ATX power action (on, off, off_hard, reset_hard)."""
        await self._request("POST", "/api/atx/power", params={"action": action})

    async def async_send_text(self, text: str, keymap: str) -> None:
        """Type text via the HID print endpoint."""
        await self._request(
            "POST",
            "/api/hid/print",
            params={"limit": "0", "keymap": keymap},
            data=text.encode(),
        )

    async def async_get_snapshot(self) -> bytes:
        """Return the current streamer snapshot as JPEG bytes."""
        response = await self._request(
            "GET",
            "/api/streamer/snapshot",
            params={"allow_offline": "1"},
        )
        return await response.read()

    async def async_get_ocr(self, lang: str) -> str:
        """Run OCR on the current screen content.

        The streamer only captures while at least one client is connected,
        so a short-lived WebSocket session is kept open during the snapshot.
        """
        async with self._ws_connect(stream=True) as ws:
            del ws
            # Give the streamer a moment to start capturing
            await asyncio.sleep(1)
            response = await self._request(
                "GET",
                "/api/streamer/snapshot",
                params={"ocr": "1", "lang": lang},
            )
            return (await response.text()).strip()

    async def async_reset(self) -> None:
        """Reset the streamer and the HID subsystem."""
        for path in ("/api/streamer/reset", "/api/hid/reset"):
            await self._request("POST", path)

    def _ws_connect(self, stream: bool = False):  # noqa: ANN202 - aiohttp WS ctx
        """Open a WebSocket session against the kvmd event API.

        With stream=True the session declares interest in the video stream,
        which makes kvmd start the streamer (required for OCR/snapshots).
        """
        return self._session.ws_connect(
            f"{self.base_url}/api/ws",
            params={"stream": "1" if stream else "0"},
            headers=self._headers,
        )

    @staticmethod
    async def _ws_send_key(
        ws: aiohttp.ClientWebSocketResponse,
        key: str,
        state: bool,
    ) -> None:
        """Send a single key event."""
        await ws.send_json({"event_type": "key", "event": {"key": key, "state": state}})

    async def _ws_press_key(
        self,
        ws: aiohttp.ClientWebSocketResponse,
        key: str,
        delay: float,
    ) -> None:
        """Press and release a key."""
        await self._ws_send_key(ws, key, True)
        await asyncio.sleep(delay)
        await self._ws_send_key(ws, key, False)

    async def async_send_key(self, key: str, delay: float = 0.2) -> None:
        """Press and release a single (special) key.

        Accepts kvmd web key names (Escape, Enter, KeyA, F2, ...) plus a few
        friendly aliases (ESC, ENTER, CTRL-ALT-DEL, ...).
        """
        key = KEY_ALIASES.get(key.strip().upper(), key.strip())
        try:
            async with self._ws_connect() as ws:
                if key == "ctrl-alt-del":
                    await self._ws_send_key(ws, "ControlLeft", True)
                    await self._ws_send_key(ws, "AltLeft", True)
                    await self._ws_press_key(ws, "Delete", delay)
                    await self._ws_send_key(ws, "AltLeft", False)
                    await self._ws_send_key(ws, "ControlLeft", False)
                else:
                    await self._ws_press_key(ws, key, delay)
        except (TimeoutError, aiohttp.ClientError, OSError) as err:
            raise PiKVMApiError(f"Error sending key {key}: {err}") from err

    async def async_send_text_slow(
        self,
        text: str,
        keymap: str,
        delay: float = 1.0,
    ) -> None:
        """Type text character by character via key events.

        Slower but much more reliable than the print endpoint, e.g. for
        typing passphrases into early-boot prompts.
        """
        try:
            async with self._ws_connect() as ws:
                for char in text:
                    mapped = char_to_web_key(char, keymap)
                    if mapped is None:
                        _LOGGER.warning(
                            "Skipping character %r: cannot map to a key event", char
                        )
                        continue
                    key, shift = mapped
                    if shift:
                        await self._ws_send_key(ws, "ShiftLeft", True)
                        await asyncio.sleep(delay / 2)
                    await self._ws_press_key(ws, key, delay)
                    if shift:
                        await asyncio.sleep(delay / 2)
                        await self._ws_send_key(ws, "ShiftLeft", False)
        except (TimeoutError, aiohttp.ClientError, OSError) as err:
            raise PiKVMApiError(f"Error typing text: {err}") from err
