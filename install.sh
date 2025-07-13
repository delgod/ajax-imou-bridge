#!/bin/bash
# A very simple script to install the SIA bridge service.

set -e

# 1. Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root"
   exit 1
fi

echo "Installing SIA bridge service..."

# 2. Install files
echo "  -> Copying files..."
install -D -m 755 sia_bridge.py /usr/local/bin/sia_bridge.py
install -D -m 644 sia-bridge.service /etc/systemd/system/sia-bridge.service
if [ ! -f /etc/sia-bridge.conf ]; then
    install -D -m 644 sia-bridge.conf /etc/sia-bridge.conf
fi

# 3. Reload systemd, enable and start the service
echo "  -> Starting systemd service..."
systemctl daemon-reload
systemctl enable --now sia-bridge.service

echo ""
echo "Installation complete!"
echo "To check the status, run: systemctl status sia-bridge.service"
echo "To view logs, run: journalctl -u sia-bridge.service -f"
echo "Configuration file is at: /etc/sia-bridge.conf"
