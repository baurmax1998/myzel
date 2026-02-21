import os
import uuid

import boto3
from dotenv import load_dotenv

load_dotenv()


def create_cloudfront_distribution_for_s3(bucket_name: str) -> dict:
    """
    Create a CloudFront distribution for an S3 bucket website.

    Args:
        bucket_name: The S3 bucket name (e.g., 'testmb-652-web')

    Returns:
        dict: Created distribution information including ID and domain name
    """
    session = boto3.session.Session(
        profile_name=os.getenv("AWS_PROFILE"),
        region_name=os.getenv("AWS_REGION")
    )
    cloudfront_client = session.client('cloudfront')
    s3_client = session.client('s3')

    # Get bucket region
    bucket_location = s3_client.get_bucket_location(Bucket=bucket_name)
    bucket_region = bucket_location['LocationConstraint'] or 'us-east-1'

    # Construct S3 domain name
    s3_domain = f"{bucket_name}.s3.{bucket_region}.amazonaws.com"

    # Generate unique origin ID
    origin_id = f"{s3_domain}-{uuid.uuid4().hex[:11]}"

    # Create Origin Access Control (OAC) first
    oac_response = cloudfront_client.create_origin_access_control(
        OriginAccessControlConfig={
            'Name': f'OAC-{bucket_name}-{uuid.uuid4().hex[:8]}',
            'Description': f'Origin Access Control for {bucket_name}',
            'SigningProtocol': 'sigv4',
            'SigningBehavior': 'always',
            'OriginAccessControlOriginType': 's3'
        }
    )
    oac_id = oac_response['OriginAccessControl']['Id']

    # Create CloudFront distribution config
    distribution_config = {
        'CallerReference': str(uuid.uuid4()),
        'Comment': f'CloudFront distribution for {bucket_name}',
        'Enabled': True,
        'Origins': {
            'Quantity': 1,
            'Items': [
                {
                    'Id': origin_id,
                    'DomainName': s3_domain,
                    'OriginPath': '',
                    'CustomHeaders': {
                        'Quantity': 0
                    },
                    'S3OriginConfig': {
                        'OriginAccessIdentity': '',
                        'OriginReadTimeout': 30
                    },
                    'ConnectionAttempts': 3,
                    'ConnectionTimeout': 10,
                    'OriginShield': {
                        'Enabled': False
                    },
                    'OriginAccessControlId': oac_id
                }
            ]
        },
        'OriginGroups': {
            'Quantity': 0
        },
        'DefaultCacheBehavior': {
            'TargetOriginId': origin_id,
            'ViewerProtocolPolicy': 'redirect-to-https',
            'AllowedMethods': {
                'Quantity': 2,
                'Items': ['HEAD', 'GET'],
                'CachedMethods': {
                    'Quantity': 2,
                    'Items': ['HEAD', 'GET']
                }
            },
            'Compress': True,
            'CachePolicyId': '658327ea-f89d-4fab-a63d-7e88639e58f6',  # CachingOptimized
            'OriginRequestPolicyId': '88a5eaf4-2fd4-4709-b370-b4c650ea3fcf',  # CORS-S3Origin
            'TrustedSigners': {
                'Enabled': False,
                'Quantity': 0
            },
            'TrustedKeyGroups': {
                'Enabled': False,
                'Quantity': 0
            },
            'SmoothStreaming': False,
            'FieldLevelEncryptionId': ''
        },
        'CacheBehaviors': {
            'Quantity': 0
        },
        'CustomErrorResponses': {
            'Quantity': 0
        },
        'DefaultRootObject': '',
        'Aliases': {
            'Quantity': 0
        },
        'PriceClass': 'PriceClass_All',
        'ViewerCertificate': {
            'CloudFrontDefaultCertificate': True,
            'MinimumProtocolVersion': 'TLSv1.2_2021',
            'CertificateSource': 'cloudfront'
        },
        'HttpVersion': 'http2and3',
        'IsIPV6Enabled': True
    }

    # Create the distribution
    response = cloudfront_client.create_distribution(
        DistributionConfig=distribution_config
    )

    distribution = response['Distribution']

    result = {
        'distribution_id': distribution['Id'],
        'arn': distribution['ARN'],
        'domain_name': distribution['DomainName'],
        'status': distribution['Status'],
        'origin_access_control_id': oac_id,
        'etag': response['ETag']
    }

    print(f"CloudFront Distribution created successfully!")
    print(f"Distribution ID: {result['distribution_id']}")
    print(f"Domain Name: {result['domain_name']}")
    print(f"Status: {result['status']}")
    print(f"\nNote: Update your S3 bucket policy to allow CloudFront access using OAC ID: {oac_id}")

    return distribution['ARN']


if __name__ == "__main__":
    # Example usage
    bucket_name = "testmb-652-web"
    bucket_name = "my-example-testmb-bucket-22"

    distribution_info = create_cloudfront_distribution_for_s3(bucket_name)

    print("\n" + "="*80)
    print("Distribution Info:")
    print("="*80)
    for key, value in distribution_info.items():
        print(f"{key}: {value}")
