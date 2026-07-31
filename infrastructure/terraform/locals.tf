locals {
  common_tags = {
    Project     = "HomePulse"
    Environment = var.environment
    ManagedBy   = "Terraform"
    Repository  = "homepulse-aws"
  }
}
