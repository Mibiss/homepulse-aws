import os
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]

if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

os.environ.setdefault("AWS_IOT_ENDPOINT", "example.iot.eu-central-1.amazonaws.com")
os.environ.setdefault("AWS_IOT_CLIENT_ID", "homepulse-agent-01")
os.environ.setdefault(
    "AWS_IOT_TOPIC",
    "homepulse/homepulse-agent-01/telemetry",
)
os.environ.setdefault("CERT_PATH", "/tmp/test-certificate.pem")
os.environ.setdefault("PRIVATE_KEY_PATH", "/tmp/test-private-key.pem")
os.environ.setdefault("CA_PATH", "/tmp/test-ca.pem")
os.environ.setdefault("LIVEBOX_IP", "192.168.1.1")
os.environ.setdefault("MIWIFI_IP", "192.168.1.68")
os.environ.setdefault("COLLECTION_INTERVAL_SECONDS", "60")
