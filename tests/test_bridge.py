#!/usr/bin/env python3
"""
Simple CLI tool to test the SIA Bridge.
Sends ARM (CL) or DISARM (OP) events.
"""

import argparse
import logging
import socket
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def crc_calc(msg: str) -> str:
    """Calculate the CRC of the msg."""
    crc = 0
    for letter in str.encode(msg):
        temp = letter
        for _ in range(0, 8):
            temp ^= crc & 1
            crc >>= 1
            if (temp & 1) != 0:
                crc ^= 0xA001
            temp >>= 1
    return ("%x" % crc).upper().zfill(4)


def create_sia_message(account_id: str, code: str) -> bytes:
    """Creates a SIA message."""
    timestamp = datetime.utcnow().strftime("_%H:%M:%S,%m-%d-%Y")

    # Zone 1, User 1. The message part of the content for CL/OP is the user id.
    # The sia_bridge doesn't use it, but good to have a valid message.
    message_part = "1"
    content = f"|Nri1/{code}{message_part}"

    sequence = "0001"
    receiver = "R0"
    line = "L0"

    message_body_content = f"[{content}]{timestamp}"
    message_body_prefix = f'"SIA-DCS"{sequence}{receiver}{line}#{account_id}'

    message_body = f"{message_body_prefix}{message_body_content}"

    crc = crc_calc(message_body)
    length = f"{len(message_body):04x}".upper()

    full_message = f"\n{crc}{length}{message_body}\r"
    return full_message.encode("ascii")


def send_sia_event(host: str, port: int, message: bytes):
    """Sends a SIA event and prints the response."""
    logging.info("Connecting to %s:%s", host, port)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.connect((host, port))
            logging.info("Sending message: %s", message.decode("ascii").strip())
            sock.sendall(message)
            response = sock.recv(1024)
            logging.info("Received response: %s", response.decode("ascii").strip())
        except ConnectionRefusedError:
            logging.error("Connection refused. Is the SIA bridge running?")
        except Exception as e:
            logging.error("An error occurred: %s", e)


def main():
    """Main function to run the CLI tool."""
    parser = argparse.ArgumentParser(description="SIA Bridge Test Tool")
    parser.add_argument(
        "command", choices=["arm", "disarm"], help="Command to send to the bridge."
    )
    parser.add_argument("--host", default="127.0.0.1", help="SIA Bridge host.")
    parser.add_argument("--port", type=int, default=12128, help="SIA Bridge port.")
    parser.add_argument("--account", default="000", help="SIA account ID.")

    args = parser.parse_args()

    if args.command == "arm":
        sia_code = "CL"
    else:  # disarm
        sia_code = "OP"

    message = create_sia_message(args.account, sia_code)
    send_sia_event(args.host, args.port, message)


if __name__ == "__main__":
    main()
