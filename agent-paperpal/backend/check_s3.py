import asyncio
import aioboto3
import os
from dotenv import load_dotenv

# Path to the .env file in the root
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env')
load_dotenv(env_path)

async def check():
    session = aioboto3.Session(
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID", "minioadmin"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY", "minioadmin"),
    )
    endpoint_url = os.getenv("AWS_S3_ENDPOINT_URL", "http://localhost:9000")
    bucket_name = os.getenv("AWS_S3_BUCKET", "paperpal-uploads")
    
    print(f"Connecting to {endpoint_url}...")
    print(f"Checking bucket: {bucket_name}")
    
    async with session.client("s3", endpoint_url=endpoint_url) as s3:
        try:
            res = await s3.list_buckets()
            buckets = [b['Name'] for b in res.get('Buckets', [])]
            print(f"Existing buckets: {buckets}")
            if bucket_name in buckets:
                print("Bucket exists!")
            else:
                print("Bucket NOT found!")
                # Try to create it here
                print(f"Attempting to create bucket '{bucket_name}'...")
                await s3.create_bucket(Bucket=bucket_name)
                print("Bucket created.")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(check())
