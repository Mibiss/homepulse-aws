# HomePulse Lambda Ingestion

This directory contains the AWS Lambda function that processes HomePulse telemetry received from AWS IoT Core.

The function validates each telemetry payload, stores the complete message in Amazon DynamoDB, and publishes selected measurements as Amazon CloudWatch custom metrics.

## File

```text
lambda_function.py
```

## Responsibilities

The function:

1. receives telemetry from an AWS IoT Rule
2. validates the schema version, device ID and timestamp
3. validates required network and system structures
4. converts floats to DynamoDB-compatible `Decimal` values
5. stores the complete telemetry payload in DynamoDB
6. publishes selected values as CloudWatch custom metrics
7. logs processing and failures to CloudWatch Logs

## Invocation

IoT Rule:

```text
homepulse_telemetry_ingestion
```

Rule SQL:

```sql
SELECT *
FROM 'homepulse/homepulse-agent-01/telemetry'
```

Lambda function:

```text
homepulse-ingestion
```

## Environment variables

Required:

```text
DYNAMODB_TABLE=homepulse-network-metrics
```

Optional:

```text
METRIC_NAMESPACE=HomePulse
ALLOWED_DEVICES=homepulse-agent-01
```

Multiple allowed devices can be supplied as a comma-separated list.

## Expected input

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

## Validation

The function requires schema version `1.0`, an allowed device ID, a timezone-aware ISO 8601 timestamp within 24 hours of the current time, and the expected `network` and `system` structures.

Latency and duration values may be `null` when a target is unavailable. CloudWatch metrics with unavailable values are skipped.

## DynamoDB storage

Table:

```text
homepulse-network-metrics
```

Keys:

```text
Partition key: device_id
Sort key:      timestamp
```

The write is idempotent for duplicate IoT deliveries because the same device ID and timestamp overwrite the same item.

## CloudWatch metrics

```text
Namespace: HomePulse
Dimension: DeviceId=<device_id>
```

Published metrics:

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

Boolean values are converted to `1` or `0`.

## Expected output

```json
{
  "statusCode": 200,
  "request_id": "example-request-id",
  "device_id": "homepulse-agent-01",
  "timestamp": "2026-07-25T11:13:05.616259+00:00",
  "dynamodb": "Telemetry stored successfully",
  "cloudwatch_metrics_published": 10
}
```

The metric count may be lower when optional values are unavailable.

## IAM permissions

DynamoDB write policy:

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

CloudWatch metric policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "PublishHomePulseMetrics",
      "Effect": "Allow",
      "Action": "cloudwatch:PutMetricData",
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "cloudwatch:namespace": "HomePulse"
        }
      }
    }
  ]
}
```

CloudWatch Logs permissions are normally supplied by `AWSLambdaBasicExecutionRole`.

The Lambda function also requires a resource-based permission allowing AWS IoT Core to invoke it.

## Runtime

```text
Runtime:      Python 3.14
Handler:      lambda_function.lambda_handler
Architecture: arm64
Region:       eu-central-1
```

`boto3` is included in the standard Lambda Python runtime.

## Deployment

### AWS Console

1. Open `homepulse-ingestion`.
2. Replace the code with `lambda_function.py`.
3. Choose **Deploy**.
4. Configure the environment variables.
5. Verify DynamoDB, CloudWatch and logging permissions.
6. Run a valid test event.
7. Confirm the DynamoDB item, custom metrics and logs.

### ZIP package

From `cloud/lambda/`:

```bash
zip lambda-package.zip lambda_function.py
```

The archive must contain `lambda_function.py` at its root.

Do not commit generated ZIP packages.

## Local syntax validation

From the repository root:

```bash
python3 -m py_compile cloud/lambda/lambda_function.py
```

## Manual test

Verify that:

1. the invocation succeeds
2. the response contains `statusCode: 200`
3. DynamoDB contains the expected item
4. CloudWatch contains the expected custom metrics
5. CloudWatch Logs contains a successful processing message

## Error handling

Validation and AWS service errors are logged and re-raised so failed invocations remain visible in Lambda monitoring and CloudWatch Logs.

## Operational monitoring

Logs:

```text
CloudWatch
-> Log groups
-> /aws/lambda/homepulse-ingestion
```

Monitor invocation count, error count, duration, throttles, missing records and missing metrics.

## Security

Do not put credentials or secrets in the source code. Use the Lambda execution role for AWS service access and keep IAM permissions restricted to the HomePulse resources and namespace.

## Future improvements

- Terraform provisioning
- automated packaging and deployment
- unit tests with mocked AWS clients
- dead-letter queue or failure destination
- structured JSON logging
- dedicated heartbeat metric
- formal JSON Schema validation
- versioned Lambda releases and aliases