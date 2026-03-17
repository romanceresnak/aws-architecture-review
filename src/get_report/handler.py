"""
Lambda: get-report
Reads the architecture review report JSON from S3 and returns it.
Triggered by: API Gateway GET /report/{jobId}
"""

import json
import os
import boto3
from botocore.exceptions import ClientError

s3 = boto3.client("s3")
BUCKET_NAME = os.environ["BUCKET_NAME"]


def lambda_handler(event, context):
    try:
        job_id = event.get("pathParameters", {}).get("jobId")
        if not job_id:
            return _response(400, {"error": "Missing jobId"})

        object_key = f"reports/{job_id}.json"

        try:
            obj = s3.get_object(Bucket=BUCKET_NAME, Key=object_key)
            report = json.loads(obj["Body"].read().decode("utf-8"))
            return _response(200, report)
        except ClientError as e:
            code = e.response["Error"]["Code"]
            if code in ("NoSuchKey", "404"):
                # Report not yet ready — tell frontend to keep polling
                return _response(202, {"status": "processing", "jobId": job_id})
            raise

    except Exception as e:
        print(f"Error fetching report: {e}")
        return _response(500, {"error": str(e)})


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
