from datetime import datetime, timedelta, timezone
import importlib.util
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

LAMBDA_FILE = (
    Path(__file__).resolve().parents[2] / "cloud" / "lambda" / "lambda_function.py"
)


def load_lambda_module():
    spec = importlib.util.spec_from_file_location(
        "homepulse_lambda",
        LAMBDA_FILE,
    )

    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load Lambda module from {LAMBDA_FILE}")

    module = importlib.util.module_from_spec(spec)

    mock_table = MagicMock()
    mock_dynamodb = MagicMock()
    mock_dynamodb.Table.return_value = mock_table
    mock_cloudwatch = MagicMock()

    with (
        patch.dict(
            "os.environ",
            {
                "DYNAMODB_TABLE": "homepulse-network-metrics",
                "METRIC_NAMESPACE": "HomePulse",
                "ALLOWED_DEVICES": "homepulse-agent-01",
            },
            clear=False,
        ),
        patch("boto3.resource", return_value=mock_dynamodb),
        patch("boto3.client", return_value=mock_cloudwatch),
    ):
        spec.loader.exec_module(module)

    module.table = mock_table
    module.cloudwatch = mock_cloudwatch

    return module


def valid_event():
    timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    return {
        "schema_version": "1.0",
        "device_id": "homepulse-agent-01",
        "timestamp": timestamp,
        "network": {
            "internet": {
                "reachable": True,
                "packet_loss_percent": 0.0,
            },
            "livebox": {
                "reachable": True,
            },
            "miwifi": {
                "reachable": True,
            },
            "dns": {
                "success": True,
            },
        },
        "system": {
            "cpu_percent": 18.5,
            "memory_percent": 42.0,
            "disk_percent": 61.2,
        },
    }


def test_lambda_handler_accepts_valid_device():
    module = load_lambda_module()

    result = module.lambda_handler(valid_event(), None)

    assert result["statusCode"] == 200
    module.table.put_item.assert_called_once()
    module.cloudwatch.put_metric_data.assert_called()


def test_lambda_handler_rejects_unknown_device():
    module = load_lambda_module()

    event = valid_event()
    event["device_id"] = "unknown-device"

    with pytest.raises(
        ValueError,
        match="Unknown or missing device_id",
    ):
        module.lambda_handler(event, None)

    module.table.put_item.assert_not_called()
    module.cloudwatch.put_metric_data.assert_not_called()


def test_lambda_handler_rejects_missing_device_id():
    module = load_lambda_module()

    event = valid_event()
    del event["device_id"]

    with pytest.raises(
        ValueError,
        match="Unknown or missing device_id",
    ):
        module.lambda_handler(event, None)

    module.table.put_item.assert_not_called()
    module.cloudwatch.put_metric_data.assert_not_called()


def test_lambda_handler_rejects_stale_timestamp():
    module = load_lambda_module()

    event = valid_event()
    event["timestamp"] = (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat()

    with pytest.raises(
        ValueError,
        match="Timestamp is more than 24 hours",
    ):
        module.lambda_handler(event, None)

    module.table.put_item.assert_not_called()
    module.cloudwatch.put_metric_data.assert_not_called()


def test_lambda_handler_rejects_missing_network():
    module = load_lambda_module()

    event = valid_event()
    del event["network"]

    with pytest.raises(
        ValueError,
        match="Missing or invalid 'network' object",
    ):
        module.lambda_handler(event, None)

    module.table.put_item.assert_not_called()
    module.cloudwatch.put_metric_data.assert_not_called()


def test_lambda_handler_rejects_missing_system():
    module = load_lambda_module()

    event = valid_event()
    del event["system"]

    with pytest.raises(
        ValueError,
        match="Missing or invalid 'system' object",
    ):
        module.lambda_handler(event, None)

    module.table.put_item.assert_not_called()
    module.cloudwatch.put_metric_data.assert_not_called()
