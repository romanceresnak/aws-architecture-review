# ─── Lambda Execution Role ───────────────────────────────────────────────────

data "aws_iam_policy_document" "lambda_assume_role" {
  statement {
    effect = "Allow"
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role" "lambda_exec" {
  name               = "${local.name_prefix}-lambda-exec"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
}

# ─── CloudWatch Logs ─────────────────────────────────────────────────────────

resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# ─── S3 Access ────────────────────────────────────────────────────────────────

data "aws_iam_policy_document" "s3_access" {
  statement {
    sid    = "S3ReadWrite"
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject",
    ]
    resources = [
      "${aws_s3_bucket.main.arn}/uploads/*",
      "${aws_s3_bucket.main.arn}/reports/*",
    ]
  }

  statement {
    sid    = "S3PresignedUrl"
    effect = "Allow"
    actions = [
      "s3:PutObject",
    ]
    resources = [
      "${aws_s3_bucket.main.arn}/uploads/*",
    ]
  }
}

resource "aws_iam_role_policy" "s3_access" {
  name   = "s3-access"
  role   = aws_iam_role.lambda_exec.id
  policy = data.aws_iam_policy_document.s3_access.json
}

# ─── Amazon Bedrock Access ────────────────────────────────────────────────────

data "aws_iam_policy_document" "bedrock_access" {
  statement {
    sid    = "BedrockInvokeModel"
    effect = "Allow"
    actions = [
      "bedrock:InvokeModel",
    ]
    resources = [
      # Amazon Nova models in us-east-1 (no cross-region routing needed)
      "arn:aws:bedrock:${var.aws_region}::foundation-model/${var.bedrock_model_id}",
      "arn:aws:bedrock:${var.aws_region}::foundation-model/*",
    ]
  }
}

resource "aws_iam_role_policy" "bedrock_access" {
  name   = "bedrock-access"
  role   = aws_iam_role.lambda_exec.id
  policy = data.aws_iam_policy_document.bedrock_access.json
}
