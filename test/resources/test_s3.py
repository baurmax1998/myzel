from src.resources.s3 import S3
from test.resources.resource_tester import ResourceTester
from test.resources.env_helper import load_env


def test_s3():
    """Testet S3 Resource"""
    env = load_env()

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
                    "Principal": {
                        "AWS": f"arn:aws:iam::{env.account}:root"
                    },
                    "Action": "s3:*",
                    "Resource": [
                        "arn:aws:s3:::test-myzel-s3-bucket-123456",
                        "arn:aws:s3:::test-myzel-s3-bucket-123456/*"
                    ]
                }
            ]
        }
    )

    tester.test_resource("S3", s3_resource, s3_modified)
    tester.print_summary()


if __name__ == "__main__":
    test_s3()
