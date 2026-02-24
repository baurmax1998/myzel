from src.model import AwsEnviroment
from src.resources.iam_role import IamRole
from test.resources.resource_tester import ResourceTester


def test_iam_role():
    """Testet IAM Role Resource"""
    env = AwsEnviroment(
        profile="default",
        region="eu-central-1",
        account="745243048623"
    )

    tester = ResourceTester(env)

    assume_role_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": "lambda.amazonaws.com"
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }

    iam_resource = IamRole(
        role_name="test-myzel-iam-role-123456",
        assume_role_policy=assume_role_policy,
        env=env
    )
    iam_modified = IamRole(
        role_name="test-myzel-iam-role-123456",
        assume_role_policy=assume_role_policy,
        env=env,
        managed_policies=["arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"],
        description="Test IAM Role for Lambda"
    )

    tester.test_resource("IAM Role", iam_resource, iam_modified)
    tester.print_summary()


if __name__ == "__main__":
    test_iam_role()
