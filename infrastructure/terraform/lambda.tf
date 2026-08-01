data "archive_file" "lambda_ingestion" {
  type = "zip"

  source_file = "${path.module}/../../cloud/lambda/lambda_function.py"
  output_path = "${path.module}/build/homepulse-ingestion.zip"
}

resource "aws_lambda_function" "ingestion" {
  function_name = "homepulse-ingestion"
  description   = "Processes HomePulse telemetry from AWS IoT Core."

  role    = aws_iam_role.lambda_execution.arn
  handler = "lambda_function.lambda_handler"

  runtime       = "python3.14"
  architectures = ["arm64"]

  filename         = data.archive_file.lambda_ingestion.output_path
  source_code_hash = data.archive_file.lambda_ingestion.output_base64sha256

  memory_size = 128
  timeout     = 3

  publish = false

  environment {
    variables = {
      DYNAMODB_TABLE   = aws_dynamodb_table.telemetry.name
      METRIC_NAMESPACE = "HomePulse"
      ALLOWED_DEVICES  = var.device_id
    }
  }
}
