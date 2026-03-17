# ─── Lambda packages (built from local source) ────────────────────────────────

data "archive_file" "get_upload_url" {
  type        = "zip"
  source_dir  = "${path.module}/../src/get_upload_url"
  output_path = "${path.module}/lambda_packages/get_upload_url.zip"
}

data "archive_file" "reviewer" {
  type        = "zip"
  source_dir  = "${path.module}/../src/reviewer"
  output_path = "${path.module}/lambda_packages/reviewer.zip"
}

# ─── Lambda: get-upload-url ───────────────────────────────────────────────────

resource "aws_cloudwatch_log_group" "get_upload_url" {
  name              = "/aws/lambda/${local.name_prefix}-get-upload-url"
  retention_in_days = 14
}

resource "aws_lambda_function" "get_upload_url" {
  function_name    = "${local.name_prefix}-get-upload-url"
  description      = "Generates S3 presigned PUT URLs for diagram uploads"
  role             = aws_iam_role.lambda_exec.arn
  runtime          = "python3.12"
  handler          = "handler.lambda_handler"
  filename         = data.archive_file.get_upload_url.output_path
  source_code_hash = data.archive_file.get_upload_url.output_base64sha256
  timeout          = 30
  memory_size      = 128

  environment {
    variables = {
      BUCKET_NAME = aws_s3_bucket.main.bucket
      BUCKET_REGION = var.aws_region
    }
  }

  depends_on = [aws_cloudwatch_log_group.get_upload_url]
}

resource "aws_lambda_permission" "api_gw_invoke_get_upload_url" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.get_upload_url.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.main.execution_arn}/*/*"
}

# ─── Lambda: architecture-reviewer ────────────────────────────────────────────

resource "aws_cloudwatch_log_group" "reviewer" {
  name              = "/aws/lambda/${local.name_prefix}-reviewer"
  retention_in_days = 14
}

resource "aws_lambda_function" "reviewer" {
  function_name    = "${local.name_prefix}-reviewer"
  description      = "Analyzes architecture diagrams using Amazon Bedrock Claude"
  role             = aws_iam_role.lambda_exec.arn
  runtime          = "python3.12"
  handler          = "handler.lambda_handler"
  filename         = data.archive_file.reviewer.output_path
  source_code_hash = data.archive_file.reviewer.output_base64sha256
  timeout          = var.lambda_timeout
  memory_size      = var.lambda_memory

  environment {
    variables = {
      BUCKET_NAME    = aws_s3_bucket.main.bucket
      BEDROCK_MODEL_ID = var.bedrock_model_id
      AWS_ACCOUNT_ID = data.aws_caller_identity.current.account_id
      BEDROCK_REGION = var.aws_region
    }
  }

  depends_on = [aws_cloudwatch_log_group.reviewer]
}

resource "aws_lambda_permission" "s3_invoke_reviewer" {
  statement_id  = "AllowS3Invoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.reviewer.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.main.arn
}

# ─── Lambda: get-report (reads report from S3) ────────────────────────────────

data "archive_file" "get_report" {
  type        = "zip"
  source_dir  = "${path.module}/../src/get_report"
  output_path = "${path.module}/lambda_packages/get_report.zip"
}

resource "aws_cloudwatch_log_group" "get_report" {
  name              = "/aws/lambda/${local.name_prefix}-get-report"
  retention_in_days = 14
}

resource "aws_lambda_function" "get_report" {
  function_name    = "${local.name_prefix}-get-report"
  description      = "Returns architecture review report JSON from S3"
  role             = aws_iam_role.lambda_exec.arn
  runtime          = "python3.12"
  handler          = "handler.lambda_handler"
  filename         = data.archive_file.get_report.output_path
  source_code_hash = data.archive_file.get_report.output_base64sha256
  timeout          = 30
  memory_size      = 128

  environment {
    variables = {
      BUCKET_NAME = aws_s3_bucket.main.bucket
      BUCKET_REGION = var.aws_region
    }
  }

  depends_on = [aws_cloudwatch_log_group.get_report]
}

resource "aws_lambda_permission" "api_gw_invoke_get_report" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.get_report.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.main.execution_arn}/*/*"
}

# ─── Data sources ─────────────────────────────────────────────────────────────

data "aws_caller_identity" "current" {}
