"""HomePulse telemetry ingestion Lambda.

Receives validated telemetry from AWS IoT Core, stores the complete payload
in Amazon DynamoDB, and publishes selected measurements as Amazon CloudWatch
custom metrics.
"""

import json
import logging
import os
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import boto3

TABLE_NAME = os.environ["DYNAMODB_TABLE"]
METRIC_NAMESPACE = os.getenv("METRIC_NAMESPACE", "HomePulse")

ALLOWED_DEVICES = {
    device_id.strip()
    for device_id in os.getenv(
        "ALLOWED_DEVICES",
        "homepulse-agent-01",
    ).split(",")
    if device_id.strip()
}


class JsonFormatter(logging.Formatter):
    """Format Lambda application logs as JSON."""

    RESERVED_FIELDS = {
        "args",
        "asctime",
        "created",
        "exc_info",
        "exc_text",
        "filename",
        "funcName",
        "levelname",
        "levelno",
        "lineno",
        "module",
        "msecs",
        "message",
        "msg",
        "name",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "thread",
        "threadName",
        "taskName",
    }

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "event": record.getMessage(),
            "logger": record.name,
        }

        for key, value in record.__dict__.items():
            if key not in self.RESERVED_FIELDS and not key.startswith("_"):
                log_entry[key] = value

        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(
            log_entry,
            default=str,
            separators=(",", ":"),
        )


LOGGER = logging.getLogger("homepulse.ingestion")
LOGGER.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())
LOGGER.propagate = False

if LOGGER.handlers:
    for handler in LOGGER.handlers:
        handler.setFormatter(JsonFormatter())
else:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    LOGGER.addHandler(handler)

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(TABLE_NAME)

cloudwatch = boto3.client("cloudwatch")


def convert_floats(value: Any) -> Any:
    """Recursively convert floats to Decimal for DynamoDB compatibility."""

    if isinstance(value, float):
        return Decimal(str(value))

    if isinstance(value, dict):
        return {key: convert_floats(item) for key, item in value.items()}

    if isinstance(value, list):
        return [convert_floats(item) for item in value]

    return value


def require_mapping(
    parent: dict[str, Any],
    key: str,
) -> dict[str, Any]:
    """Return a required nested mapping or raise a validation error."""

    value = parent.get(key)

    if not isinstance(value, dict):
        raise ValueError(f"Missing or invalid '{key}' object")

    return value


def require_value(
    parent: dict[str, Any],
    key: str,
) -> Any:
    """Return a required value or raise a validation error."""

    if key not in parent or parent[key] is None:
        raise ValueError(f"Missing required field: {key}")

    return parent[key]


def validate_event(event: dict[str, Any]) -> datetime:
    """Validate the telemetry payload and return its parsed timestamp."""

    if not isinstance(event, dict):
        raise ValueError("Telemetry event must be a JSON object")

    if event.get("schema_version") != "1.0":
        raise ValueError("Unsupported schema version")

    device_id = event.get("device_id")

    if device_id not in ALLOWED_DEVICES:
        raise ValueError("Unknown or missing device_id")

    timestamp_value = event.get("timestamp")

    if not isinstance(timestamp_value, str) or not timestamp_value:
        raise ValueError("Missing or invalid timestamp")

    try:
        parsed_timestamp = datetime.fromisoformat(
            timestamp_value.replace("Z", "+00:00")
        )
    except ValueError as exc:
        raise ValueError("Timestamp is not valid ISO 8601") from exc

    if parsed_timestamp.tzinfo is None:
        raise ValueError("Timestamp must include a timezone")

    parsed_timestamp = parsed_timestamp.astimezone(timezone.utc)

    now = datetime.now(timezone.utc)
    difference_seconds = abs((now - parsed_timestamp).total_seconds())

    if difference_seconds > 86400:
        raise ValueError("Timestamp is more than 24 hours from the current time")

    network = require_mapping(event, "network")
    system = require_mapping(event, "system")

    internet = require_mapping(network, "internet")
    livebox = require_mapping(network, "livebox")
    miwifi = require_mapping(network, "miwifi")
    dns = require_mapping(network, "dns")

    require_value(internet, "reachable")
    require_value(internet, "packet_loss_percent")

    require_value(livebox, "reachable")
    require_value(miwifi, "reachable")

    require_value(dns, "success")

    require_value(system, "cpu_percent")
    require_value(system, "memory_percent")
    require_value(system, "disk_percent")

    return parsed_timestamp


def build_metric(
    name: str,
    value: float | int | bool,
    unit: str,
    device_id: str,
    timestamp: datetime,
) -> dict[str, Any]:
    """Build one CloudWatch MetricDatum object."""

    numeric_value = 1.0 if value is True else 0.0 if value is False else float(value)

    return {
        "MetricName": name,
        "Dimensions": [
            {
                "Name": "DeviceId",
                "Value": device_id,
            }
        ],
        "Timestamp": timestamp,
        "Value": numeric_value,
        "Unit": unit,
        "StorageResolution": 60,
    }


def append_metric(
    metrics: list[dict[str, Any]],
    *,
    name: str,
    value: Any,
    unit: str,
    device_id: str,
    timestamp: datetime,
) -> None:
    """Append a metric only when its value is available and numeric."""

    if value is None:
        LOGGER.warning(
            "Skipping metric %s because its value is null",
            name,
        )
        return

    if not isinstance(value, (bool, int, float)):
        raise ValueError(f"Metric '{name}' must be numeric or boolean")

    metrics.append(
        build_metric(
            name=name,
            value=value,
            unit=unit,
            device_id=device_id,
            timestamp=timestamp,
        )
    )


def publish_cloudwatch_metrics(
    event: dict[str, Any],
    timestamp: datetime,
) -> int:
    """Publish selected telemetry measurements to CloudWatch."""

    device_id = event["device_id"]

    network = require_mapping(event, "network")
    system = require_mapping(event, "system")

    internet = require_mapping(network, "internet")
    livebox = require_mapping(network, "livebox")
    miwifi = require_mapping(network, "miwifi")
    dns = require_mapping(network, "dns")

    metric_data: list[dict[str, Any]] = []

    metric_definitions = [
        (
            "InternetReachable",
            internet.get("reachable"),
            "Count",
        ),
        (
            "InternetLatency",
            internet.get("latency_ms"),
            "Milliseconds",
        ),
        (
            "InternetPacketLoss",
            internet.get("packet_loss_percent"),
            "Percent",
        ),
        (
            "LiveboxReachable",
            livebox.get("reachable"),
            "Count",
        ),
        (
            "MiWifiReachable",
            miwifi.get("reachable"),
            "Count",
        ),
        (
            "DnsSuccess",
            dns.get("success"),
            "Count",
        ),
        (
            "DnsDuration",
            dns.get("duration_ms"),
            "Milliseconds",
        ),
        (
            "CpuPercent",
            system.get("cpu_percent"),
            "Percent",
        ),
        (
            "MemoryPercent",
            system.get("memory_percent"),
            "Percent",
        ),
        (
            "DiskPercent",
            system.get("disk_percent"),
            "Percent",
        ),
    ]

    for name, value, unit in metric_definitions:
        append_metric(
            metric_data,
            name=name,
            value=value,
            unit=unit,
            device_id=device_id,
            timestamp=timestamp,
        )

    if not metric_data:
        raise ValueError("No valid CloudWatch metrics were produced")

    cloudwatch.put_metric_data(
        Namespace=METRIC_NAMESPACE,
        MetricData=metric_data,
    )

    cloudwatch.put_metric_data(
        Namespace=METRIC_NAMESPACE,
        MetricData=metric_data,
    )

    return len(metric_data)


def lambda_handler(
    event: dict[str, Any],
    context: Any,
) -> dict[str, Any]:
    """Process one HomePulse telemetry event."""

    request_id = getattr(context, "aws_request_id", "local-test")

    LOGGER.info(
        "telemetry_processing_started",
        extra={
            "request_id": request_id,
            "device_id": (event.get("device_id") if isinstance(event, dict) else None),
            "telemetry_timestamp": (
                event.get("timestamp") if isinstance(event, dict) else None
            ),
        },
    )

    try:
        parsed_timestamp = validate_event(event)
        device_id = event["device_id"]

        table.put_item(
            Item=convert_floats(event),
        )

        LOGGER.info(
            "telemetry_stored",
            extra={
                "request_id": request_id,
                "device_id": device_id,
                "telemetry_timestamp": event["timestamp"],
                "table_name": TABLE_NAME,
            },
        )

        metrics_published = publish_cloudwatch_metrics(
            event,
            parsed_timestamp,
        )

        LOGGER.info(
            "metrics_published",
            extra={
                "request_id": request_id,
                "device_id": device_id,
                "metric_namespace": METRIC_NAMESPACE,
                "metric_count": metrics_published,
            },
        )

    except ValueError as exc:
        LOGGER.warning(
            "telemetry_validation_failed",
            extra={
                "request_id": request_id,
                "device_id": (
                    event.get("device_id") if isinstance(event, dict) else None
                ),
                "error_type": type(exc).__name__,
                "error_message": str(exc),
            },
        )
        raise

    except Exception as exc:
        LOGGER.exception(
            "telemetry_processing_failed",
            extra={
                "request_id": request_id,
                "device_id": (
                    event.get("device_id") if isinstance(event, dict) else None
                ),
                "error_type": type(exc).__name__,
            },
        )
        raise

    LOGGER.info(
        "telemetry_processing_succeeded",
        extra={
            "request_id": request_id,
            "device_id": device_id,
            "telemetry_timestamp": event["timestamp"],
            "metric_count": metrics_published,
        },
    )

    return {
        "statusCode": 200,
        "request_id": request_id,
        "device_id": device_id,
        "timestamp": event["timestamp"],
        "dynamodb": "Telemetry stored successfully",
        "cloudwatch_metrics_published": metrics_published,
    }
