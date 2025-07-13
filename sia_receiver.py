#!/usr/bin/env python3
"""Standalone SIA (Security Industry Association) Protocol Daemon.

This script creates a standalone daemon that listens for SIA alarm system messages
and prints them to stdout. Configuration is read from environment variables.

Environment Variables:
    SIA_PORT: Network port to listen on (default: 12128)
    SIA_ACCOUNT: Account ID (hex string, 3-16 chars)
    SIA_ENCRYPTION_KEY: Encryption key (optional, hex string)

Example usage:
    export SIA_PORT=7777
    export SIA_ACCOUNT="1234"
    export SIA_ENCRYPTION_KEY="abcdef1234567890"
    python sia_daemon.py


"""

import asyncio
import logging
import os
import signal
import sys
from typing import Any, Dict, Optional
from imouapi.api import ImouAPIClient
from imouapi.device import ImouDevice
import aiohttp
from pysiaalarm.aio import CommunicationsProtocol, SIAAccount, SIAClient, SIAEvent


# Global state
client: Optional[SIAClient] = None
running = True
logger = logging.getLogger("sia_daemon")
config = {}


def load_config() -> Dict[str, Any]:
    """Load configuration from environment variables."""
    config = {}

    try:
        config["port"] = int(os.getenv("SIA_PORT", "12128"))
    except ValueError:
        logger.error(f"Invalid port number: {os.getenv('SIA_PORT', '12128')}")
        sys.exit(1)

    config["sia_account_id"] = os.getenv("SIA_ACCOUNT", "000")
    config["sia_encryption_key"] = os.getenv("SIA_ENCRYPTION_KEY")
    config["imou_app_id"] = os.getenv("IMOU_APP_ID")
    config["imou_app_secret"] = os.getenv("IMOU_APP_SECRET")

    if not config.get("imou_app_id") or not config.get("imou_app_secret"):
        logger.error("IMOU_APP_ID and IMOU_APP_SECRET must be set in the environment.")
        sys.exit(1)

    logger.info(
        f"Loaded configuration: port={config['port']}, account={config['sia_account_id']}"
    )

    return config


async def handle_sia_event(event: SIAEvent) -> None:
    """Handle incoming SIA events by printing them to stdout."""
    logger.debug(
        f"Received SIA event: account={event.account}, code={event.code}, "
        f"message={event.message}, zone={event.ri}, "
        f"type={event.sia_code.type if event.sia_code else ''}"
    )
    if event.code in ["CL", "NL"]:
        logger.info("Received ARM event")
        await set_privacy_mode(False)
    elif event.code == "OP":
        logger.info("Received DISARM event")
        await set_privacy_mode(True)


async def set_privacy_mode(mode: bool) -> None:
    """Turn privacy mode on or off for a device."""
    async with aiohttp.ClientSession() as session:
        try:
            logger.info(f"Turning privacy mode {mode}...")
            api_client = ImouAPIClient(
                config["imou_app_id"], config["imou_app_secret"], session
            )
            discovered_devices = await api_client.async_api_deviceBaseList()
            for device in discovered_devices["deviceList"]:
                imou_device = ImouDevice(api_client, device["deviceId"])
                await imou_device.async_initialize()
                closeCamera = imou_device.get_sensor_by_name("closeCamera")
                if closeCamera:
                    if mode:
                        await closeCamera.async_turn_on()
                    else:
                        await closeCamera.async_turn_off()
                device_id = device["deviceId"]
                device_name = device["channels"][0]["channelName"]
                logger.info(f"Device: {device_id} ({device_name}) privacy mode {mode}")
        except Exception as e:
            logger.error(f"An error occurred: {e}")
            sys.exit(1)


async def shutdown() -> None:
    """Shutdown the SIA daemon."""
    global client
    logger.info("Shutting down SIA daemon...")
    if client:
        try:
            await client.async_stop()
            logger.info("SIA client stopped")
        except Exception as e:
            logger.error(f"Error stopping SIA client: {e}")


def signal_handler(signum, frame):
    """Handle shutdown signals."""
    global running
    logger.info(f"Received signal {signum}, shutting down...")
    running = False


async def start_daemon() -> None:
    """Start the SIA daemon."""
    global client, running

    logger.info("Starting SIA daemon...")

    # Create SIA client
    client = SIAClient(
        host="0.0.0.0",  # Listen on all interfaces
        port=config["port"],
        accounts=[
            SIAAccount(
                account_id=config["sia_account_id"],
                key=config["sia_encryption_key"],
                allowed_timeband=(80, 40),
            )
        ],
        function=handle_sia_event,
        protocol=CommunicationsProtocol("TCP"),
    )

    try:
        # Start the SIA client
        await client.async_start(reuse_port=True)
        logger.info(f"SIA daemon started on port {config['port']}")

        # Keep running until stopped
        while running:
            await asyncio.sleep(1)

    except OSError as e:
        logger.error(f"Failed to start SIA server on port {config['port']}: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)
    finally:
        await shutdown()


async def main():
    """Main entry point."""
    global config

    # Setup logging and config
    logging.basicConfig(level=logging.INFO)
    config = load_config()

    # Setup signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        await start_daemon()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
