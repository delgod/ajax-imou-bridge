#!/bin/bash
# A very simple script to install the SIA receiver daemon.

set -e

# 1. Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root" 
   exit 1
fi

echo "Installing SIA receiver service..."

# 2. Install files
echo "  -> Copying files..."
install -D -m 755 sia_receiver.py /usr/local/bin/sia_receiver.py
install -D -m 644 sia-receiver.conf /etc/sia-receiver.conf
install -D -m 644 sia-receiver.service /etc/systemd/system/sia-receiver.service

# 3. Reload systemd, enable and start the service
echo "  -> Starting systemd service..."
systemctl daemon-reload
systemctl enable --now sia-receiver.service

echo ""
echo "Installation complete!"
echo "To check the status, run: systemctl status sia-receiver.service"
echo "To view logs, run: journalctl -u sia-receiver.service -f"
echo "Configuration file is at: /etc/sia-receiver.conf" 