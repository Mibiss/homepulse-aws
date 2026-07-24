#!/usr/bin/env python3

import json
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
        return {
            "reachable": False,
            "latency_ms": None,
            "packet_loss_percent": 100.0,
        }

    output = result.stdout + result.stderr

    latency_match = re.search(
        r"(?:avg|Average =)[^0-9]*([0-9.]+)",
        output,
        re.IGNORECASE,
    )

    if not latency_match:
        linux_match = re.search(
            r"=\s*[0-9.]+/([0-9.]+)/[0-9.]+/",
            output,
        )
        latency = float(linux_match.group(1)) if linux_match else None
    else:
        latency = float(latency_match.group(1))

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

    return {
        "reachable": result.returncode == 0,
        "latency_ms": latency,
        "packet_loss_percent": packet_loss,
    }


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
    except socket.gaierror:
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
    mqtt_connection = create_connection()

    print("Connecting to AWS IoT Core...")
    mqtt_connection.connect().result()
    print("Connected.")

    try:
        while True:
            payload = collect_metrics()

            mqtt_connection.publish(
                topic=TOPIC,
                payload=json.dumps(payload),
                qos=mqtt.QoS.AT_LEAST_ONCE,
            )

            print(json.dumps(payload, indent=2))
            time.sleep(INTERVAL)

    except KeyboardInterrupt:
        print("Stopping agent...")
    finally:
        mqtt_connection.disconnect().result()


if __name__ == "__main__":
    main()
