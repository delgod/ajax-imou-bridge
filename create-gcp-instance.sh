#!/bin/bash

# GCP Cheapest Instance Creation Script for SIA Bridge
# Creates an e2-micro instance in us-east1 with minimal features

set -e

# Configuration - CHANGE THESE VALUES
PROJECT_ID=$(gcloud config get project)
INSTANCE_NAME="sia-bridge"           # Name for your VM instance
ZONE="us-east1-b"                     # Always Free eligible zone
MACHINE_TYPE="e2-micro"               # Always Free eligible (1 instance/month)
IMAGE_FAMILY="ubuntu-minimal-2404-lts-amd64"        # Free Ubuntu 20.04 LTS
IMAGE_PROJECT="ubuntu-os-cloud"       # Official Ubuntu images
DISK_SIZE="10GB"                      # Minimum disk size (cheapest)
DISK_TYPE="pd-standard"               # Cheapest disk type

# Check if instance already exists
echo "🔍 Checking if instance '$INSTANCE_NAME' already exists..."
if gcloud compute instances describe $INSTANCE_NAME --zone=$ZONE --project=$PROJECT_ID &>/dev/null; then
    echo "✅ Instance '$INSTANCE_NAME' already exists in zone $ZONE"
    echo "ℹ️  Skipping instance creation..."
else
    echo "🚀 Creating new instance '$INSTANCE_NAME'..."
    gcloud compute instances create $INSTANCE_NAME \
        --project=$PROJECT_ID \
        --zone=$ZONE \
        --machine-type=$MACHINE_TYPE \
        --image-family=$IMAGE_FAMILY \
        --image-project=$IMAGE_PROJECT \
        --boot-disk-size=$DISK_SIZE \
        --boot-disk-type=$DISK_TYPE \
        --boot-disk-device-name=$INSTANCE_NAME \
        --no-boot-disk-auto-delete \
        --network-interface=network-tier=STANDARD,subnet=default \
        --no-restart-on-failure \
        --no-service-account \
        --no-scopes \
        --tags=sia-bridge \
        --metadata=enable-oslogin=FALSE 
    echo -e "✅ Instance created successfully!"
fi

# Create firewall rule for SIA bridge port
echo "🔥 Checking/creating firewall rule for port 12128..."
if gcloud compute firewall-rules describe allow-sia-bridge --project=$PROJECT_ID &>/dev/null; then
    echo "✅ Firewall rule 'allow-sia-bridge' already exists"
else
    echo "🚀 Creating firewall rule 'allow-sia-bridge'..."
    gcloud compute firewall-rules create allow-sia-bridge \
        --project=$PROJECT_ID \
        --allow tcp:12128 \
        --source-ranges 0.0.0.0/0 \
        --target-tags sia-bridge \
        --description "Allow SIA DC-09 bridge on port 12128"
    echo "✅ Firewall rule created successfully!"
fi

# Get the external IP
echo "🌐 Getting instance information..."
EXTERNAL_IP=$(gcloud compute instances describe $INSTANCE_NAME --zone=$ZONE --project=$PROJECT_ID --format='get(networkInterfaces[0].accessConfigs[0].natIP)')

echo ""
echo -e "🎉 Instance created successfully!"
echo -e "Instance Details:"
echo "  Project: $PROJECT_ID"
echo "  Name: $INSTANCE_NAME"
echo "  Zone: $ZONE"
echo "  External IP: $EXTERNAL_IP"
echo "  SSH Command: gcloud compute ssh $INSTANCE_NAME --zone=$ZONE"
echo ""

echo -e "💡 Next Steps:"
echo "1. SSH to the instance:"
echo "   gcloud compute ssh $INSTANCE_NAME --zone=$ZONE"
echo ""
echo "2. Install Python and dependencies:"
echo "   sudo apt update && sudo apt install -y python3 python3-pip git"
echo ""
echo "3. Install the SIA Bridge package from PyPI (or GitHub):"
echo "   pip3 install git+https://github.com/delgod/ajax-imou-bridge.git"
echo ""
echo "4. Copy configuration and service files to the correct locations:" 
echo "   sudo cp sia-bridge.conf /etc/sia-bridge.conf"
echo "   sudo cp sia-bridge.service /etc/systemd/system/"
echo ""
echo "5. Enable and start the systemd service:"
echo "   sudo systemctl daemon-reload"
echo "   sudo systemctl enable --now sia-bridge.service"
echo ""
echo "6. Your SIA bridge will be accessible at: $EXTERNAL_IP:12128"
echo ""
