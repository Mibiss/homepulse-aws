# HomePulse AWS

HomePulse AWS is a home-network observability project that collects connectivity and system-health measurements from a macOS or Linux agent and publishes them securely to AWS IoT Core using MQTT over TLS.

## Current status

* [x] Python monitoring agent
* [x] Internet latency and packet-loss checks
* [x] Livebox reachability checks
* [x] Xiaomi access-point reachability checks
* [x] DNS response-time checks
* [x] Local CPU, memory and disk metrics
* [x] AWS IoT Core MQTT connection
* [x] X.509 certificate authentication
* [x] Least-privilege IoT publishing policy
* [ ] Lambda ingestion
* [ ] Amazon Timestream storage
* [ ] Dashboard
* [ ] CloudWatch alarms
* [ ] SNS notifications
* [ ] Infrastructure as Code

## Architecture

```text
Home network
    |
Python monitoring agent
    |
MQTT over TLS
    |
AWS IoT Core
```

Planned cloud architecture:

```text
Home monitoring agent
        |
        | MQTT over TLS
        v
AWS IoT Core
        |
        | IoT Rule
        v
AWS Lambda
        |
        +--> Amazon Timestream
        |         |
        |         v
        |      Dashboard
        |
        +--> CloudWatch metrics and alarms
                  |
                  v
              Amazon SNS
                  |
                  v
            Email notification
```

## Collected metrics

The monitoring agent currently collects:

* Internet reachability
* Internet latency
* Internet packet loss
* Livebox reachability and latency
* Xiaomi access-point reachability and latency
* DNS resolution status
* DNS response time
* Local CPU usage
* Local memory usage
* Local disk usage
* Agent boot time

## Telemetry topic

The agent publishes telemetry to:

```text
homepulse/homepulse-agent-01/telemetry
```

Example payload:

```json
{
  "schema_version": "1.0",
  "device_id": "homepulse-agent-01",
  "timestamp": "2026-07-24T19:49:56.623432+00:00",
  "network": {
    "internet": {
      "reachable": true,
      "latency_ms": 12.528,
      "packet_loss_percent": 0.0
    },
    "livebox": {
      "reachable": true,
      "latency_ms": 3.31,
      "packet_loss_percent": 0.0
    },
    "miwifi": {
      "reachable": true,
      "latency_ms": 2.901,
      "packet_loss_percent": 0.0
    },
    "dns": {
      "success": true,
      "duration_ms": 19.21,
      "resolved_ip": "104.20.23.154"
    }
  },
  "system": {
    "cpu_percent": 28.9,
    "memory_percent": 73.9,
    "disk_percent": 3.6
  }
}
```

## Requirements

* macOS or Linux
* Python 3
* An AWS account
* An AWS IoT Thing
* An active AWS IoT certificate
* A least-privilege AWS IoT policy
* Network access to the local router and access point

Python dependencies are listed in:

```text
requirements.txt
```

## Local setup

Clone the repository:

```bash
git clone https://github.com/mibiss/homepulse-aws.git
cd homepulse-aws
```

Create a Python virtual environment:

```bash
python3 -m venv .venv
```

Activate it on macOS or Linux:

```bash
source .venv/bin/activate
```

Install the dependencies:

```bash
python3 -m pip install -r requirements.txt
```

Create your local configuration file:

```bash
cp config.env.example config.env
```

Update `config.env` with your own AWS IoT endpoint, local network addresses and certificate paths.

Example:

```bash
AWS_IOT_ENDPOINT=YOUR_ENDPOINT-ats.iot.eu-central-1.amazonaws.com
AWS_IOT_CLIENT_ID=homepulse-agent-01
AWS_IOT_TOPIC=homepulse/homepulse-agent-01/telemetry

LIVEBOX_IP=
MIWIFI_IP=

CERT_PATH=/path/to/certificates/device-certificate.pem.crt
PRIVATE_KEY_PATH=/path/to/certificates/private.pem.key
CA_PATH=/path/to/certificates/AmazonRootCA1.pem

COLLECTION_INTERVAL_SECONDS=60
RUN_SPEEDTEST=false
```

Run the monitoring agent:

```bash
python3 agent.py
```

A successful connection should display:

```text
Connecting to AWS IoT Core...
Connected.
```

The agent will then print and publish a telemetry message approximately once per minute.

## AWS IoT policy

The device policy should allow the agent to connect only with its expected client ID and publish only to its own topics.

Example structure:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "iot:Connect",
      "Resource": "arn:aws:iot:eu-central-1:ACCOUNT_ID:client/homepulse-agent-01"
    },
    {
      "Effect": "Allow",
      "Action": "iot:Publish",
      "Resource": [
        "arn:aws:iot:eu-central-1:ACCOUNT_ID:topic/homepulse/homepulse-agent-01/telemetry",
        "arn:aws:iot:eu-central-1:ACCOUNT_ID:topic/homepulse/homepulse-agent-01/status"
      ]
    }
  ]
}
```

Replace `ACCOUNT_ID` with your own AWS account ID when creating the policy. Do not publish your real account details unnecessarily in screenshots or documentation.

## Testing

Open the AWS IoT Core MQTT test client and subscribe to:

```text
homepulse/homepulse-agent-01/telemetry
```

Use a browser client ID different from the Python agent, such as the automatically generated `iotconsole-...` client ID.

Run the agent locally and confirm that new telemetry messages appear in the MQTT test client.

## Security

The following files must never be committed to GitHub:

* Private keys
* Device certificates
* Root CA files
* `config.env`
* `.env` files
* AWS access keys
* AWS secret access keys
* Local credential files
* Terraform state files containing sensitive values

The repository should include only safe example files such as:

```text
config.env.example
```

Recommended `.gitignore` entries:

```gitignore
.venv/
__pycache__/
*.py[cod]

config.env
.env
.env.*
!.env.example

certificates/
*.pem
*.key
*.crt
*.p12
*.pfx

.DS_Store
*.log

.terraform/
*.tfstate
*.tfstate.*
```

The monitoring agent creates only an outbound encrypted connection to AWS IoT Core. No inbound router ports are required.

## Project roadmap

### Version 1

* Python monitoring agent
* AWS IoT Core connection
* Secure MQTT publishing
* Lambda ingestion
* Amazon Timestream storage
* Basic dashboard
* SNS outage notifications

## Repository structure

Structure:

```text
homepulse-aws/
├── README.md
├── .gitignore
├── requirements.txt
├── config.env.example
├── agent.py
└── certificates/
```

The `certificates/` directory is local-only and must remain ignored by Git.

## License

This project is intended for educational and portfolio use. Add a licence file before distributing or accepting contributions.
