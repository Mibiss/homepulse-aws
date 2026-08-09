locals {
  common_tags = {
    Project     = "HomePulse"
    Environment = var.environment
    ManagedBy   = "Terraform"
    Repository  = "homepulse-aws"
  }

  lambda_logging_policy_arn = "arn:${data.aws_partition.current.partition}:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"

}
