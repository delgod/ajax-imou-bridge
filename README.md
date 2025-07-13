# SIA-BRIDGE(1) - SIA Protocol Bridge for Ajax/Imou Integration

## NAME

sia-bridge - Security Industry Association (SIA) protocol bridge daemon for Ajax alarm systems and Imou camera privacy mode control

## SYNOPSIS

```
sia-bridge
```

## DESCRIPTION

The SIA Bridge is a production-grade daemon that implements the SIA DC-09 protocol receiver, providing seamless integration between Ajax security systems and Imou cloud cameras. The bridge monitors alarm system state changes via SIA protocol and automatically toggles camera privacy mode based on system arm/disarm events.

This implementation follows UNIX philosophy: do one thing well, with minimal dependencies and maximum reliability.

## FEATURES

* **SIA DC-09 Protocol Support** - Full implementation of the Security Industry Association Contact ID protocol
* **Asynchronous I/O** - Built on Python's asyncio for efficient concurrent connection handling
* **Zero Downtime Operation** - Graceful shutdown with SIGTERM/SIGINT signal handling
* **Secure by Default** - Runs as unprivileged user with systemd security hardening
* **Container Ready** - Twelve-factor app principles with environment-based configuration
* **Production Hardened** - Comprehensive error handling and automatic reconnection logic

## ARCHITECTURE

```
┌─────────────┐      SIA Protocol       ┌──────────────┐      HTTPS API      ┌─────────────┐
│ Ajax Panel  │ ──────────────────────► │  SIA Bridge  │ ──────────────────► │ Imou Cloud  │
│             │      TCP Port 12128      │   (Daemon)   │                     │   Cameras   │
└─────────────┘                          └──────────────┘                     └─────────────┘
       │                                         │                                     │
       └─── ARM Event (CL/NL) ──────────────────┼──── Disable Privacy Mode ──────────┘
       └─── DISARM Event (OP) ──────────────────┼──── Enable Privacy Mode ───────────┘
```

## SYSTEM REQUIREMENTS

### Minimum Requirements

* Python 3.9 or higher
* Linux kernel 3.10+ (systemd 219+)
* 64 MB RAM
* 10 MB disk space
* Network connectivity to Imou cloud services
* Open TCP port 12128 for SIA protocol

### Python Dependencies

* aiohttp >= 3.9.0 - Asynchronous HTTP client
* pysiaalarm >= 0.6.0 - SIA protocol implementation
* imouapi >= 0.3.2 - Imou cloud API client

## QUICK START

### Package Installation

```bash
sudo pip3 install --break-system-packages git+https://github.com/delgod/ajax-imou-bridge.git
```

### Configuration

```bash
sudo cp /usr/local/lib/python3.*/dist-packages/sia_bridge/sia-bridge.conf /etc/sia-bridge.conf
sudo cp /usr/local/lib/python3.*/dist-packages/sia_bridge/sia-bridge.service /etc/systemd/system/
```

Edit `/etc/sia-bridge.conf`:

```bash
SIA_PORT=12128
SIA_ACCOUNT=000
IMOU_APP_ID=<your_app_id_here>
IMOU_APP_SECRET=<your_app_secret_here>
LOG_LEVEL=INFO
```

### Service Management

```bash
# Enable and start the service
sudo systemctl daemon-reload
sudo systemctl enable --now sia-bridge.service

# View logs
sudo journalctl -u sia-bridge.service -f
```

## CONFIGURATION

Configuration follows the twelve-factor app methodology using environment variables:

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `SIA_PORT` | TCP port for SIA protocol listener | 12128 | No |
| `SIA_ACCOUNT` | SIA account ID (3-16 hex chars) | 000 | No |
| `SIA_ENCRYPTION_KEY` | Optional SIA encryption key | None | No |
| `IMOU_APP_ID` | Imou cloud application ID | None | Yes |
| `IMOU_APP_SECRET` | Imou cloud application secret | None | Yes |
| `LOG_LEVEL` | Python logging level | INFO | No |

## PROTOCOL MAPPING

The bridge implements the following SIA event code mappings:

| SIA Code | Event Type | Camera Action |
|----------|------------|---------------|
| CL | Close (ARM) | Disable privacy mode |
| NL | Night Mode (ARM) | Disable privacy mode |
| OP | Opening (DISARM) | Enable privacy mode |

All other SIA event codes are logged but not acted upon.

## SECURITY CONSIDERATIONS

### SystemD Hardening

The provided service unit implements defense-in-depth security:

* Runs as `nobody:nogroup` unprivileged user
* Private `/tmp` with `PrivateTmp=true`
* Read-only filesystem with `ProtectSystem=strict`
* No access to home directories with `ProtectHome=true`
* Restricted system calls with `SystemCallFilter=@system-service`
* Memory write-execute protection with `MemoryDenyWriteExecute=true`

### Network Security

* Bind to specific interface recommended for production
* Consider firewall rules limiting source IPs to alarm panel only
* Use SIA encryption key when supported by alarm panel
* Imou API credentials should be protected with appropriate file permissions

## FILES

* `/usr/local/bin/sia-bridge` - Main executable
* `/etc/sia-bridge.conf` - Environment configuration
* `/etc/systemd/system/sia-bridge.service` - SystemD service unit
* `/var/log/journal/*/sia-bridge.service` - Service logs (via journald)

## DIAGNOSTICS

The daemon logs all significant events to syslog/journald with the identifier `sia-bridge`.

### Debug Mode

Enable verbose logging for troubleshooting:

```bash
# In /etc/sia-bridge.conf
LOG_LEVEL=DEBUG
```

### Common Issues

1. **Connection Refused** - Verify firewall rules and port availability
2. **Authentication Failed** - Check Imou API credentials
3. **No Devices Found** - Ensure cameras support privacy mode feature

## EXIT STATUS

* 0 - Successful termination
* 1 - Configuration or runtime error
* 130 - Interrupted by SIGINT (Ctrl-C)
* 143 - Terminated by SIGTERM

## STANDARDS CONFORMANCE

This implementation conforms to:

* SIA DC-09 Digital Communication Standard
* RFC 3164 - BSD Syslog Protocol
* SystemD Integration Standards
* Python PEP 8 Style Guide

## AUTHORS

Mykola Marzhan <delgod@delgod.com>

## COPYRIGHT

Copyright © 2024 Mykola Marzhan. Licensed under the Apache License, Version 2.0.

## SEE ALSO

* [Ajax Systems](https://ajax.systems/) - Professional security systems
* [Imou Cloud](https://www.imoulife.com/) - Smart home camera platform
* [SIA Standards](https://www.securityindustry.org/) - Security Industry Association

## REPORTING BUGS

Report bugs to: https://github.com/delgod/ajax-imou-bridge/issues

When reporting bugs, include:
* System configuration (OS, Python version)
* Complete error messages and stack traces
* Relevant log entries with DEBUG level
* Steps to reproduce the issue

## CONTRIBUTING

Contributions are welcome. Please read [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

Code submissions must:
* Include appropriate test coverage
* Follow PEP 8 style guidelines
* Update documentation as needed
* Sign-off commits per Developer Certificate of Origin

---

Last updated: December 2024 
