resource "aws_sqs_queue" "lambda_failures" {
  name = "homepulse-lambda-failures"

  message_retention_seconds = 1209600

  sqs_managed_sse_enabled = true
}

