locals {
  common_tags = {
    Project     = "HomePulse"
    Environment = var.environment
    ManagedBy   = "Terraform"
    Repository  = "homepulse-aws"
  }

  lambda_logging_policy_arn = join("", [
    "arn:",
    data.aws_partition.current.partition,
    ":iam::",
    data.aws_caller_identity.current.account_id,
    ":policy/service-role/",
    "AWSLambdaBasicExecutionRole-2c2367e4-5a30-49bf-95b2-833c79646f77"
  ])

}
