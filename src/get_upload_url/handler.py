"""
Lambda: get-upload-url
Returns a presigned S3 PUT URL and a unique jobId.
Triggered by: API Gateway POST /upload
"""

import json
import os
import uuid
import boto3
from botocore.exceptions import ClientError
from botocore.config import Config

# Configure S3 client with signature version and regional endpoint
s3_config = Config(
    signature_version='s3v4',
    s3={'addressing_style': 'path'}
)
s3 = boto3.client("s3", config=s3_config, region_name=os.environ.get("BUCKET_REGION", "eu-west-1"))
BUCKET_NAME = os.environ["BUCKET_NAME"]


def lambda_handler(event, context):
    try:
        body = json.loads(event.get("body") or "{}")
        file_type = body.get("fileType", "image/png")
        extension = _extension_for(file_type)

        job_id = str(uuid.uuid4())
        object_key = f"uploads/{job_id}{extension}"

        presigned_url = s3.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": BUCKET_NAME,
                "Key": object_key,
                "ContentType": file_type,
            },
            ExpiresIn=300,  # 5 minutes
        )

        return _response(200, {"uploadUrl": presigned_url, "jobId": job_id})

    except ClientError as e:
        print(f"AWS error: {e}")
        return _response(500, {"error": "Failed to generate upload URL"})
    except Exception as e:
        print(f"Unexpected error: {e}")
        return _response(500, {"error": str(e)})


def _extension_for(mime_type: str) -> str:
    mapping = {
        "image/png": ".png",
        "image/jpeg": ".jpg",
        "image/jpg": ".jpg",
        "image/webp": ".webp",
        "application/pdf": ".pdf",
        "application/xml": ".xml",
        "text/xml": ".xml",
        "image/svg+xml": ".svg",
    }
    return mapping.get(mime_type, ".png")


def _response(status_code: int, body: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Allow-Methods": "OPTIONS,POST,GET",
        },
        "body": json.dumps(body),
    }
