from src.resources.dynamodb import DynamoDB
from test.resources.resource_tester import ResourceTester
from test.resources.env_helper import load_env


def test_dynamodb():
    """Testet DynamoDB Resource"""
    env = load_env()

    tester = ResourceTester(env)

    dynamodb_resource = DynamoDB(
        table_name="test-myzel-dynamodb-123456",
        partition_key={"name": "id", "type": "S"},
        env=env
    )
    dynamodb_modified = DynamoDB(
        table_name="test-myzel-dynamodb-123456",
        partition_key={"name": "id", "type": "S"},
        sort_key={"name": "timestamp", "type": "N"},
        env=env,
        stream_enabled=True
    )

    tester.test_resource("DynamoDB", dynamodb_resource, dynamodb_modified)
    tester.print_summary()


if __name__ == "__main__":
    test_dynamodb()
