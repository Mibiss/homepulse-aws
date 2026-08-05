variable "aws_region" {
  description = "AWS Region used by HomePulse."
  type        = string
  default     = "eu-central-1"

  validation {
    condition     = var.aws_region == "eu-central-1"
    error_message = "HomePulse is currently deployed in eu-central-1."
  }
}

variable "project_name" {
  description = "Short project name used for naming and tagging."
  type        = string
  default     = "homepulse"
}

variable "environment" {
  description = "Deployment environment."
  type        = string
  default     = "prod"

  validation {
    condition = contains(
      ["dev", "uat", "prod"],
      var.environment
    )

    error_message = "Environment must be dev, uat, or prod."
  }
}

variable "device_id" {
  description = "HomePulse monitoring-agent device ID."
  type        = string
  default     = "homepulse-agent-01"
}

variable "dynamodb_table_name" {
  description = "Name of the existing HomePulse telemetry table."
  type        = string
  default     = "homepulse-network-metrics"
}
