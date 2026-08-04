#!/usr/bin/env python3

import json
import logging
import os
import platform
import re
import socket
import subprocess
import time
from datetime import datetime, timezone
from typing import Any

import psutil
from awscrt import mqtt
from awsiot import mqtt_connection_builder
from dotenv import load_dotenv

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(SCRIPT_DIR, "config.env")

load_dotenv(CONFIG_PATH)


class JsonFormatter(logging.Formatter):
    """Format application logs as single-line JSON objects."""

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


def configure_logging() -> logging.Logger:
    """Configure the HomePulse agent logger."""

    logger = logging.getLogger("homepulse.agent")
    logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())
    logger.propagate = False

    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)

    return logger


LOGGER = configure_logging()


def required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


AWS_IOT_ENDPOINT = required_env("AWS_IOT_ENDPOINT")
CLIENT_ID = required_env("AWS_IOT_CLIENT_ID")
TOPIC = required_env("AWS_IOT_TOPIC")
CERT_PATH = required_env("CERT_PATH")
PRIVATE_KEY_PATH = required_env("PRIVATE_KEY_PATH")
CA_PATH = required_env("CA_PATH")

LIVEBOX_IP = required_env("LIVEBOX_IP")
MIWIFI_IP = required_env("MIWIFI_IP")

INTERVAL = int(os.getenv("COLLECTION_INTERVAL_SECONDS", "60"))


def ping_host(host: str, count: int = 4) -> dict[str, Any]:
    """Return reachability, average latency and packet loss."""

    parameter = "-n" if platform.system().lower() == "windows" else "-c"

    try:
        result = subprocess.run(
            ["ping", parameter, str(count), host],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except subprocess.TimeoutExpired:
        LOGGER.warning(
            "ping_timeout",
            extra={
                "target": host,
                "count": count,
                "timeout_seconds": 15,
            },
        )

        return {
            "reachable": False,
            "latency_ms": None,
            "packet_loss_percent": 100.0,
        }

    output = result.stdout + result.stderr

    unix_match = re.search(
        r"=\s*[0-9.]+/([0-9.]+)/[0-9.]+/[0-9.]+\s*ms",
        output,
    )

    windows_match = re.search(
        r"Average\s*=\s*([0-9.]+)\s*ms",
        output,
        re.IGNORECASE,
    )

    if unix_match:
        latency = float(unix_match.group(1))
    elif windows_match:
        latency = float(windows_match.group(1))
    else:
        latency = None

    loss_match = re.search(
        r"([0-9.]+)%\s*(?:packet\s*)?loss",
        output,
        re.IGNORECASE,
    )

    packet_loss = (
        float(loss_match.group(1))
        if loss_match
        else (0.0 if result.returncode == 0 else 100.0)
    )

    ping_result = {
        "reachable": result.returncode == 0,
        "latency_ms": latency,
        "packet_loss_percent": packet_loss,
    }

    if not ping_result["reachable"]:
        LOGGER.warning(
            "ping_failed",
            extra={
                "target": host,
                "return_code": result.returncode,
                "packet_loss_percent": packet_loss,
            },
        )

    return ping_result


def dns_lookup(domain: str = "example.com") -> dict[str, Any]:
    start = time.perf_counter()

    try:
        resolved_ip = socket.gethostbyname(domain)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)

        return {
            "success": True,
            "duration_ms": duration_ms,
            "resolved_ip": resolved_ip,
        }

    except socket.gaierror as exc:
        LOGGER.warning(
            "dns_lookup_failed",
            extra={
                "domain": domain,
                "error_type": type(exc).__name__,
            },
        )

        return {
            "success": False,
            "duration_ms": None,
            "resolved_ip": None,
        }


def collect_metrics() -> dict[str, Any]:
    internet = ping_host("1.1.1.1")
    livebox = ping_host(LIVEBOX_IP)
    miwifi = ping_host(MIWIFI_IP)
    dns = dns_lookup()

    boot_time = datetime.fromtimestamp(
        psutil.boot_time(),
        tz=timezone.utc,
    ).isoformat()

    return {
        "schema_version": "1.0",
        "device_id": CLIENT_ID,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "network": {
            "internet": internet,
            "livebox": livebox,
            "miwifi": miwifi,
            "dns": dns,
        },
        "system": {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage("/").percent,
            "boot_time": boot_time,
        },
    }


def create_connection():
    return mqtt_connection_builder.mtls_from_path(
        endpoint=AWS_IOT_ENDPOINT,
        cert_filepath=CERT_PATH,
        pri_key_filepath=PRIVATE_KEY_PATH,
        ca_filepath=CA_PATH,
        client_id=CLIENT_ID,
        clean_session=False,
        keep_alive_secs=30,
    )


def main() -> None:
    LOGGER.info(
        "agent_starting",
        extra={
            "device_id": CLIENT_ID,
            "collection_interval_seconds": INTERVAL,
            "topic": TOPIC,
        },
    )

    mqtt_connection = create_connection()

    try:
        mqtt_connection.connect().result()

        LOGGER.info(
            "mqtt_connected",
            extra={
                "device_id": CLIENT_ID,
            },
        )

        while True:
            collection_started = time.perf_counter()
            payload = collect_metrics()

            collection_duration_ms = round(
                (time.perf_counter() - collection_started) * 1000,
                2,
            )

            LOGGER.info(
                "telemetry_collected",
                extra={
                    "device_id": payload["device_id"],
                    "telemetry_timestamp": payload["timestamp"],
                    "collection_duration_ms": collection_duration_ms,
                    "internet_reachable": payload["network"]["internet"]["reachable"],
                    "livebox_reachable": payload["network"]["livebox"]["reachable"],
                    "miwifi_reachable": payload["network"]["miwifi"]["reachable"],
                    "dns_success": payload["network"]["dns"]["success"],
                },
            )

            publish_future, packet_id = mqtt_connection.publish(
                topic=TOPIC,
                payload=json.dumps(payload),
                qos=mqtt.QoS.AT_LEAST_ONCE,
            )

            publish_future.result()

            LOGGER.info(
                "telemetry_published",
                extra={
                    "device_id": payload["device_id"],
                    "telemetry_timestamp": payload["timestamp"],
                    "topic": TOPIC,
                    "packet_id": packet_id,
                },
            )

            time.sleep(INTERVAL)

    except KeyboardInterrupt:
        LOGGER.info(
            "agent_stopping",
            extra={
                "device_id": CLIENT_ID,
                "reason": "keyboard_interrupt",
            },
        )

    except Exception:
        LOGGER.exception(
            "agent_unhandled_error",
            extra={
                "device_id": CLIENT_ID,
            },
        )
        raise

    finally:
        try:
            mqtt_connection.disconnect().result()

            LOGGER.info(
                "mqtt_disconnected",
                extra={
                    "device_id": CLIENT_ID,
                },
            )
        except Exception:
            LOGGER.exception(
                "mqtt_disconnect_failed",
                extra={
                    "device_id": CLIENT_ID,
                },
            )


if __name__ == "__main__":
    main()
