from pathlib import Path
from src.resources.api_gateway import ApiGateway
from src.resources.lambda_function import LambdaFunction
from src.resources.iam_role import IamRole
from test.resources.resource_tester import ResourceTester
from test.resources.env_helper import load_env


def test_api_gateway():
    """Testet API Gateway Resource"""
    import time
    env = load_env()

    tester = ResourceTester(env)

    # Create IAM Role for Lambda
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
        role_name="test-myzel-api-lambda-role-123456",
        assume_role_policy=assume_role_policy,
        env=env,
        managed_policies=["arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"]
    )

    try:
        role_arn = iam_role.create()
        print(f"Created IAM Role: {role_arn}\n")
        time.sleep(2)  # Wait for role to propagate
    except Exception as e:
        print(f"Using existing IAM Role: {e}\n")
        role_arn = f"arn:aws:iam::{env.account}:role/test-myzel-api-lambda-role-123456"

    # Create Lambda Function
    code_path = Path(__file__).parent.parent.parent / "functions" / "hallo_welt"

    lambda_function = LambdaFunction(
        function_name="test-myzel-api-lambda-123456",
        handler="index.handler",
        runtime="python3.13",
        code_path=code_path,
        role_arn=role_arn,
        env=env
    )

    try:
        lambda_arn = lambda_function.create()
        print(f"Created Lambda: {lambda_arn}\n")
        time.sleep(3)  # Wait for Lambda to be fully ready
    except Exception as e:
        print(f"Using existing Lambda: {e}\n")
        lambda_arn = f"arn:aws:lambda:{env.region}:{env.account}:function:test-myzel-api-lambda-123456"

    lambda_name = "test-myzel-api-lambda-123456"

    # Test API Gateway
    api_resource = ApiGateway(
        api_name="test-myzel-api-123456",
        routes={
            "/hello": {
                "method": "GET",
                "lambda_arn": lambda_arn,
                "lambda_name": lambda_name
            }
        },
        env=env,
        description="Test API Gateway"
    )

    api_modified = ApiGateway(
        api_name="test-myzel-api-123456",
        routes={
            "/hello": {
                "method": "GET",
                "lambda_arn": lambda_arn,
                "lambda_name": lambda_name
            },
            "/hello/{id}": {
                "method": "GET",
                "lambda_arn": lambda_arn,
                "lambda_name": lambda_name
            }
        },
        env=env,
        description="Test API Gateway with more routes"
    )

    tester.test_resource("API Gateway", api_resource, api_modified)
    tester.print_summary()

    # Cleanup
    try:
        lambda_function.delete(lambda_arn)
        print(f"Cleaned up Lambda")
    except Exception as e:
        print(f"Could not cleanup Lambda: {e}")

    try:
        iam_role.delete(role_arn)
        print(f"Cleaned up IAM Role")
    except Exception as e:
        print(f"Could not cleanup IAM Role: {e}")


if __name__ == "__main__":
    test_api_gateway()
