provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "HomePulse"
      Environment = "prod"
      ManagedBy   = "Terraform"
      Repository  = "homepulse-aws"
    }
  }
}