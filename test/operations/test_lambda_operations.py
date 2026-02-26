"""Test Lambda invoke operation"""
import time
import sys
from pathlib import Path

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.resources.lambda_function import LambdaFunction
from src.resources.iam_role import IamRole
from test.resources.env_helper import load_env


def test_lambda_invoke():
    """Test Lambda invoke operation"""
    env = load_env()

    # Create IAM Role for Lambda
    assume_role_policy = {
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"Service": "lambda.amazonaws.com"},
            "Action": "sts:AssumeRole"
        }]
    }

    iam_role = IamRole(
        role_name="test-lambda-ops-role",
        assume_role_policy=assume_role_policy,
        env=env,
        managed_policies=["arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"]
    )

    try:
        print("Creating IAM Role...")
        role_arn = iam_role.create()
        print(f"✓ IAM Role created: {role_arn}\n")
        time.sleep(10)
    except Exception as e:
        print(f"Using existing IAM Role: {e}\n")
        role_arn = f"arn:aws:iam::{env.account}:role/test-lambda-ops-role"

    code_path = Path(__file__).parent.parent.parent / "functions" / "hallo_welt"

    lambda_func = LambdaFunction(
        function_name="test-lambda-operations",
        handler="lambda_function.lambda_handler",
        runtime="python3.13",
        code_path=code_path,
        role_arn=role_arn,
        env=env
    )

    try:
        print("=" * 60)
        print("Testing Lambda Operations")
        print("=" * 60)

        # Create Lambda
        print("\n1. Creating Lambda Function...")
        lambda_arn = lambda_func.create()
        print(f"✓ Lambda created: {lambda_arn}")
        time.sleep(5)

        # Test invoke with payload
        print("\n2. Testing invoke with payload...")
        result = lambda_func.invoke(payload={"name": "Test"})
        assert result['StatusCode'] == 200, f"Expected StatusCode 200, got {result['StatusCode']}"
        print(f"✓ Invoke successful: {result}")

        # Test invoke without payload
        print("\n3. Testing invoke without payload...")
        result = lambda_func.invoke()
        assert result['StatusCode'] == 200, f"Expected StatusCode 200, got {result['StatusCode']}"
        print(f"✓ Invoke successful: {result}")

        # Test async invoke
        print("\n4. Testing async invoke...")
        result = lambda_func.invoke(payload={"async": True}, invocation_type="Event")
        assert result['StatusCode'] == 202, f"Expected StatusCode 202 for async, got {result['StatusCode']}"
        print(f"✓ Async invoke successful: {result}")

        print("\n✓ All Lambda operation tests passed!")

    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup
        print("\n5. Cleaning up Lambda Function...")
        try:
            lambda_func.delete(lambda_arn)
            print("✓ Lambda deleted")
        except Exception as e:
            print(f"Warning: Could not delete Lambda: {e}")

        print("\n6. Cleaning up IAM Role...")
        try:
            iam_role.delete(role_arn)
            print("✓ IAM Role deleted")
        except Exception as e:
            print(f"Warning: Could not delete IAM Role: {e}")


if __name__ == "__main__":
    test_lambda_invoke()
