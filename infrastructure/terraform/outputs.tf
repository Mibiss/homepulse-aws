output "dynamodb_table_name" {
  description = "Name of the HomePulse telemetry table."
  value       = aws_dynamodb_table.telemetry.name
}

output "dynamodb_table_arn" {
  description = "ARN of the HomePulse telemetry table."
  value       = aws_dynamodb_table.telemetry.arn
}

output "lambda_failure_queue_arn" {
  description = "ARN of the Lambda asynchronous failure queue."
  value       = aws_sqs_queue.lambda_failures.arn
}
