# HomePulse AWS

HomePulse AWS is a home-network observability project that collects connectivity and system-health measurements from a macOS or Linux agent and publishes them securely to AWS IoT Core using MQTT over TLS.

The current version stores each telemetry payload in Amazon DynamoDB through an AWS IoT Rule and AWS Lambda.

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
* [x] AWS IoT telemetry routing rule
* [x] AWS Lambda ingestion
* [x] Amazon DynamoDB telemetry storage
* [x] Manual Lambda ingestion test
* [x] End-to-end live telemetry test
* [ ] CloudWatch custom metrics
* [ ] CloudWatch dashboard
* [ ] CloudWatch alarms
* [ ] SNS notifications
* [ ] Infrastructure as Code
* [ ] Automated tests

## Architecture

```text
Home network
    |
Python monitoring agent
    |
MQTT over TLS
    |
AWS IoT Core
    |
AWS IoT Rule
    |
AWS Lambda
    |
Amazon DynamoDB
```

Planned monitoring and alerting architecture:

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
        +--> CloudWatch metrics
                  |
                  v
          CloudWatch dashboard
                  |
                  v
          CloudWatch alarms
                  |
                  v
              Amazon SNS
                  |
                  v
           Email notification
```

## Project components

### Monitoring agent

The monitoring agent is a Python application running on macOS or Linux.

It collects:

* Internet reachability
* Internet latency
* Internet packet loss
* Livebox reachability
* Livebox latency
* Livebox packet loss
* Xiaomi access-point reachability
* Xiaomi access-point latency
* Xiaomi access-point packet loss
* DNS resolution status
* DNS response time
* Resolved IP address
* Local CPU usage
* Local memory usage
* Local disk usage
* Agent boot time

### AWS IoT Core

AWS IoT Core receives telemetry from the monitoring agent over MQTT with TLS.

The device authenticates using:

* An AWS IoT device certificate
* A private key stored locally
* Amazon Root CA 1
* A restricted AWS IoT policy

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

The Lambda function:

* Receives telemetry from AWS IoT Core
* Validates the schema version
* Validates the device ID
* Validates the timestamp
* Converts floating-point values to DynamoDB-compatible decimal values
* Writes the complete telemetry document to DynamoDB

Function name:

```text
homepulse-ingestion
```

### Amazon DynamoDB

Telemetry is stored in:

```text
homepulse-network-metrics
```

Table key structure:

```text
Partition key: device_id
Sort key:      timestamp
```

Each DynamoDB item represents one complete observation from the monitoring agent.

## Telemetry topic

The agent publishes to:

```text
homepulse/homepulse-agent-01/telemetry
```

The MQTT browser test client should use a different client ID from the monitoring agent.

Example browser client ID:

```text
iotconsole-generated-client-id
```

Monitoring agent client ID:

```text
homepulse-agent-01
```

Using different client IDs prevents the two MQTT connections from disconnecting each other.

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

## DynamoDB representation

DynamoDB displays values using typed attributes.

Common types used by this project are:

```text
S     String
N     Number
BOOL  Boolean
M     Map or nested object
```

For example:

```text
"latency_ms": { "N": "11.964" }
```

represents a number.

```text
"reachable": { "BOOL": true }
```

represents a Boolean value.

```text
"network": { "M": { ... } }
```

represents a nested map.

DynamoDB does not guarantee the display order of fields inside maps. The order of keys such as `internet`, `dns`, `livebox`, and `miwifi` may therefore differ between items without changing the meaning of the data.

## Requirements

* macOS or Linux
* Python 3
* AWS account
* AWS IoT Core Thing
* Active AWS IoT certificate
* Restricted AWS IoT policy
* AWS Lambda function
* Amazon DynamoDB table
* Network access to the local router and access point

Python dependencies are listed in:

```text
requirements.txt
```

Current dependencies:

```text
awsiotsdk
psutil
python-dotenv
```

## Repository structure

```text
HomePulse_AWS/
├── README.md
├── agent.py
├── requirements.txt
├── config.env.example
├── .gitignore
├── certificates/
└── .venv/
```

The `certificates/`, `.venv/`, and local configuration files must not be committed to GitHub.

## Local setup

Clone the repository:

```bash
git clone https://github.com/Mibiss/homepulse-aws.git
cd homepulse-aws
```

Create a Python virtual environment:

```bash
python3 -m venv .venv
```

Activate it:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
python3 -m pip install -r requirements.txt
```

Create the local configuration file:

```bash
cp config.env.example config.env
```

Update `config.env` with your real values:

```bash
AWS_IOT_ENDPOINT=YOUR_ENDPOINT-ats.iot.eu-central-1.amazonaws.com
AWS_IOT_CLIENT_ID=homepulse-agent-01
AWS_IOT_TOPIC=homepulse/homepulse-agent-01/telemetry

LIVEBOX_IP=
MIWIFI_IP=

CERT_PATH=/absolute/path/to/certificates/device-certificate.pem.crt
PRIVATE_KEY_PATH=/absolute/path/to/certificates/private.pem.key
CA_PATH=/absolute/path/to/certificates/AmazonRootCA1.pem

COLLECTION_INTERVAL_SECONDS=60
RUN_SPEEDTEST=false
```

Run the agent:

```bash
python3 agent.py
```

Expected output:

```text
Connecting to AWS IoT Core...
Connected.
```

The agent then prints and publishes a telemetry payload.

## Collection interval

The configured interval is:

```text
60 seconds
```

The actual gap between DynamoDB items may be slightly longer than 60 seconds because the agent first performs:

* Internet ping tests
* Router ping tests
* Access-point ping tests
* DNS resolution
* CPU sampling

It then sleeps for 60 seconds.

The full cycle is therefore approximately:

```text
metric collection time + 60-second sleep
```

## AWS IoT policy

The policy should allow the agent to connect only with its expected client ID and publish only to its own telemetry topics.

Example:

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

Replace `ACCOUNT_ID` when creating the real AWS policy.

## Lambda environment variable

The Lambda function uses:

```text
DYNAMODB_TABLE=homepulse-network-metrics
```

## Lambda IAM permission

The Lambda execution role should only be allowed to write to the HomePulse DynamoDB table.

Example policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "WriteHomePulseTelemetry",
      "Effect": "Allow",
      "Action": "dynamodb:PutItem",
      "Resource": "arn:aws:dynamodb:eu-central-1:ACCOUNT_ID:table/homepulse-network-metrics"
    }
  ]
}
```

## Testing completed

The following tests have been completed successfully:

* Python agent connected to AWS IoT Core
* MQTT test client received telemetry
* Manual Lambda test returned HTTP status 200
* Manual Lambda test item appeared in DynamoDB
* AWS IoT Rule invoked Lambda
* Live MQTT telemetry appeared automatically in DynamoDB
* Multiple timestamped telemetry records were stored
* Nested network and system maps were stored correctly

Confirmed end-to-end data flow:

```text
Mac monitoring agent
→ AWS IoT Core
→ AWS IoT Rule
→ AWS Lambda
→ Amazon DynamoDB
```

## Security

Never commit the following files:

* Private keys
* Device certificates
* Root CA files
* `config.env`
* `.env` files
* AWS access keys
* AWS secret access keys
* AWS credential files
* Terraform state files
* Local virtual environments

Recommended `.gitignore` entries:

```gitignore
# Python
.venv/
venv/
__pycache__/
*.py[cod]
.pytest_cache/

# Local configuration
config.env
.env
.env.*
!.env.example

# Certificates and keys
certificates/
*.pem
*.key
*.crt
*.p12
*.pfx

# macOS
.DS_Store

# Logs
*.log
logs/

# IDE settings
.vscode/
.idea/

# Terraform
.terraform/
*.tfstate
*.tfstate.*
crash.log
```

The agent creates only an outbound TLS connection to AWS IoT Core. No inbound ports or router port-forwarding rules are required.

## Git workflow
Completed commits:

```text
Build Python network telemetry agent
Add secure AWS IoT MQTT publishing
Add DynamoDB telemetry table
Add Lambda telemetry ingestion
Route IoT telemetry through Lambda
Complete end-to-end DynamoDB ingestion
```

## Roadmap

### Version 1

* [x] Python monitoring agent
* [x] AWS IoT Core connection
* [x] Secure MQTT publishing
* [x] AWS IoT Rule
* [x] Lambda ingestion
* [x] DynamoDB storage
* [ ] CloudWatch dashboard
* [ ] Outage alarms
* [ ] SNS email notifications
* [ ] Project documentation polish

## Licence

This project is intended for educational and portfolio use.

Add a `LICENSE` file before distributing the project or accepting external contributions.
