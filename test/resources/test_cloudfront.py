from src.resources.s3 import S3
from src.resources.cloudfront import CloudFront
from test.resources.resource_tester import ResourceTester
from test.resources.env_helper import load_env


def test_cloudfront():
    """Testet CloudFront Resource"""
    env = load_env()

    tester = ResourceTester(env)

    # Create S3 Bucket for CloudFront origin
    s3_bucket = S3(
        bucket_name="test-myzel-cf-bucket-123456",
        env=env
    )

    try:
        bucket_arn = s3_bucket.create()
        print(f"Created S3 Bucket: {bucket_arn}\n")
    except Exception as e:
        print(f"Using existing S3 Bucket: {e}\n")
        bucket_arn = "arn:aws:s3:::test-myzel-cf-bucket-123456"

    # Test CloudFront with S3 origin
    cloudfront_resource = CloudFront(
        env=env,
        bucket_name="test-myzel-cf-bucket-123456",
        distribution_name="test-myzel-cf-123456"
    )

    # For the modified version, we can add an API Gateway endpoint
    # But for simplicity, we'll just test with S3
    cloudfront_modified = CloudFront(
        env=env,
        bucket_name="test-myzel-cf-bucket-123456",
        distribution_name="test-myzel-cf-123456-modified"
    )

    tester.test_resource("CloudFront", cloudfront_resource, cloudfront_modified)
    tester.print_summary()

    # Cleanup
    try:
        s3_bucket.delete(bucket_arn)
        print(f"Cleaned up S3 Bucket")
    except Exception as e:
        print(f"Could not cleanup S3 Bucket: {e}")


if __name__ == "__main__":
    test_cloudfront()
