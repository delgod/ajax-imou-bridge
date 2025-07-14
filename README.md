# Ajax Imou Bridge

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0) [![Python](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/) [![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black) [![Security: bandit](https://img.shields.io/badge/security-bandit-yellow.svg)](https://github.com/PyCQA/bandit) [![GitHub issues](https://img.shields.io/github/issues/delgod/ajax-imou-bridge)](https://github.com/delgod/ajax-imou-bridge/issues) [![GitHub last commit](https://img.shields.io/github/last-commit/delgod/ajax-imou-bridge)](https://github.com/delgod/ajax-imou-bridge/commits/)
<!--
[![PyPI Version](https://img.shields.io/pypi/v/sia-bridge.svg)](https://pypi.org/project/sia-bridge/)
[![Build Status](https://img.shields.io/github/actions/workflow/status/delgod/ajax-imou-bridge/main.yml?branch=main)](https://github.com/delgod/ajax-imou-bridge/actions)
<img src="https://codecov.io/gh/delgod/ajax-imou-bridge/branch/main/graph/badge.svg" alt="Coverage"/>
-->

A robust and reliable bridge that connects Ajax security systems with Imou cameras, automatically managing camera privacy settings based on the alarm's armed state.

This daemon listens for arming and disarming events from an Ajax Hub via the SIA DC-09 protocol. It then toggles the privacy mode on your Imou cameras accordingly: when the system is armed, camera recording is activated; when disarmed, privacy mode is re-enabled, ensuring cameras are active only when necessary.

## Architecture

```
┌──────────┐      SIA Protocol       ┌──────────────┐      HTTPS API      ┌─────────────┐
│ Ajax Hub │ ──────────────────────► │  SIA Bridge  │ ──────────────────► │ Imou Cloud  │
│          │                         │   (Daemon)   │                     │   Cameras   │
└──────────┘                         └──────────────┘                     └─────────────┘
     │                                      │                                    │
     └─── ARM Event (CL/NL) ────────────────┼──── Disable Privacy Mode ──────────┘
     └─── DISARM Event (OP) ────────────────┼──── Enable Privacy Mode ───────────┘
```

## Features

*   **SIA DC-09 Protocol Receiver**
*   **Asynchronous & Lightweight**
*   **Reliable and Robust**

## Prerequisites

*   Python 3.9+
*   An Ajax Hub with access to its configuration settings.
*   One or more Imou cameras that support Privacy Mode.
*   [Imou Developer API credentials](https://open.imoulife.com/consoleNew/myApp/appInfo).


### Create Imou API Credentials

1.  Go to the [Imou Developer Portal](https://open.imoulife.com) and sign in with your Imou account.
2.  Navigate to [Control Board](https://open.imoulife.com/consoleNew/myApp/appInfo) and select "My Applications".
3.  Create an application to obtain your App ID and App Secret. Store these credentials in a secure location.

### Ajax Hub Configuration

Follow the [official Ajax documentation](https://support.ajax.systems/en/how-to-use-sia-for-cms-connection/) to configure your Hub to send alarm events to the bridge.

To configure the Hub, you will need administrator privileges for the Ajax system.

1.  In the Ajax mobile application, navigate to **Hub Settings** → **Security Companies** → **Monitoring Station**.
2.  Set the following parameters:
    *   **Ethernet**: Enable if the Hub can reach the bridge over a local network.
    *   **Cellular**: Enable if the Hub can reach the bridge over the internet via a public IP address.
    *   **IP address**: The IP address of the server where the bridge is running.
    *   **Port**: The `BIND_PORT` you have configured (e.g., `12128`).
    *   **Monitoring station ping interval**: Set as required.
    *   **Object number**: The `SIA_ACCOUNT` you have configured.
    *   **Encryption key**: The `SIA_ENCRYPTION_KEY` if you are using one.
3.  Click "**< Back**" to save the settings and wait for the "**Monitoring station**" status to show "**Connected**".


## Configuration
| Variable | Description | Validation | Default | Required |
| :--- | :--- | :--- | :--- | :--- |
| `BIND_PORT` | The TCP port for the SIA listener. | 1-49151 | 12128 | Yes |
| `BIND_IP` | The IP address to listen on for SIA protocol messages. | IPv4/IPv6 address | 0.0.0.0 | No |
| `SIA_ACCOUNT` | The SIA account identifier, as configured in your Ajax Hub. | 3-16 hex chars | 000 | Yes |
| `SIA_ENCRYPTION_KEY` | The optional SIA encryption key. Must match the key in your Ajax Hub. | 16 or 32 hex chars| None | No |
| `IMOU_APP_ID` | Your application ID from the Imou Developer Portal. | | None | Yes |
| `IMOU_APP_SECRET` | Your application secret from the Imou Developer Portal. | | None | Yes |
| `LOG_LEVEL` | Logging level. | `DEBUG` or `INFO` | INFO | No |

## Running as a Docker (recommended)
```bash
docker run -d \
    --name sia-bridge \
    --restart unless-stopped \
    -p 12128:12128 \
    -e BIND_PORT=12128 \
    -e SIA_ACCOUNT="000" \
    -e IMOU_APP_ID="<your_app_id>" \
    -e IMOU_APP_SECRET="<your_app_secret>" \
    ghcr.io/delgod/sia-bridge:latest
```
See configuration section above.

## Running as a Service (not recommended)
**Note**: Using `sudo pip` is strongly discouraged as it can lead to system dependency conflicts.

* **Install pip package**
    ```bash
    sudo pip3 install --break-system-packages git+https://github.com/delgod/ajax-imou-bridge.git
    ```
* **Deploy service files**
    ```bash
    sudo cp /usr/local/lib/python3.*/dist-packages/sia_bridge/sia-bridge.conf /etc/sia-bridge.conf
    sudo cp /usr/local/lib/python3.*/dist-packages/sia_bridge/sia-bridge.service /etc/systemd/system/
    ```
- Open `/etc/sia-bridge.conf` with a text editor and provide your specific details. This file sets the environment variables used by the service.

    ```ini
    # /etc/sia-bridge.conf

    BIND_PORT=12128
    SIA_ACCOUNT=000
    SIA_ENCRYPTION_KEY=
    IMOU_APP_ID=
    IMOU_APP_SECRET=
    LOG_LEVEL=
    ```
    See configuration section above.
- **Reload systemd and Enable the Service:**
    ```bash
    sudo systemctl daemon-reload
    sudo systemctl enable --now sia-bridge.service
    ```
- **Check the Service Status:**
    ```bash
    sudo systemctl status sia-bridge.service
    ```
* **View Logs:**
    Follow the service logs in real-time to monitor events.
    ```bash
    sudo journalctl -u sia-bridge.service -f
    ```


## Diagnostics

To enable verbose logging for troubleshooting, set `LOG_LEVEL=DEBUG` and restart the service/docker.

**Common Issues:**

*   **Connection Refused**: Check your firewall rules and ensure the `BIND_PORT` is open on the host running the bridge, allowing inbound connections from your Ajax Hub.
*   **Authentication Failed**: Double-check your `IMOU_APP_ID` and `IMOU_APP_SECRET`.
*   **No Devices Found**: Ensure your cameras are online, controllable in your Imou Life application and support the privacy mode feature.

## Reporting Bugs

Please report any bugs or issues on the [GitHub Issues page](https://github.com/delgod/ajax-imou-bridge/issues).

When reporting bugs, please include:

*   Steps to reproduce the issue.
*   Your system configuration (OS, Python version).
*   The complete error message and stack trace.
*   Relevant log entries with `LOG_LEVEL=DEBUG`.
