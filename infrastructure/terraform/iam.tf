data "aws_iam_policy_document" "lambda_assume_role" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "lambda_execution" {
  name = "homepulse-ingestion-role-sqlm07gg"
  path = "/service-role/"

  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
}

data "aws_iam_policy_document" "lambda_dynamodb" {
  statement {
    sid     = "WriteHomePulseTelemetry"
    effect  = "Allow"
    actions = ["dynamodb:PutItem"]

    resources = [
      aws_dynamodb_table.telemetry.arn
    ]
  }
}

resource "aws_iam_role_policy" "lambda_dynamodb" {
  name = "HomePulseDynamoDBWritePolicy"
  role = aws_iam_role.lambda_execution.name

  policy = data.aws_iam_policy_document.lambda_dynamodb.json
}

data "aws_iam_policy_document" "lambda_cloudwatch" {
  statement {
    sid     = "PublishHomePulseMetrics"
    effect  = "Allow"
    actions = ["cloudwatch:PutMetricData"]

    resources = ["*"]

    condition {
      test     = "StringEquals"
      variable = "cloudwatch:namespace"
      values   = ["HomePulse"]
    }
  }
}

resource "aws_iam_role_policy" "lambda_cloudwatch" {
  name = "HomePulseCloudWatchMetricsPolicy"
  role = aws_iam_role.lambda_execution.name

  policy = data.aws_iam_policy_document.lambda_cloudwatch.json
}

resource "aws_iam_role_policy_attachment" "lambda_logging" {
  role       = aws_iam_role.lambda_execution.name
  policy_arn = local.lambda_logging_policy_arn
}
