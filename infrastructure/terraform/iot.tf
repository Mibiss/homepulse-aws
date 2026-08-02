resource "aws_iot_topic_rule" "telemetry_ingestion" {
  name        = "homepulse_telemetry_ingestion"
  description = "Routes HomePulse telemetry to the ingestion Lambda function."

  enabled     = true
  sql         = "SELECT * FROM 'homepulse/${var.device_id}/telemetry'"
  sql_version = "2016-03-23"

  lambda {
    function_arn = aws_lambda_function.ingestion.arn
  }
}

resource "aws_lambda_permission" "allow_iot" {
  statement_id = "homepulse_telemetry_ingestion"

  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.ingestion.function_name
  principal     = "iot.amazonaws.com"

  source_arn     = aws_iot_topic_rule.telemetry_ingestion.arn
  source_account = data.aws_caller_identity.current.account_id
}