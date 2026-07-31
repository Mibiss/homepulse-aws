output "dynamodb_table_name" {
  description = "Name of the HomePulse telemetry table."
  value       = aws_dynamodb_table.telemetry.name
}

output "dynamodb_table_arn" {
  description = "ARN of the HomePulse telemetry table."
  value       = aws_dynamodb_table.telemetry.arn
}
