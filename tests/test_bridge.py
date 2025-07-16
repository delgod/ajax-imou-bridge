#!/usr/bin/env python3
"""
Simple CLI tool to test the SIA Bridge.
Sends ARM (CL) or DISARM (OP) events.
"""

from unittest.mock import AsyncMock, MagicMock, patch
import logging
import signal

import pytest
from sia_bridge import SIABridge, Config, configure_logging, show_config_files, main

# pylint: disable=redefined-outer-name, unused-argument


@pytest.fixture
def mock_config():
    """Provides a mock Config object for tests."""
    return Config(
        bind_port=12345,
        bind_ip="0.0.0.0",
        sia_account_id="test_account",
        sia_encryption_key=None,
        imou_app_id="test_app_id",
        imou_app_secret="test_app_secret",
        log_level="DEBUG",
    )


@pytest.fixture
def mock_sia_client():
    """Provides a mock SIAClient."""
    with patch("sia_bridge.SIAClient", new_callable=MagicMock) as mock_client:
        mock_client.return_value.async_start = AsyncMock()
        mock_client.return_value.async_stop = AsyncMock()
        yield mock_client


@pytest.fixture
def mock_aiohttp_session():
    """Provides a mock aiohttp ClientSession."""
    with patch("sia_bridge.aiohttp.ClientSession") as mock_session_cls:
        mock_session = MagicMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session_cls.return_value = mock_session
        yield mock_session


@pytest.fixture
def mock_imou_api():
    """Provides a mock ImouAPIClient and related objects."""
    with patch("sia_bridge.ImouAPIClient") as mock_api:
        # Mock the API client and its device list method
        mock_api.return_value.async_api_deviceBaseList = AsyncMock(
            return_value={
                "deviceList": [
                    {
                        "deviceId": "test_device_1",
                        "channels": [{"channelName": "Cam 1"}],
                    }
                ]
            }
        )

        # Mock the ImouDevice and its sensors
        with patch("sia_bridge.ImouDevice") as mock_device:
            privacy_switch = MagicMock()
            privacy_switch.async_turn_on = AsyncMock()
            privacy_switch.async_turn_off = AsyncMock()
            privacy_switch.async_update = AsyncMock()
            privacy_switch.is_on = MagicMock(return_value=False)

            mock_device.return_value.async_initialize = AsyncMock()
            mock_device.return_value.async_refresh_status = AsyncMock()
            mock_device.return_value.is_online = MagicMock(return_value=True)
            mock_device.return_value.get_sensor_by_name = MagicMock(
                return_value=privacy_switch
            )
            yield {
                "api_client": mock_api,
                "device": mock_device,
                "privacy_switch": privacy_switch,
            }


@pytest.fixture
def bridge(mock_config, mock_sia_client, mock_imou_api, mock_aiohttp_session):
    """Provides an SIABridge instance with mocked dependencies."""
    return SIABridge(mock_config)


@pytest.mark.asyncio
async def test_start_and_stop(bridge, mock_sia_client, mock_imou_api):
    """Verify that start and stop call the underlying client methods."""
    # Patch the run_imou_action to avoid running it here
    with patch.object(bridge, "_run_imou_action", new_callable=AsyncMock):
        await bridge.start()
        mock_sia_client.return_value.async_start.assert_awaited_once()

        await bridge.stop()
        mock_sia_client.return_value.async_stop.assert_awaited_once()


@pytest.mark.asyncio
async def test_run_imou_action_privacy_check(bridge, mock_imou_api, mock_aiohttp_session):
    """Verify that privacy_check action logs the current camera state."""
    await bridge._run_imou_action("privacy_check")

    # Verify API was called
    api_client = mock_imou_api["api_client"]
    api_client.return_value.async_api_deviceBaseList.assert_awaited_once()

    # Verify device methods were called
    device = mock_imou_api["device"]
    device.return_value.async_initialize.assert_awaited_once()
    device.return_value.async_refresh_status.assert_awaited_once()
    device.return_value.is_online.assert_called_once()
    device.return_value.get_sensor_by_name.assert_called_with("closeCamera")

    # Verify state was updated and checked
    privacy_switch = mock_imou_api["privacy_switch"]
    privacy_switch.async_update.assert_awaited_once()
    privacy_switch.is_on.assert_called_once()


@pytest.mark.asyncio
async def test_run_imou_action_privacy_on(bridge, mock_imou_api, mock_aiohttp_session):
    """Verify that privacy_on action enables privacy mode."""
    await bridge._run_imou_action("privacy_on")

    privacy_switch = mock_imou_api["privacy_switch"]
    privacy_switch.async_turn_on.assert_awaited_once()
    privacy_switch.async_turn_off.assert_not_awaited()


@pytest.mark.asyncio
async def test_run_imou_action_privacy_off(bridge, mock_imou_api, mock_aiohttp_session):
    """Verify that privacy_off action disables privacy mode."""
    await bridge._run_imou_action("privacy_off")

    privacy_switch = mock_imou_api["privacy_switch"]
    privacy_switch.async_turn_off.assert_awaited_once()
    privacy_switch.async_turn_on.assert_not_awaited()


@pytest.mark.asyncio
async def test_run_imou_action_unknown_action(bridge, mock_imou_api, mock_aiohttp_session):
    """Verify that unknown action values raise ValueError."""
    with pytest.raises(ValueError) as exc:
        await bridge._run_imou_action("unknown_action")
    assert "Unknown action: unknown_action" in str(exc.value)


@pytest.mark.asyncio
async def test_handle_sia_event_arm(bridge):
    """Verify an ARM event (CL) disables privacy mode."""
    with patch.object(bridge, "_run_imou_action", new_callable=AsyncMock) as mock_action:
        mock_event = MagicMock(code="CL", sia_code=MagicMock(type="ARM"))
        await bridge._handle_sia_event(mock_event)
        mock_action.assert_awaited_once_with("privacy_off")


@pytest.mark.asyncio
async def test_handle_sia_event_arm_nl(bridge):
    """Verify an ARM event (NL) disables privacy mode."""
    with patch.object(bridge, "_run_imou_action", new_callable=AsyncMock) as mock_action:
        mock_event = MagicMock(code="NL", sia_code=MagicMock(type="ARM"))
        await bridge._handle_sia_event(mock_event)
        mock_action.assert_awaited_once_with("privacy_off")


@pytest.mark.asyncio
async def test_handle_sia_event_disarm(bridge):
    """Verify a DISARM event (OP) enables privacy mode."""
    with patch.object(bridge, "_run_imou_action", new_callable=AsyncMock) as mock_action:
        mock_event = MagicMock(code="OP", sia_code=MagicMock(type="DISARM"))
        await bridge._handle_sia_event(mock_event)
        mock_action.assert_awaited_once_with("privacy_on")


@pytest.mark.asyncio
async def test_handle_sia_event_unknown(bridge):
    """Verify an unknown event code is ignored."""
    with patch.object(bridge, "_run_imou_action", new_callable=AsyncMock) as mock_action:
        mock_event = MagicMock(code="XX", sia_code=MagicMock(type="UNKNOWN"))
        await bridge._handle_sia_event(mock_event)
        mock_action.assert_not_awaited()


@pytest.mark.asyncio
async def test_run_imou_action_no_devices(bridge, mock_imou_api, mock_aiohttp_session, caplog):
    """Verify behavior when no Imou devices are found."""
    mock_imou_api["api_client"].return_value.async_api_deviceBaseList.return_value = {
        "deviceList": []
    }
    with caplog.at_level(logging.WARNING):
        await bridge._run_imou_action("privacy_check")
        assert "No Imou devices found" in caplog.text


@pytest.mark.asyncio
async def test_run_imou_action_api_error(bridge, mock_imou_api, mock_aiohttp_session, caplog):
    """Verify behavior when the Imou API call fails."""
    mock_imou_api[
        "api_client"
    ].return_value.async_api_deviceBaseList.side_effect = Exception("API Failure")
    with caplog.at_level(logging.ERROR):
        await bridge._run_imou_action("privacy_check")
        assert "Failed to check camera states: API Failure" in caplog.text


@pytest.mark.asyncio
async def test_run_imou_action_device_error(bridge, mock_imou_api, mock_aiohttp_session, caplog):
    """Verify behavior when a specific device fails to initialize."""
    mock_imou_api["device"].return_value.async_initialize.side_effect = Exception(
        "Device Failure"
    )
    with caplog.at_level(logging.ERROR):
        await bridge._run_imou_action("privacy_check")
        assert (
            "Error checking device test_device_1 (Cam 1): Device Failure - continuing with other devices" in caplog.text
        )


@pytest.mark.asyncio
async def test_run_imou_action_device_offline(bridge, mock_imou_api, mock_aiohttp_session, caplog):
    """Verify behavior when a device is offline."""
    mock_imou_api["device"].return_value.is_online.return_value = False
    with caplog.at_level(logging.INFO):
        await bridge._run_imou_action("privacy_check")
        assert "is offline - skipping" in caplog.text


@pytest.mark.asyncio
async def test_run_imou_action_no_privacy_switch(
    bridge, mock_imou_api, mock_aiohttp_session, caplog
):
    """Verify behavior for a device without a privacy switch."""
    mock_imou_api["device"].return_value.get_sensor_by_name.return_value = None
    with caplog.at_level(logging.DEBUG):
        await bridge._run_imou_action("privacy_check")
        assert "lacks privacy switch - skipping" in caplog.text
    mock_imou_api["privacy_switch"].async_update.assert_not_called()


def test_config_from_env_valid(monkeypatch):
    """Test config loading with valid environment variables."""
    monkeypatch.setenv("BIND_PORT", "1234")
    monkeypatch.setenv("SIA_ACCOUNT", "my_account")
    monkeypatch.setenv("IMOU_APP_ID", "my_app_id")
    monkeypatch.setenv("IMOU_APP_SECRET", "my_app_secret")

    config = Config.from_env()
    assert config.bind_port == 1234
    assert config.sia_account_id == "my_account"
    assert config.imou_app_id == "my_app_id"


def test_config_from_env_missing_required(monkeypatch):
    """Test config loading with missing required environment variables."""
    # Unset a required variable
    monkeypatch.delenv("IMOU_APP_ID", raising=False)
    monkeypatch.delenv("IMOU_APP_SECRET", raising=False)
    with pytest.raises(SystemExit):
        Config.from_env()


def test_config_from_env_invalid_port(monkeypatch):
    """Test config loading with an invalid port value."""
    monkeypatch.setenv("BIND_PORT", "not-a-number")
    monkeypatch.setenv("IMOU_APP_ID", "my_app_id")
    monkeypatch.setenv("IMOU_APP_SECRET", "my_app_secret")
    with pytest.raises(SystemExit):
        Config.from_env()


@pytest.mark.parametrize(
    "level_str, expected_level",
    [
        ("DEBUG", logging.DEBUG),
        ("INFO", logging.INFO),
        ("warning", logging.WARNING),
        ("ERROR", logging.ERROR),
        ("INVALID", logging.INFO),
        ("", logging.INFO),
    ],
)
@patch("logging.basicConfig")
def test_configure_logging(mock_basic_config, level_str, expected_level):
    """Verify that logging is configured with the correct level."""
    configure_logging(level_str)
    mock_basic_config.assert_called_once()
    _, kwargs = mock_basic_config.call_args
    assert kwargs["level"] == expected_level


def test_request_shutdown(bridge):
    """Test the signal handler for shutdown requests."""
    assert not bridge._stop_event.is_set()
    bridge.request_shutdown(signal.SIGINT)
    assert bridge._stop_event.is_set()


@pytest.mark.asyncio
async def test_main_loop(mocker):
    """Test the main async entrypoint and graceful shutdown."""
    mock_asyncio_run = mocker.patch("asyncio.run")
    mock_main = mocker.patch("sia_bridge._async_main", new_callable=MagicMock)

    main()
    mock_asyncio_run.assert_called_once_with(mock_main())

    # Test KeyboardInterrupt
    mock_asyncio_run.reset_mock()
    mock_asyncio_run.side_effect = KeyboardInterrupt
    main()  # Should not raise

    # Test other exceptions
    mock_asyncio_run.reset_mock()
    mock_asyncio_run.side_effect = Exception("test error")
    with pytest.raises(SystemExit):
        main()


def test_show_config_files(capsys):
    """Test the utility function for showing config file paths."""
    show_config_files()
    captured = capsys.readouterr()
    assert "sia-bridge.service" in captured.out
    assert "sia-bridge.conf" in captured.out
