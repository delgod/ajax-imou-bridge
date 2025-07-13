#!/usr/bin/env python3
"""
Standalone SIA (Security Industry Association) Protocol daemon.

This script listens for SIA events and toggles privacy mode on Imou cameras
accordingly. Configuration is sourced from environment variables for easy
containerisation / deployment.

Environment Variables
---------------------
SIA_PORT              Port to bind the SIA TCP server             (default: 12128)
SIA_ACCOUNT           SIA account identifier (3-16 hex chars)     (default: "000")
SIA_ENCRYPTION_KEY    Optional SIA encryption key (hex string)
IMOU_APP_ID           Imou cloud application id                   (required)
IMOU_APP_SECRET       Imou cloud application secret               (required)
LOG_LEVEL             Python logging level (DEBUG, INFO ...)      (default: INFO)
"""

from __future__ import annotations

import asyncio
import logging
import os
import signal
import sys
from dataclasses import dataclass
from typing import Optional

import aiohttp
from imouapi.api import ImouAPIClient
from imouapi.device import ImouDevice
from pysiaalarm.aio import CommunicationsProtocol, SIAAccount, SIAEvent
from pysiaalarm.aio.client import SIAClient

LOGGER_NAME = "sia_receiver"
logger = logging.getLogger(LOGGER_NAME)


# ---------------------------------------------------------------------------
# Configuration helpers
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Config:
    """Runtime configuration object populated from environment variables."""

    port: int
    sia_account_id: str
    sia_encryption_key: Optional[str]
    imou_app_id: str
    imou_app_secret: str
    log_level: str

    @classmethod
    def from_env(cls) -> "Config":
        """Build a :class:`Config` instance using environment variables."""
        try:
            port = int(os.getenv("SIA_PORT", "12128"))
        except ValueError as exc:
            logger.error("Invalid SIA_PORT value: %s", os.environ.get("SIA_PORT"))
            raise SystemExit(1) from exc

        sia_account_id = os.getenv("SIA_ACCOUNT", "000")
        sia_encryption_key = os.getenv("SIA_ENCRYPTION_KEY")
        log_level_str = os.getenv("LOG_LEVEL", "INFO").upper()
        imou_app_id = os.getenv("IMOU_APP_ID")
        imou_app_secret = os.getenv("IMOU_APP_SECRET")

        if not imou_app_id or not imou_app_secret:
            logger.error(
                "Environment variables IMOU_APP_ID and IMOU_APP_SECRET are required."
            )
            raise SystemExit(1)

        return cls(
            port=port,
            sia_account_id=sia_account_id,
            sia_encryption_key=sia_encryption_key,
            imou_app_id=imou_app_id,
            imou_app_secret=imou_app_secret,
            log_level=log_level_str,
        )


# ---------------------------------------------------------------------------
# Core receiver implementation
# ---------------------------------------------------------------------------


class SIAReceiver:
    """Async context manager wrapping :class:`pysiaalarm.aio.SIAClient`."""

    def __init__(self, config: Config) -> None:
        self._cfg = config
        self._client: Optional[SIAClient] = None
        self._stop_event = asyncio.Event()
        self._privacy_lock = asyncio.Lock()

    # ---------------------------------------------------------------------
    # Async context-manager helpers
    # ---------------------------------------------------------------------

    async def __aenter__(self) -> "SIAReceiver":
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.stop()

    # ---------------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------------

    async def start(self) -> None:
        """Initialise and start the SIA TCP server."""
        if self._client is not None:
            logger.warning("Receiver already started - ignoring second start() call")
            return

        self._client = SIAClient(  # type: ignore[abstract]
            host="0.0.0.0",
            port=self._cfg.port,
            accounts=[
                SIAAccount(
                    account_id=self._cfg.sia_account_id,
                    key=self._cfg.sia_encryption_key,
                    allowed_timeband=(80, 40),
                )
            ],
            function=self._handle_sia_event,  # callback
            protocol=CommunicationsProtocol("TCP"),
        )

        # Tell type checkers `_client` is definitely assigned from here on.
        assert self._client is not None

        logger.info("Starting SIA TCP server on port %d", self._cfg.port)
        await self._client.async_start(reuse_port=True)
        logger.info("SIA TCP server started - waiting for events...")

    async def stop(self) -> None:
        """Stop the SIA server and clean up resources."""
        if self._client is None:
            return  # Nothing to do

        logger.info("Stopping SIA TCP server ...")
        await self._client.async_stop()
        self._client = None
        logger.info("SIA TCP server stopped")

    async def run_forever(self) -> None:
        """Block until :pyattr:`_stop_event` is set, then shut down."""
        await self._stop_event.wait()

    # ---------------------------------------------------------------------
    # Internal helpers
    # ---------------------------------------------------------------------

    async def _handle_sia_event(self, event: SIAEvent) -> None:  # noqa: D401
        """Async callback processing inbound SIA events."""
        details = (
            "account=%s, code=%s, message=%s, zone=%s, type=%s",
            event.account,
            event.code,
            event.message,
            event.ri,
            event.sia_code.type if event.sia_code else "",
        )
        logger.debug("Received SIA event: " + details[0], *details[1:])

        # Map SIA codes to privacy mode state.
        if event.code in {"CL", "NL"}:  # ARM
            logger.info("Handling ARM event -> disabling privacy mode")
            await self._set_privacy_mode(False)
        elif event.code == "OP":  # DISARM
            logger.info("Handling DISARM event -> enabling privacy mode")
            await self._set_privacy_mode(True)

    async def _set_privacy_mode(self, enabled: bool) -> None:
        """Toggle Imou camera privacy mode.

        Serialised via an instance-level asyncio.Lock so that only one
        privacy-mode operation can run at a time, even if multiple SIA
        events arrive in quick succession.
        """

        async with self._privacy_lock:
            mode_str = "ON" if enabled else "OFF"
            logger.info("Toggling camera privacy mode: %s", mode_str)

            async with aiohttp.ClientSession() as session:
                api_client = ImouAPIClient(
                    self._cfg.imou_app_id, self._cfg.imou_app_secret, session
                )
                devices = await api_client.async_api_deviceBaseList()

                for device in devices.get("deviceList", []):
                    imou_device = ImouDevice(api_client, device["deviceId"])
                    await imou_device.async_initialize()

                    privacy_switch = imou_device.get_sensor_by_name("closeCamera")
                    if privacy_switch is None:
                        logger.debug(
                            "Device %s lacks privacy switch - skipping", device["deviceId"]
                        )
                        continue

                    if enabled:
                        await privacy_switch.async_turn_on()  # type: ignore[attr-defined]
                    else:
                        await privacy_switch.async_turn_off()  # type: ignore[attr-defined]

                    channel_name = device.get("channels", [{}])[0].get(
                        "channelName", "<unknown>"
                    )
                    logger.info(
                        "Device %s (%s) -> privacy mode %s",
                        device["deviceId"],
                        channel_name,
                        mode_str,
                    )

    # ---------------------------------------------------------------------
    # Signal handling helpers
    # ---------------------------------------------------------------------

    def request_shutdown(self, signum: int) -> None:  # noqa: D401
        """Signal handler that schedules receiver shutdown."""
        logger.info("Received signal %d - commencing shutdown", signum)
        self._stop_event.set()


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------


def configure_logging(log_level_str: str) -> None:
    """Configure root logger using provided log level string from Config."""
    try:
        level = getattr(logging, log_level_str.upper(), logging.INFO)
    except AttributeError:
        level = logging.INFO

    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------


async def _async_main() -> None:
    """Async entrypoint used by :pyfunc:`asyncio.run`."""
    cfg = Config.from_env()
    configure_logging(cfg.log_level)
    receiver = SIAReceiver(cfg)

    # Install signal handlers for graceful shutdown.
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, receiver.request_shutdown, sig)

    async with receiver:
        await receiver.run_forever()


def main() -> None:  # pragma: no cover
    """Synchronous wrapper starting the asyncio event loop."""
    try:
        asyncio.run(_async_main())
    except KeyboardInterrupt:
        # Already handled via signal, but catch to avoid stacktrace when Ctrl-C is pressed early.
        logger.info("Interrupted by user - exiting")
    except Exception as exc:  # broad exception acceptable for top-level guard
        logger.exception("Fatal error: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
