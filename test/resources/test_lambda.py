from pathlib import Path
from src.model import AwsEnviroment
from src.resources.lambda_function import LambdaFunction
from src.resources.iam_role import IamRole
from test.resources.resource_tester import ResourceTester


def test_lambda():
    """Testet Lambda Function Resource"""
    env = AwsEnviroment(
        profile="default",
        region="eu-central-1",
        account="745243048623"
    )

    tester = ResourceTester(env)

    # Create IAM Role for Lambda first
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

    iam_role = IamRole(
        role_name="test-myzel-lambda-role-123456",
        assume_role_policy=assume_role_policy,
        env=env,
        managed_policies=["arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"]
    )

    try:
        role_arn = iam_role.create()
        print(f"Created IAM Role: {role_arn}\n")
    except Exception as e:
        print(f"Using existing IAM Role: {e}\n")
        role_arn = f"arn:aws:iam::745243048623:role/test-myzel-lambda-role-123456"

    # Test Lambda with simple code path
    lambda_resource = LambdaFunction(
        function_name="test-myzel-lambda-123456",
        handler="index.handler",
        runtime="python3.13",
        code_path=Path("functions/hallo_welt"),
        role_arn=role_arn,
        env=env
    )

    lambda_modified = LambdaFunction(
        function_name="test-myzel-lambda-123456",
        handler="index.handler",
        runtime="python3.13",
        code_path=Path("functions/hallo_welt"),
        role_arn=role_arn,
        env=env,
        timeout=60,
        memory_size=256,
        environment_variables={"TEST_VAR": "test_value"}
    )

    tester.test_resource("Lambda", lambda_resource, lambda_modified)
    tester.print_summary()

    # Cleanup IAM Role
    try:
        iam_role.delete(role_arn)
        print(f"Cleaned up IAM Role")
    except Exception as e:
        print(f"Could not cleanup IAM Role: {e}")


if __name__ == "__main__":
    test_lambda()
