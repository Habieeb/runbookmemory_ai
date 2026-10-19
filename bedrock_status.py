import boto3
from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError

REGION = "us-west-2"
MODEL_ID = "amazon.nova-2-lite-v1:0"

def check_bedrock():
    try:
        session = boto3.Session(
            profile_name="platform-lab-admin",
            region_name=REGION
        )

        client = session.client("bedrock")

        model = client.get_foundation_model(
            modelIdentifier=MODEL_ID
        )

        return {
            "connected": True,
            "inference_ready": False,
            "message": "AWS access verified · Inference quota blocked",
            "model": model["modelDetails"]["modelId"]
        }

    except (ClientError, BotoCoreError, NoCredentialsError) as exc:
        return {
            "connected": False,
            "inference_ready": False,
            "message": f"Bedrock access unavailable: {type(exc).__name__}",
            "model": None
        }
