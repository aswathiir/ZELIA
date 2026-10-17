import boto3
from botocore.client import Config

s3 = boto3.client(
    's3',
    endpoint_url='http://localhost:9000',
    aws_access_key_id='minioadmin',
    aws_secret_access_key='minioadmin_secure_2024',
    config=Config(signature_version='s3v4')
)

buckets = ['zelia-raw', 'zelia-processed', 'zelia-templates', 'zelia-icons', 'zelia-audio']

for bucket in buckets:
    try:
        s3.head_bucket(Bucket=bucket)
        print(f'✓ Bucket {bucket} exists')
    except:
        s3.create_bucket(Bucket=bucket)
        print(f'✓ Created bucket {bucket}')