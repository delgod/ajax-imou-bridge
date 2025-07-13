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

# Get the location of installed package files
PACKAGE_DIR=$(python3 -c "import site; print(site.getsitepackages()[0])")

# Copy executable
install -D -m 755 sia_bridge.py /usr/local/bin/sia_bridge.py

# Copy service file (try from current directory first, then from installed package)
if [ -f "sia-bridge.service" ]; then
    install -D -m 644 sia-bridge.service /etc/systemd/system/sia-bridge.service
elif [ -f "$PACKAGE_DIR/sia-bridge.service" ]; then
    install -D -m 644 "$PACKAGE_DIR/sia-bridge.service" /etc/systemd/system/sia-bridge.service
else
    echo "  Warning: sia-bridge.service not found in current directory or installed package"
fi

# Copy config file (try from current directory first, then from installed package)
if [ ! -f /etc/sia-bridge.conf ]; then
    if [ -f "sia-bridge.conf" ]; then
        install -D -m 644 sia-bridge.conf /etc/sia-bridge.conf
    elif [ -f "$PACKAGE_DIR/sia-bridge.conf" ]; then
        install -D -m 644 "$PACKAGE_DIR/sia-bridge.conf" /etc/sia-bridge.conf
    else
        echo "  Warning: sia-bridge.conf not found in current directory or installed package"
    fi
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
