"""
Master test runner for all resources.
Führt alle Resource-Tests nacheinander aus.
"""

from test.resources.test_s3 import test_s3
from test.resources.test_iam_role import test_iam_role
from test.resources.test_dynamodb import test_dynamodb
from test.resources.test_lambda import test_lambda
from test.resources.test_api_gateway import test_api_gateway
from test.resources.test_cloudfront import test_cloudfront


def main():
    """Führt alle Resource-Tests aus"""
    print("\n" + "="*60)
    print("MYZEL RESOURCE TEST SUITE")
    print("="*60)

    tests = [
        ("S3", test_s3),
        ("IAM Role", test_iam_role),
        ("DynamoDB", test_dynamodb),
        ("Lambda", test_lambda),
        ("API Gateway", test_api_gateway),
        ("CloudFront", test_cloudfront),
    ]

    results = []

    for test_name, test_func in tests:
        try:
            print(f"\n\n{'#'*60}")
            print(f"# Running {test_name} tests")
            print(f"{'#'*60}")
            test_func()
            results.append((test_name, "✓ PASSED"))
        except Exception as e:
            print(f"\n✗ {test_name} test failed: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, f"✗ FAILED: {str(e)[:50]}"))

    # Final summary
    print(f"\n\n{'='*60}")
    print("FINAL TEST SUMMARY")
    print(f"{'='*60}")
    for test_name, result in results:
        print(f"  {test_name:20s} {result}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
