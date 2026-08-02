import subprocess
from types import SimpleNamespace
from unittest.mock import patch, MagicMock

import agent


@patch("agent.psutil.disk_usage")
@patch("agent.psutil.virtual_memory")
@patch("agent.psutil.cpu_percent")
@patch("agent.psutil.boot_time")
@patch("agent.dns_lookup")
@patch("agent.ping_host")
def test_collect_metrics_contains_required_structure(
    mock_ping_host,
    mock_dns_lookup,
    mock_boot_time,
    mock_cpu_percent,
    mock_virtual_memory,
    mock_disk_usage,
):
    mock_ping_host.side_effect = [
        {
            "reachable": True,
            "latency_ms": 20.5,
            "packet_loss_percent": 0.0,
        },
        {
            "reachable": True,
            "latency_ms": 1.2,
            "packet_loss_percent": 0.0,
        },
        {
            "reachable": True,
            "latency_ms": 2.4,
            "packet_loss_percent": 0.0,
        },
    ]

    mock_dns_lookup.return_value = {
        "success": True,
        "duration_ms": 12.3,
        "resolved_ip": "93.184.216.34",
    }

    mock_boot_time.return_value = 1_700_000_000
    mock_cpu_percent.return_value = 10.0
    mock_virtual_memory.return_value = SimpleNamespace(percent=40.0)
    mock_disk_usage.return_value = SimpleNamespace(percent=60.0)

    payload = agent.collect_metrics()

    assert payload["schema_version"] == "1.0"
    assert payload["device_id"] == agent.CLIENT_ID
    assert "timestamp" in payload

    assert payload["network"]["internet"]["reachable"] is True
    assert payload["network"]["livebox"]["reachable"] is True
    assert payload["network"]["miwifi"]["reachable"] is True
    assert payload["network"]["dns"]["success"] is True

    assert payload["system"]["cpu_percent"] == 10.0
    assert payload["system"]["memory_percent"] == 40.0
    assert payload["system"]["disk_percent"] == 60.0
    assert "boot_time" in payload["system"]

    assert mock_ping_host.call_count == 3
    mock_dns_lookup.assert_called_once_with()


@patch("agent.subprocess.run")
def test_ping_host_reports_success(mock_run):
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout=(
            "4 packets transmitted, 4 packets received, 0.0% packet loss\n"
            "round-trip min/avg/max/stddev = 10.000/20.500/30.000/5.000 ms\n"
        ),
        stderr="",
    )

    result = agent.ping_host("1.1.1.1")

    assert result == {
        "reachable": True,
        "latency_ms": 20.5,
        "packet_loss_percent": 0.0,
    }


@patch("agent.subprocess.run")
def test_ping_host_reports_failure(mock_run):
    mock_run.return_value = MagicMock(
        returncode=1,
        stdout="4 packets transmitted, 0 packets received, 100.0% packet loss",
        stderr="",
    )

    result = agent.ping_host("192.0.2.1")

    assert result["reachable"] is False
    assert result["latency_ms"] is None
    assert result["packet_loss_percent"] == 100.0


@patch("agent.subprocess.run")
def test_ping_host_handles_timeout(mock_run):
    mock_run.side_effect = subprocess.TimeoutExpired(
        cmd=["ping"],
        timeout=15,
    )

    result = agent.ping_host("192.0.2.1")

    assert result == {
        "reachable": False,
        "latency_ms": None,
        "packet_loss_percent": 100.0,
    }
