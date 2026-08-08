import json
import logging
from datetime import datetime, timedelta, timezone
import importlib.util
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError, EndpointConnectionError

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
                "RETENTION_DAYS": "90",
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


def client_error(
    operation_name: str,
    code: str,
    message: str,
) -> ClientError:
    return ClientError(
        error_response={
            "Error": {
                "Code": code,
                "Message": message,
            },
            "ResponseMetadata": {
                "RequestId": "aws-test-request",
                "HTTPStatusCode": 400,
            },
        },
        operation_name=operation_name,
    )


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


def test_lambda_json_formatter_produces_structured_log():
    module = load_lambda_module()
    formatter = module.JsonFormatter()

    record = logging.LogRecord(
        name="homepulse.ingestion",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="telemetry_processing_succeeded",
        args=(),
        exc_info=None,
    )

    record.request_id = "test-request-id"
    record.device_id = "homepulse-agent-01"
    record.metric_count = 11

    parsed_log = json.loads(formatter.format(record))

    assert parsed_log["level"] == "INFO"
    assert parsed_log["event"] == "telemetry_processing_succeeded"
    assert parsed_log["request_id"] == "test-request-id"
    assert parsed_log["device_id"] == "homepulse-agent-01"
    assert parsed_log["metric_count"] == 11
    assert "timestamp" in parsed_log


def test_unknown_device_logs_validation_failure():
    module = load_lambda_module()

    event = valid_event()
    event["device_id"] = "unknown-device"

    with patch.object(module.LOGGER, "warning") as mock_warning:
        with pytest.raises(
            ValueError,
            match="Unknown or missing device_id",
        ):
            module.lambda_handler(event, None)

    mock_warning.assert_called_once()

    log_event = mock_warning.call_args.args[0]
    log_fields = mock_warning.call_args.kwargs["extra"]

    assert log_event == "telemetry_validation_failed"
    assert log_fields["device_id"] == "unknown-device"
    assert log_fields["error_type"] == "ValueError"


def test_lambda_handler_reraises_dynamodb_failure():
    module = load_lambda_module()

    module.table.put_item.side_effect = client_error(
        operation_name="PutItem",
        code="AccessDeniedException",
        message="Access denied",
    )

    with patch.object(module.LOGGER, "exception") as mock_exception:
        with pytest.raises(ClientError):
            module.lambda_handler(valid_event(), None)

    module.cloudwatch.put_metric_data.assert_not_called()

    mock_exception.assert_called_once()

    assert mock_exception.call_args.args[0] == ("dynamodb_write_failed")

    fields = mock_exception.call_args.kwargs["extra"]

    assert fields["aws_error_code"] == "AccessDeniedException"
    assert fields["table_name"] == "homepulse-network-metrics"


def test_lambda_handler_reraises_cloudwatch_failure():
    module = load_lambda_module()

    module.cloudwatch.put_metric_data.side_effect = client_error(
        operation_name="PutMetricData",
        code="AccessDenied",
        message="CloudWatch access denied",
    )

    with patch.object(module.LOGGER, "exception") as mock_exception:
        with pytest.raises(ClientError):
            module.lambda_handler(valid_event(), None)

    module.table.put_item.assert_called_once()
    module.cloudwatch.put_metric_data.assert_called_once()

    matching_calls = [
        call
        for call in mock_exception.call_args_list
        if call.args[0] == "cloudwatch_publish_failed"
    ]

    assert len(matching_calls) == 1

    fields = matching_calls[0].kwargs["extra"]

    assert fields["aws_error_code"] == "AccessDenied"
    assert fields["metric_namespace"] == "HomePulse"


def test_lambda_handler_handles_cloudwatch_connection_failure():
    module = load_lambda_module()

    module.cloudwatch.put_metric_data.side_effect = EndpointConnectionError(
        endpoint_url="https://monitoring.eu-central-1.amazonaws.com"
    )

    with patch.object(module.LOGGER, "exception") as mock_exception:
        with pytest.raises(EndpointConnectionError):
            module.lambda_handler(valid_event(), None)

    matching_calls = [
        call
        for call in mock_exception.call_args_list
        if call.args[0] == "cloudwatch_publish_failed"
    ]

    assert len(matching_calls) == 1


def test_calculate_expiration_timestamp_uses_retention_days():
    module = load_lambda_module()

    telemetry_time = datetime(
        2026,
        8,
        4,
        12,
        0,
        tzinfo=timezone.utc,
    )

    expiration = module.calculate_expiration_timestamp(telemetry_time)

    expected = int((telemetry_time + timedelta(days=90)).timestamp())

    assert expiration == expected


def test_lambda_stores_expiration_timestamp():
    module = load_lambda_module()
    event = valid_event()

    module.lambda_handler(event, None)

    module.table.put_item.assert_called_once()

    stored_item = module.table.put_item.call_args.kwargs["Item"]

    assert "expires_at" in stored_item
    assert isinstance(stored_item["expires_at"], int)


def test_lambda_does_not_add_expiration_to_input_event():
    module = load_lambda_module()
    event = valid_event()

    module.lambda_handler(event, None)

    assert "expires_at" not in event


def test_stored_expiration_is_90_days_after_telemetry():
    module = load_lambda_module()
    event = valid_event()

    module.lambda_handler(event, None)

    stored_item = module.table.put_item.call_args.kwargs["Item"]

    telemetry_time = datetime.fromisoformat(event["timestamp"].replace("Z", "+00:00"))

    expected_expiration = int((telemetry_time + timedelta(days=90)).timestamp())

    assert stored_item["expires_at"] == expected_expiration


def test_lambda_publishes_agent_heartbeat():
    module = load_lambda_module()

    module.lambda_handler(valid_event(), None)

    module.cloudwatch.put_metric_data.assert_called_once()

    call_arguments = module.cloudwatch.put_metric_data.call_args.kwargs

    assert call_arguments["Namespace"] == "HomePulse"

    metric_data = call_arguments["MetricData"]

    heartbeat_metrics = [
        metric for metric in metric_data if metric["MetricName"] == "AgentHeartbeat"
    ]

    assert len(heartbeat_metrics) == 1

    heartbeat = heartbeat_metrics[0]

    assert heartbeat["Value"] == 1.0
    assert heartbeat["Unit"] == "Count"
    assert heartbeat["Dimensions"] == [
        {
            "Name": "DeviceId",
            "Value": "homepulse-agent-01",
        }
    ]
