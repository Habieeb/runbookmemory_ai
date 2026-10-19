import boto3

client = boto3.client("bedrock-runtime", region_name="us-west-2")

response = client.converse(
    modelId="us.amazon.nova-micro-v1:0",
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "text": (
                        "You are an IT incident analyst. "
                        "A Linux host reports memory usage of 73%, "
                        "above a temporary monitoring threshold of 70%. "
                        "Explain two safe investigation steps. "
                        "Do not recommend automatic remediation."
                    )
                }
            ],
        }
    ],
    inferenceConfig={
        "maxTokens": 150,
        "temperature": 0.2,
    },
)

print("Model response:")
for block in response["output"]["message"]["content"]:
    if "text" in block:
        print(block["text"])

print("\nToken usage:", response.get("usage"))
