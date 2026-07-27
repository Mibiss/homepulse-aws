# HomePulse AWS

HomePulse AWS is an edge-to-cloud home-network observability project. A Python agent running on macOS or Linux collects connectivity and system-health measurements and publishes them securely to AWS IoT Core using MQTT over TLS.

AWS IoT Core routes each telemetry payload to AWS Lambda. The Lambda function validates the message, stores the complete payload in Amazon DynamoDB, and publishes selected measurements as Amazon CloudWatch custom metrics. CloudWatch dashboards visualise system health, while CloudWatch alarms and Amazon SNS deliver outage and recovery notifications by email.

## Current status

- [x] Python monitoring agent
- [x] Internet latency and packet-loss checks
- [x] Livebox reachability checks
- [x] Xiaomi access-point reachability checks
- [x] DNS response-time checks
- [x] Local CPU, memory and disk metrics
- [x] AWS IoT Core MQTT connection
- [x] X.509 certificate authentication
- [x] Least-privilege IoT publishing policy
- [x] AWS IoT telemetry routing rule
- [x] AWS Lambda ingestion
- [x] Amazon DynamoDB telemetry storage
- [x] Manual Lambda ingestion test
- [x] End-to-end live telemetry test
- [x] DynamoDB telemetry queries
- [x] CloudWatch custom metrics
- [x] CloudWatch dashboard
- [x] Five-minute dashboard aggregation
- [x] CloudWatch alarms
- [x] Amazon SNS topic
- [x] Email alert subscription
- [x] Alarm and recovery notification tests
- [ ] Infrastructure as Code
- [ ] Automated tests

## Architecture

### HomePulse AWS — Edge-to-cloud observability architecture


![HomePulse AWS architecture](architecture/architecture.png)


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
        +--> Amazon DynamoDB
        |
        +--> CloudWatch custom metrics
                  |
                  +--> CloudWatch dashboard
                  |
                  +--> CloudWatch alarms
                              |
                              v
                         Amazon SNS
                              |
                              v
                     Email notification
```

The monitoring agent runs inside the home network and communicates with AWS through an outbound encrypted MQTT connection. No inbound router ports or port-forwarding rules are required.


## Project components

### Monitoring agent

The monitoring agent is a Python application running on macOS or Linux.

It collects:

- Internet reachability
- Internet latency
- Internet packet loss
- Livebox reachability
- Livebox latency
- Livebox packet loss
- Xiaomi access-point reachability
- Xiaomi access-point latency
- Xiaomi access-point packet loss
- DNS resolution status
- DNS response time
- Resolved IP address
- Local CPU usage
- Local memory usage
- Local disk usage
- Agent boot time

### AWS IoT Core

AWS IoT Core receives telemetry from the monitoring agent over MQTT with TLS.

The device authenticates using:

- an AWS IoT device certificate
- a private key stored locally
- Amazon Root CA 1
- a restricted AWS IoT policy

### AWS IoT Rule

The IoT Rule subscribes to the telemetry topic and invokes the Lambda ingestion function.

Rule name:

```text
homepulse_telemetry_ingestion
```

Rule SQL:

```sql
SELECT *
FROM 'homepulse/homepulse-agent-01/telemetry'
```

### AWS Lambda

The `homepulse-ingestion` Lambda function:

- validates incoming telemetry
- stores the complete payload in DynamoDB
- publishes selected CloudWatch custom metrics
- logs processing results and failures

Source code and detailed deployment documentation are available in [`cloud/lambda/`](cloud/lambda/).

### Amazon DynamoDB

Raw telemetry is stored in:

```text
homepulse-network-metrics
```

Table key structure:

```text
Partition key: device_id
Sort key:      timestamp
```

Each DynamoDB item represents one complete observation from the monitoring agent.

### Amazon CloudWatch

The Lambda function publishes selected telemetry values to the custom namespace:

```text
HomePulse
```

CloudWatch is used for dashboards, availability alarms, missing-telemetry detection and recovery notifications.

### Amazon SNS

CloudWatch sends alarm state-change notifications to the `homepulse-alerts` SNS topic, which delivers them to a confirmed email subscription.

## Telemetry topic

```text
homepulse/homepulse-agent-01/telemetry
```

Use a different MQTT client ID for the browser test client and the monitoring agent to prevent them from disconnecting each other.

## Example telemetry payload

```json
{
  "schema_version": "1.0",
  "device_id": "homepulse-agent-01",
  "timestamp": "2026-07-25T11:13:05.616259+00:00",
  "network": {
    "internet": {
      "reachable": true,
      "latency_ms": 11.964,
      "packet_loss_percent": 0.0
    },
    "livebox": {
      "reachable": true,
      "latency_ms": 3.133,
      "packet_loss_percent": 0.0
    },
    "miwifi": {
      "reachable": true,
      "latency_ms": 2.565,
      "packet_loss_percent": 0.0
    },
    "dns": {
      "success": true,
      "duration_ms": 24.29,
      "resolved_ip": "104.20.23.154"
    }
  },
  "system": {
    "cpu_percent": 9.2,
    "memory_percent": 73.9,
    "disk_percent": 3.6,
    "boot_time": "2026-06-30T12:11:56+00:00"
  }
}
```

## DynamoDB queries

Example PartiQL query:

```sql
SELECT
    "timestamp",
    "network"."internet"."latency_ms",
    "network"."internet"."packet_loss_percent",
    "network"."internet"."reachable"
FROM "homepulse-network-metrics"
WHERE "device_id" = 'homepulse-agent-01'
ORDER BY "timestamp" DESC
```

## CloudWatch custom metrics

```text
InternetReachable
InternetLatency
InternetPacketLoss
LiveboxReachable
MiWifiReachable
DnsSuccess
DnsDuration
CpuPercent
MemoryPercent
DiskPercent
```

Metrics use:

```text
Namespace: HomePulse
Dimension: DeviceId=homepulse-agent-01
```

Boolean values are represented as `1` for available/successful and `0` for unavailable/failed.

## CloudWatch dashboard

Dashboard name:

```text
HomePulse-Network-Dashboard
```

Latency and resource metrics use five-minute periods with the `Average` statistic. Status metrics use five-minute periods with the `Minimum` statistic.

The dashboard definition is stored in [`dashboard/homepulse-dashboard.json`](dashboard/homepulse-dashboard.json).

## CloudWatch alarms

Configured and tested alarms:

- `HomePulse-Agent-Telemetry-Missing`
- `HomePulse-Internet-Unavailable`
- `HomePulse-MiWifi-Unavailable`

A high-latency alarm is documented as a future enhancement.

CloudWatch sends `ALARM` and `OK` state-change notifications through Amazon SNS.

## Requirements

- macOS or Linux
- Python 3
- AWS account
- AWS IoT Core Thing and active certificate
- restricted AWS IoT policy
- AWS IoT Rule
- AWS Lambda function
- Amazon DynamoDB table
- Amazon CloudWatch dashboard and alarms
- Amazon SNS topic with confirmed email subscription
- network access to the local router and access point

Python dependencies are listed in `requirements.txt`:

```text
awsiotsdk
psutil
python-dotenv
```

## Repository structure

```text
homepulse-aws/
├── README.md
├── agent.py
├── requirements.txt
├── config.env.example
├── .gitignore
├── cloud/
│   └── lambda/
│       ├── README.md
│       └── lambda_function.py
├── architecture/
│   ├── architecture.drawio
│   └── architecture.png
└── dashboard/
    └── homepulse-dashboard.json
```

## Local setup

```bash
git clone https://github.com/Mibiss/homepulse-aws.git
cd homepulse-aws
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
cp config.env.example config.env
python3 agent.py
```

## Lambda configuration

Required environment variable:

```text
DYNAMODB_TABLE=homepulse-network-metrics
```

Optional environment variables:

```text
METRIC_NAMESPACE=HomePulse
ALLOWED_DEVICES=homepulse-agent-01
```

The Lambda role permits `dynamodb:PutItem`, `cloudwatch:PutMetricData` for the `HomePulse` namespace, and standard CloudWatch Logs operations.

Detailed Lambda configuration, IAM policies, deployment, validation, input/output and testing instructions are documented in [`cloud/lambda/README.md`](cloud/lambda/README.md).

## Testing completed

The end-to-end pipeline, DynamoDB storage, custom metrics, dashboard, SNS delivery, outage alarms and recovery notifications have been tested successfully.

## Security

Never commit private keys, AWS credentials, real local configuration, Terraform state or virtual environments.

This project also keeps device certificates and CA files outside the repository to simplify certificate management.

Recommended `.gitignore` additions include:

```gitignore
.venv/
config.env
.env
.env.*
certificates/
*.pem
*.key
*.crt
*.tfstate
*.tfstate.*
cloud/lambda/*.zip
```

## Roadmap

### Version 1

- [x] Monitoring agent
- [x] AWS IoT ingestion
- [x] Lambda and DynamoDB
- [x] CloudWatch metrics and dashboard
- [x] CloudWatch alarms and SNS email notifications
- [x] Final architecture diagram
- [x] Project documentation polish

### Version 2

- Infrastructure as Code
- Automated tests
- Structured logging improvements
- Lambda failure handling
- DynamoDB retention strategy
- Dedicated heartbeat metric
- CI pipeline
- Automated deployment

## Licence

This project is intended for educational and portfolio use.

This project is licensed under the MIT License. See [`LICENSE`](LICENSE) for details.