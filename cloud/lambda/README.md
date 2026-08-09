# HomePulse Ingestion Lambda

The HomePulse ingestion Lambda receives telemetry from AWS IoT Core, validates it, stores the full event in DynamoDB, and publishes selected measurements to CloudWatch.

## Responsibilities

- Validate telemetry schema and device ID
- Reject invalid or stale timestamps
- Store telemetry in DynamoDB
- Add DynamoDB TTL metadata
- Publish CloudWatch custom metrics
- Emit structured JSON logs
- Publish the `AgentHeartbeat` metric
- Re-raise processing failures so Lambda retries and failure destinations can work

## Environment Variables

- `DYNAMODB_TABLE`
- `METRIC_NAMESPACE`
- `ALLOWED_DEVICES`
- `RETENTION_DAYS`
- `LOG_LEVEL`

## Failure Handling

The function distinguishes between:

- telemetry validation errors
- DynamoDB SDK failures
- CloudWatch publishing failures
- metric validation failures

AWS service failures are logged with structured diagnostic fields and re-raised.

Failed asynchronous invocations that exhaust retries are sent to the configured SQS failure queue.

## Testing

From the repository root:

```bash
pytest tests/unit/test_lambda_function.py -v