"""SSH helper for PiKVM system-level features (LEDs, OLED, updates, shutdown)."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

import asyncssh

from .const import DEFAULT_SSH_TIMEOUT

_LOGGER = logging.getLogger(__name__)

# One round trip per coordinator refresh: everything in a single command.
STATUS_COMMAND = (
    "test -e /var/lib/pacman/db.lck && echo updating=1 || echo updating=0; "
    "grep -q '\\[none\\]' /sys/class/leds/led*/trigger && echo leds=0 || echo leds=1; "
    "systemctl --quiet is-active kvmd-oled && echo oled=1 || echo oled=0"
)
LEDS_ON_COMMAND = (
    "echo mmc0 > /sys/class/leds/led0/trigger; "
    "echo default-on > /sys/class/leds/led1/trigger"
)
LEDS_OFF_COMMAND = (
    "echo 0 | tee /sys/class/leds/led0/brightness /sys/class/leds/led1/brightness "
    ">/dev/null; "
    "echo none | tee /sys/class/leds/led0/trigger /sys/class/leds/led1/trigger "
    ">/dev/null"
)
OLED_ON_COMMAND = "systemctl restart kvmd-oled kvmd-oled-reboot kvmd-oled-shutdown"
OLED_OFF_COMMAND = (
    "kvmd-oled --height=32 --interval=5 --clear-on-exit --text='turning off'; "
    "systemctl stop kvmd-oled kvmd-oled-reboot kvmd-oled-shutdown"
)
SHUTDOWN_COMMAND = "shutdown -h now"


class PiKVMSshError(Exception):
    """Raised when an SSH command fails."""


@dataclass
class PiKVMSshStatus:
    """SSH-sourced state of the PiKVM host."""

    updating: bool | None = None
    leds_on: bool | None = None
    oled_on: bool | None = None


class PiKVMSshClient:
    """Run commands on the PiKVM host over SSH."""

    def __init__(
        self,
        host: str,
        username: str,
        port: int,
        key_path: str | None,
        timeout: float = DEFAULT_SSH_TIMEOUT,
    ) -> None:
        """Initialize the SSH client."""
        self._host = host
        self._username = username
        self._port = port
        self._key_path = key_path
        self._timeout = timeout

    async def async_run(self, command: str) -> str:
        """Run a command and return its stdout."""
        try:
            async with asyncio.timeout(self._timeout):
                async with asyncssh.connect(
                    self._host,
                    port=self._port,
                    username=self._username,
                    client_keys=[self._key_path] if self._key_path else None,
                    known_hosts=None,
                ) as conn:
                    result = await conn.run(command)
        except (TimeoutError, OSError, asyncssh.Error) as err:
            raise PiKVMSshError(f"SSH command failed on {self._host}: {err}") from err

        stdout = result.stdout or ""
        return stdout if isinstance(stdout, str) else stdout.decode()

    async def async_get_status(self) -> PiKVMSshStatus:
        """Fetch update/LED/OLED status in a single SSH round trip."""
        output = await self.async_run(STATUS_COMMAND)
        status = PiKVMSshStatus()
        for line in output.splitlines():
            key, _, value = line.strip().partition("=")
            if key == "updating":
                status.updating = value == "1"
            elif key == "leds":
                status.leds_on = value == "1"
            elif key == "oled":
                status.oled_on = value == "1"
        return status

    async def async_set_leds(self, enabled: bool) -> None:
        """Toggle the Raspberry Pi status LEDs."""
        await self.async_run(LEDS_ON_COMMAND if enabled else LEDS_OFF_COMMAND)

    async def async_set_oled(self, enabled: bool) -> None:
        """Toggle the kvmd OLED screen services."""
        await self.async_run(OLED_ON_COMMAND if enabled else OLED_OFF_COMMAND)

    async def async_shutdown(self) -> None:
        """Shut down the PiKVM host."""
        await self.async_run(SHUTDOWN_COMMAND)
