import os

import boto3
import json
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()


def serialize_datetime(obj):
    """JSON serializer for datetime objects"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")


def get_cloudfront_distribution_info(distribution_id: str) -> dict:
    """
    Retrieve all information about a CloudFront distribution.

    Args:
        distribution_id: The CloudFront distribution ID (e.g., 'E1EZPQ7LIRIK83')

    Returns:
        dict: Complete distribution information
    """

    session = boto3.session.Session(
        profile_name=os.getenv("AWS_PROFILE"),
        region_name=os.getenv("AWS_REGION")
    )
    client = session.client('cloudfront')

    result = {}

    # Get distribution configuration and metadata
    try:
        response = client.get_distribution(Id=distribution_id)
        result['distribution'] = response['Distribution']
        result['etag'] = response['ETag']
    except Exception as e:
        result['error_distribution'] = str(e)

    # Get distribution configuration only
    try:
        response = client.get_distribution_config(Id=distribution_id)
        result['distribution_config'] = response['DistributionConfig']
        result['config_etag'] = response['ETag']
    except Exception as e:
        result['error_config'] = str(e)

    # Get tags
    try:
        arn = f"arn:aws:cloudfront::745243048623:distribution/{distribution_id}"
        response = client.list_tags_for_resource(Resource=arn)
        result['tags'] = response.get('Tags', {})
    except Exception as e:
        result['error_tags'] = str(e)

    return result


if __name__ == "__main__":
    distribution_id = "E119T2J1I45FI2"
    distribution_id = "E3FCJ7NX9ZWE74"

    print(f"Fetching information for CloudFront distribution: {distribution_id}")

    info = get_cloudfront_distribution_info(distribution_id)

    # Print formatted JSON
    print("\n" + "=" * 80)
    print("CloudFront Distribution Information:")
    print("=" * 80 + "\n")
    print(json.dumps(info, indent=2, default=serialize_datetime))

    # Optionally save to file
    output_file = f"cloudfront_distribution_{distribution_id}.json"
    with open(output_file, 'w') as f:
        json.dump(info, f, indent=2, default=serialize_datetime)

    print(f"\n\nInformation saved to: {output_file}")
