from src.model import AwsEnviroment
from src.resources.s3 import S3
from test.resources.resource_tester import ResourceTester


def test_s3():
    """Testet S3 Resource"""
    env = AwsEnviroment(
        profile="default",
        region="eu-central-1",
        account="745243048623"
    )

    tester = ResourceTester(env)

    s3_resource = S3(
        bucket_name="test-myzel-s3-bucket-123456",
        env=env
    )
    s3_modified = S3(
        bucket_name="test-myzel-s3-bucket-123456",
        env=env,
        policy={
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": "s3:GetObject",
                    "Resource": "arn:aws:s3:::test-myzel-s3-bucket-123456/*"
                }
            ]
        }
    )

    tester.test_resource("S3", s3_resource, s3_modified)
    tester.print_summary()


if __name__ == "__main__":
    test_s3()
