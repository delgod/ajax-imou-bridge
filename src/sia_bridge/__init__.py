#!/usr/bin/env python3
"""
Standalone SIA (Security Industry Association) Protocol daemon.

This script listens for SIA events and toggles privacy mode on Imou cameras
accordingly. Configuration is sourced from environment variables for easy
containerisation / deployment.

Environment Variables
---------------------
BIND_IP               IP address to bind the SIA TCP server to    (default: 0.0.0.0)
BIND_PORT             Port to bind the SIA TCP server             (default: 12128)
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

LOGGER_NAME = "sia_bridge"
logger = logging.getLogger(LOGGER_NAME)


# ---------------------------------------------------------------------------
# Configuration helpers
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Config:
    """Runtime configuration object populated from environment variables."""

    bind_ip: str
    bind_port: int
    sia_account_id: str
    sia_encryption_key: Optional[str]
    imou_app_id: str
    imou_app_secret: str
    log_level: str

    @classmethod
    def from_env(cls) -> "Config":
        """Build a :class:`Config` instance using environment variables."""
        try:
            bind_port = int(os.getenv("BIND_PORT", "12128"))
        except ValueError as exc:
            logger.error("Invalid BIND_PORT value: %s", os.environ.get("BIND_PORT"))
            raise SystemExit(1) from exc

        bind_ip = os.getenv("BIND_IP", "0.0.0.0")  # nosec B104
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
            bind_ip=bind_ip,
            bind_port=bind_port,
            sia_account_id=sia_account_id,
            sia_encryption_key=sia_encryption_key,
            imou_app_id=imou_app_id,
            imou_app_secret=imou_app_secret,
            log_level=log_level_str,
        )


# ---------------------------------------------------------------------------
# Core receiver implementation
# ---------------------------------------------------------------------------


class SIABridge:
    """Async context manager wrapping :class:`pysiaalarm.aio.SIAClient`."""

    def __init__(self, config: Config) -> None:
        self._cfg = config
        self._client: Optional[SIAClient] = None
        self._stop_event = asyncio.Event()
        self._privacy_lock = asyncio.Lock()

    # ---------------------------------------------------------------------
    # Async context-manager helpers
    # ---------------------------------------------------------------------

    async def __aenter__(self) -> "SIABridge":
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

        # Log initial camera state before starting the server.
        await self._run_imou_action("privacy_check")

        self._client = SIAClient(  # type: ignore[abstract]
            host=self._cfg.bind_ip,
            port=self._cfg.bind_port,
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
        if self._client is None:
            raise RuntimeError("SIAClient has not been initialized.")

        logger.info(
            "Starting SIA TCP server on %s:%d", self._cfg.bind_ip, self._cfg.bind_port
        )
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

    async def _run_imou_action(self, action: str) -> None:
        """Run an Imou action for all devices."""
        if action not in ("privacy_on", "privacy_off", "privacy_check"):
            raise ValueError(f"Unknown action: {action}")
        logger.info("Running Imou action: %s", action)
        try:
            async with aiohttp.ClientSession() as session:
                api_client = ImouAPIClient(
                    self._cfg.imou_app_id, self._cfg.imou_app_secret, session
                )
                devices = await api_client.async_api_deviceBaseList()

                if not devices.get("deviceList"):
                    logger.warning("No Imou devices found.")
                    return

                for device_data in devices.get("deviceList", []):
                    device_id = device_data["deviceId"]
                    channel_name = device_data.get("channels", [{}])[0].get(
                        "channelName", "<unknown>"
                    )
                    try:
                        imou_device = ImouDevice(api_client, device_id)
                        await imou_device.async_initialize()

                        await imou_device.async_refresh_status()
                        if not imou_device.is_online():
                            logger.info(
                                "Device %s (%s) is offline - skipping",
                                device_id,
                                channel_name,
                            )
                            continue

                        privacy_switch = imou_device.get_sensor_by_name("closeCamera")
                        if privacy_switch is None:
                            logger.debug(
                                "Device %s (%s) lacks privacy switch - skipping",
                                device_id,
                                channel_name,
                            )
                            continue

                        if action == "privacy_on":
                            await privacy_switch.async_turn_on()  # type: ignore[attr-defined]
                        elif action == "privacy_off":
                            await privacy_switch.async_turn_off()  # type: ignore[attr-defined]
                        elif action == "privacy_check":
                            await privacy_switch.async_update()
                        else:
                            raise ValueError(f"Unknown action: {action}")

                        # The sensor `is_on()` method returns a boolean.
                        state = "ON" if privacy_switch.is_on() else "OFF"  # type: ignore[attr-defined]
                        logger.info(
                            "Device %s (%s) -> privacy mode: %s",
                            device_id,
                            channel_name,
                            state,
                        )
                    except Exception as exc:
                        logger.error(
                            "Error checking device %s (%s): %s - continuing with other devices",
                            device_id,
                            channel_name,
                            exc,
                        )
                        continue
        except Exception as exc:
            logger.error("Failed to check camera states: %s", exc)

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
            await self._run_imou_action("privacy_off")
        elif event.code == "OP":  # DISARM
            logger.info("Handling DISARM event -> enabling privacy mode")
            await self._run_imou_action("privacy_on")

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
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------


async def _async_main() -> None:
    """Async entrypoint used by :pyfunc:`asyncio.run`."""
    cfg = Config.from_env()
    configure_logging(cfg.log_level)
    receiver = SIABridge(cfg)

    # Install signal handlers for graceful shutdown.
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, receiver.request_shutdown, sig)

    async with receiver:
        await receiver.run_forever()


def show_config_files() -> None:  # pragma: no cover
    """Show the location of configuration files included in the package."""
    try:
        # Use importlib.resources.files to get a traversable object for the package
        # In this case, for a top-level module, we refer to it directly.
        from importlib.resources import files

        service_file = files("sia_bridge").joinpath("sia-bridge.service")
        config_file = files("sia_bridge").joinpath("sia-bridge.conf")
    except (ImportError, AttributeError):
        # Fallback for older Python versions if needed, though requires-python>=3.9
        # should make this unnecessary.
        print(
            "Error: Could not locate packaged data files. Please ensure you are using Python 3.9+.",
            file=sys.stderr,
        )
        sys.exit(1)

    print("SIA Bridge configuration files location:")
    print(f"  Service file: {service_file}")
    print(f"  Config file:  {config_file}")
    print()
    print("To install these files to system locations (example paths):")
    print(f"  sudo cp {service_file} /etc/systemd/system/")
    print(f"  sudo cp {config_file} /etc/sia-bridge.conf")
    print()
    print("To add IMOU_APP_ID and IMOU_APP_SECRET to the configuration file:")
    print("   sudo vim /etc/sia-bridge.conf")
    print()
    print("Then enable and start the service:")
    print("  sudo systemctl daemon-reload")
    print("  sudo systemctl enable --now sia-bridge.service")


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
