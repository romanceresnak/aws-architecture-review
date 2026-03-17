output "api_url" {
  description = "Base URL of the API Gateway"
  value       = aws_api_gateway_stage.main.invoke_url
}

output "upload_endpoint" {
  description = "POST endpoint to get a presigned upload URL"
  value       = "${aws_api_gateway_stage.main.invoke_url}/upload"
}

output "report_endpoint" {
  description = "GET endpoint to retrieve a report (append /{jobId})"
  value       = "${aws_api_gateway_stage.main.invoke_url}/report"
}

output "bucket_name" {
  description = "S3 bucket where uploads and reports are stored"
  value       = aws_s3_bucket.main.bucket
}

output "reviewer_function_name" {
  description = "Name of the architecture reviewer Lambda function"
  value       = aws_lambda_function.reviewer.function_name
}

output "reviewer_function_log_group" {
  description = "CloudWatch log group for the reviewer Lambda"
  value       = aws_cloudwatch_log_group.reviewer.name
}

output "website_url" {
  description = "Public S3 website URL for the frontend"
  value       = "http://${aws_s3_bucket.main.bucket}.s3-website-${var.aws_region}.amazonaws.com"
}
