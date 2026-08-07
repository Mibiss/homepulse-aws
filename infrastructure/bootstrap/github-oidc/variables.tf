variable "aws_region" {
  description = "AWS region used by HomePulse."
  type        = string
  default     = "eu-central-1"
}

variable "github_owner" {
  description = "GitHub account or organization that owns the repository."
  type        = string
  default     = "Mibiss"
}

variable "github_repository" {
  description = "GitHub repository allowed to deploy HomePulse."
  type        = string
  default     = "homepulse-aws"
}

variable "github_environment" {
  description = "Protected GitHub environment allowed to deploy."
  type        = string
  default     = "production"
}

variable "terraform_state_bucket_name" {
  description = "Existing S3 bucket containing the HomePulse Terraform state."
  type        = string
}

variable "github_oidc_subject" {
  description = "Exact GitHub OIDC subject allowed to deploy HomePulse."
  type        = string
}