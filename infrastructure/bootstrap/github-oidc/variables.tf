variable "aws_region" {
  description = "AWS region used by HomePulse."
  type        = string
  default     = "eu-central-1"
}

variable "terraform_state_bucket_name" {
  description = "Existing S3 bucket containing the HomePulse Terraform state."
  type        = string
}

variable "github_oidc_subject" {
  description = "Exact GitHub OIDC subject allowed to deploy HomePulse."
  type        = string
}