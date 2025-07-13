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
import json
import logging
import os
import signal
import sys
from datetime import datetime
from typing import Any, Dict, Optional
from pysiaalarm.aio import CommunicationsProtocol, SIAAccount, SIAClient, SIAEvent


# Global state
client: Optional[SIAClient] = None
running = True
logger = logging.getLogger("sia_daemon")


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
    
    logger.info(f"Loaded configuration: port={config['port']}, account={config['sia_account_id']}")
    
    return config


def get_sia_account(config: Dict[str, Any]) -> SIAAccount:
    """Create SIAAccount object from configuration."""
    default_timeband = (80, 40)  # Default timeband from HA component
    
    try:
        account = SIAAccount(
            account_id=config["sia_account_id"],
            key=config["sia_encryption_key"],
            allowed_timeband=default_timeband
        )
        logger.info(f"Got SIA account: {config['sia_account_id']} with timestamp validation enabled")
        return account
    except Exception as e:
        logger.error(f"Failed to get SIA account {config['account_id']}: {e}")
        sys.exit(1)


async def handle_sia_event(event: SIAEvent) -> None:
    """Handle incoming SIA events by printing them to stdout."""
    logger.debug(f"Received SIA event: account={event.account}, code={event.code}, "
                 f"message={event.message}, zone={event.ri}, "
                 f"type={event.sia_code.type if event.sia_code else ''}")
    if event.code in ["CL", "NL"]:
        logger.info(f"Received ARM event: {event}")
    elif event.code == "OP":
        logger.info(f"Received DISARM event: {event}")


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
    
    # Load configuration
    config = load_config()
    
    # Create SIA account
    sia_account = get_sia_account(config)
    
    # Create SIA client
    client = SIAClient(
        host="0.0.0.0",  # Listen on all interfaces
        port=config["port"],
        accounts=[sia_account],
        function=handle_sia_event,
        protocol=CommunicationsProtocol("TCP")
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
    # Setup logging
    logging.basicConfig(level=logging.DEBUG)
    
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