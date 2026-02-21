import os
import time

import boto3
from dotenv import load_dotenv

load_dotenv()


def delete_cloudfront_distribution(distribution_arn: str) -> None:
    """
    Delete a CloudFront distribution.

    Args:
        distribution_arn: The ARN of the CloudFront distribution to delete
    """
    session = boto3.session.Session(
        profile_name=os.getenv("AWS_PROFILE"),
        region_name=os.getenv("AWS_REGION")
    )
    cloudfront_client = session.client('cloudfront')

    # Extract distribution ID from ARN
    distribution_id = distribution_arn.split('/')[-1]

    # Get current distribution config
    response = cloudfront_client.get_distribution_config(Id=distribution_id)
    distribution_config = response['DistributionConfig']
    etag = response['ETag']

    # Check if distribution is already disabled
    if distribution_config['Enabled']:
        print(f"Distribution {distribution_id} is enabled. Disabling it first...")

        # Disable the distribution
        distribution_config['Enabled'] = False
        cloudfront_client.update_distribution(
            DistributionConfig=distribution_config,
            Id=distribution_id,
            IfMatch=etag
        )

        print("Distribution disabled. Waiting for deployment to complete...")

        # Wait for distribution to be deployed
        while True:
            response = cloudfront_client.get_distribution(Id=distribution_id)
            status = response['Distribution']['Status']
            print(f"Current status: {status}")

            if status == 'Deployed':
                print("Distribution is now deployed and disabled.")
                etag = response['ETag']
                break

            time.sleep(30)
    else:
        print(f"Distribution {distribution_id} is already disabled.")

    # Delete the distribution
    print(f"Deleting distribution {distribution_id}...")
    cloudfront_client.delete_distribution(
        Id=distribution_id,
        IfMatch=etag
    )

    print(f"CloudFront Distribution {distribution_id} deleted successfully!")


if __name__ == "__main__":
    # Example usage
    distribution_arn = "arn:aws:cloudfront::745243048623:distribution/E2YY4MDF5W8XKP"

    delete_cloudfront_distribution(distribution_arn)
