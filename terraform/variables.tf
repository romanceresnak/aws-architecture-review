variable "aws_region" {
  description = "AWS region to deploy resources"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Name prefix for all resources"
  type        = string
  default     = "arch-reviewer"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "bedrock_model_id" {
  description = "Amazon Bedrock model ID to use for architecture analysis"
  type        = string
  default     = "amazon.nova-pro-v1:0"
}

variable "lambda_timeout" {
  description = "Lambda function timeout in seconds"
  type        = number
  default     = 300
}

variable "lambda_memory" {
  description = "Lambda function memory in MB"
  type        = number
  default     = 512
}

variable "upload_expiry_days" {
  description = "Days to keep uploaded diagrams in S3"
  type        = number
  default     = 7
}

variable "report_expiry_days" {
  description = "Days to keep generated reports in S3"
  type        = number
  default     = 30
}
