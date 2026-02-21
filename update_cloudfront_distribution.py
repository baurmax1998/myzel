import os

import boto3
from dotenv import load_dotenv

load_dotenv()


def update_cloudfront_bucket(distribution_arn: str, new_bucket_name: str) -> str:
    """
    Update the S3 bucket origin of a CloudFront distribution.

    Args:
        distribution_arn: The ARN of the CloudFront distribution
        new_bucket_name: The new S3 bucket name

    Returns:
        str: Updated distribution ARN
    """
    session = boto3.session.Session(
        profile_name=os.getenv("AWS_PROFILE"),
        region_name=os.getenv("AWS_REGION")
    )
    cloudfront_client = session.client('cloudfront')
    s3_client = session.client('s3')

    # Extract distribution ID from ARN
    distribution_id = distribution_arn.split('/')[-1]

    # Get current distribution config
    response = cloudfront_client.get_distribution_config(Id=distribution_id)
    distribution_config = response['DistributionConfig']
    etag = response['ETag']

    # Get new bucket region
    bucket_location = s3_client.get_bucket_location(Bucket=new_bucket_name)
    bucket_region = bucket_location['LocationConstraint'] or 'us-east-1'

    # Construct new S3 domain name
    new_s3_domain = f"{new_bucket_name}.s3.{bucket_region}.amazonaws.com"

    # Update the origin domain name
    if distribution_config['Origins']['Quantity'] > 0:
        distribution_config['Origins']['Items'][0]['DomainName'] = new_s3_domain
        print(f"Updated origin domain to: {new_s3_domain}")
    else:
        raise ValueError("No origins found in distribution")

    # Update the distribution
    update_response = cloudfront_client.update_distribution(
        DistributionConfig=distribution_config,
        Id=distribution_id,
        IfMatch=etag
    )

    updated_distribution = update_response['Distribution']

    print(f"CloudFront Distribution updated successfully!")
    print(f"Distribution ID: {updated_distribution['Id']}")
    print(f"New Origin: {new_s3_domain}")
    print(f"Status: {updated_distribution['Status']}")

    return updated_distribution['ARN']


if __name__ == "__main__":
    # Example usage
    distribution_arn = "arn:aws:cloudfront::745243048623:distribution/E2YY4MDF5W8XKP"
    new_bucket_name = "testmb-652-web"
    # new_bucket_name = "my-example-testmb-bucket-22"

    updated_arn = update_cloudfront_bucket(distribution_arn, new_bucket_name)
    print(f"\nUpdated ARN: {updated_arn}")
