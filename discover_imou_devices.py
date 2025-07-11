#!/usr/bin/env python3
"""
A simple script to discover and print all devices from an Imou account.

This script uses the imouapi library to connect to the Imou cloud API
and retrieve a list of all associated devices.

Credentials must be provided via environment variables.

Environment Variables:
    IMOU_APP_ID: Your Imou application ID.
    IMOU_APP_SECRET: Your Imou application secret.
"""

import asyncio
import logging
import os
import sys

import aiohttp
from imouapi.api import ImouAPIClient
from imouapi.device import ImouDevice

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    """Connects to the Imou API and prints discovered devices."""
    app_id = os.getenv("IMOU_APP_ID")
    app_secret = os.getenv("IMOU_APP_SECRET")

    if not all([app_id, app_secret]):
        logger.error("Missing required environment variables.")
        logger.error("Please set IMOU_APP_ID and IMOU_APP_SECRET.")
        sys.exit(1)

    async with aiohttp.ClientSession() as session:
        try:
            logger.info("Discovering devices...")
            api_client = ImouAPIClient(app_id, app_secret, session)
            discovered_devices = await api_client.async_api_deviceBaseList()
            for device in discovered_devices["deviceList"]:
                imou_device = ImouDevice(api_client, device["deviceId"])
                await imou_device.async_initialize()
                closeCamera = imou_device.get_sensor_by_name("closeCamera")
                await closeCamera.async_update()
                status = closeCamera.is_on()
                logger.info(f"Device: {device['channels'][0]['channelName']}, Status: {status}")
        except Exception as e:
            logger.error(f"An error occurred: {e}")
            sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\nScript interrupted by user.")
        sys.exit(0) 
