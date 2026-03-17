"""
Lambda: architecture-reviewer
Triggered by S3 upload event.
Reads the diagram, sends it to Amazon Bedrock (Claude), stores report JSON back to S3.
"""

import json
import os
import base64
import boto3
from botocore.exceptions import ClientError

BUCKET_NAME = os.environ["BUCKET_NAME"]
BEDROCK_MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "amazon.nova-pro-v1:0")
BEDROCK_REGION = os.environ.get("BEDROCK_REGION", "us-east-1")

s3 = boto3.client("s3")
bedrock = boto3.client("bedrock-runtime", region_name=BEDROCK_REGION)

ANALYSIS_PROMPT = """You are an expert AWS Solutions Architect with deep knowledge of the AWS Well-Architected Framework.

Analyze the provided architecture diagram and produce a structured review in the following JSON format ONLY (no markdown, no explanation outside JSON):

{
  "status": "completed",
  "summary": "One paragraph executive summary of the architecture",
  "overallRisk": "HIGH | MEDIUM | LOW",
  "pillarScores": {
    "operationalExcellence": { "score": 1-5, "comment": "brief comment" },
    "security": { "score": 1-5, "comment": "brief comment" },
    "reliability": { "score": 1-5, "comment": "brief comment" },
    "performanceEfficiency": { "score": 1-5, "comment": "brief comment" },
    "costOptimization": { "score": 1-5, "comment": "brief comment" },
    "sustainability": { "score": 1-5, "comment": "brief comment" }
  },
  "issues": [
    {
      "severity": "CRITICAL | HIGH | MEDIUM | LOW",
      "pillar": "Well-Architected pillar name",
      "title": "Short issue title",
      "description": "Detailed description of the problem",
      "impact": "What could go wrong"
    }
  ],
  "recommendations": [
    {
      "priority": "HIGH | MEDIUM | LOW",
      "title": "Short recommendation title",
      "description": "Detailed actionable recommendation",
      "awsServices": ["list", "of", "relevant", "AWS", "services"]
    }
  ],
  "wellArchitectedRisks": [
    {
      "pillar": "Pillar name",
      "risk": "HIGH | MEDIUM | LOW",
      "finding": "Specific Well-Architected finding"
    }
  ],
  "detectedServices": ["list of AWS services detected in the diagram"],
  "positives": ["list of things done well in this architecture"]
}

Be thorough, specific, and actionable. Look for:
- Single points of failure
- Missing redundancy / Multi-AZ
- Security gaps (exposed endpoints, missing WAF, no encryption)
- Missing caching layers
- Over/under-provisioned resources
- Cost inefficiencies
- Lack of observability (no CloudWatch, no tracing)
- Data backup / DR gaps
- Network security (NACLs, Security Groups too permissive)
- IAM least privilege violations

If the image is not an architecture diagram, return:
{"status": "error", "message": "The uploaded file does not appear to be an architecture diagram."}
"""


def lambda_handler(event, context):
    for record in event.get("Records", []):
        bucket = record["s3"]["bucket"]["name"]
        key = record["s3"]["object"]["key"]

        print(f"Processing: s3://{bucket}/{key}")

        # Extract jobId from key: uploads/<jobId>.<ext>
        filename = key.split("/")[-1]
        job_id = filename.rsplit(".", 1)[0]
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "png"

        try:
            # Read file from S3
            obj = s3.get_object(Bucket=bucket, Key=key)
            file_bytes = obj["Body"].read()
            content_type = obj.get("ContentType", "image/png")

            print(f"File size: {len(file_bytes)} bytes, type: {content_type}, ext: {ext}")

            # Build Bedrock message
            if ext in ("png", "jpg", "jpeg", "webp", "gif"):
                message_content = _build_image_message(file_bytes, ext)
            elif ext in ("pdf",):
                message_content = _build_text_message(
                    f"[PDF file uploaded — {len(file_bytes)} bytes. Treat this as an architecture document and analyze based on common AWS PDF architecture diagrams.]"
                )
            elif ext in ("xml", "drawio"):
                xml_text = file_bytes.decode("utf-8", errors="replace")[:8000]
                message_content = _build_text_message(
                    f"This is a draw.io XML architecture diagram. Analyze the following XML for AWS architecture review:\n\n{xml_text}"
                )
            else:
                message_content = _build_text_message(
                    f"Architecture file ({ext}) uploaded. Analyze based on what you can infer."
                )

            # Call Bedrock
            report = _invoke_bedrock(message_content)
            report["jobId"] = job_id

            # Save report to S3
            report_key = f"reports/{job_id}.json"
            s3.put_object(
                Bucket=BUCKET_NAME,
                Key=report_key,
                Body=json.dumps(report, ensure_ascii=False, indent=2),
                ContentType="application/json",
            )
            print(f"Report saved: s3://{BUCKET_NAME}/{report_key}")

        except Exception as e:
            print(f"Error processing {job_id}: {e}")
            # Save error report so frontend doesn't poll forever
            error_report = {
                "status": "error",
                "jobId": job_id,
                "message": f"Analysis failed: {str(e)}",
            }
            try:
                s3.put_object(
                    Bucket=BUCKET_NAME,
                    Key=f"reports/{job_id}.json",
                    Body=json.dumps(error_report),
                    ContentType="application/json",
                )
            except Exception as save_err:
                print(f"Could not save error report: {save_err}")


def _build_image_message(file_bytes: bytes, ext: str) -> list:
    media_type_map = {
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "webp": "image/webp",
        "gif": "image/gif",
    }
    media_type = media_type_map.get(ext, "image/png")
    b64 = base64.standard_b64encode(file_bytes).decode("utf-8")

    # Check if using Claude or Amazon Nova
    if "anthropic" in BEDROCK_MODEL_ID.lower():
        # Claude format
        return [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": b64,
                },
            },
            {"type": "text", "text": ANALYSIS_PROMPT},
        ]
    else:
        # Amazon Nova format
        return [
            {
                "image": {
                    "format": ext,
                    "source": {"bytes": b64}
                }
            },
            {"text": ANALYSIS_PROMPT},
        ]


def _build_text_message(text: str) -> list:
    return [{"type": "text", "text": f"{text}\n\n{ANALYSIS_PROMPT}"}]


def _invoke_bedrock(content: list) -> dict:
    # Check if using Claude or Amazon Nova
    if "anthropic" in BEDROCK_MODEL_ID.lower():
        # Claude API format
        payload = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 4096,
            "messages": [{"role": "user", "content": content}],
        }
    else:
        # Amazon Nova API format
        payload = {
            "messages": [{"role": "user", "content": content}],
            "inferenceConfig": {"max_new_tokens": 4096},
        }

    response = bedrock.invoke_model(
        modelId=BEDROCK_MODEL_ID,
        contentType="application/json",
        accept="application/json",
        body=json.dumps(payload),
    )

    response_body = json.loads(response["body"].read())

    # Extract text from response (different structure for Claude vs Nova)
    if "anthropic" in BEDROCK_MODEL_ID.lower():
        raw_text = response_body["content"][0]["text"].strip()
    else:
        # Amazon Nova response structure
        raw_text = response_body["output"]["message"]["content"][0]["text"].strip()

    # Strip markdown code fences if present
    if raw_text.startswith("```"):
        raw_text = raw_text.split("```")[1]
        if raw_text.startswith("json"):
            raw_text = raw_text[4:]
        raw_text = raw_text.strip()

    return json.loads(raw_text)
