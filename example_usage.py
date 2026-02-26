#!/usr/bin/env python3
"""
Beispiel für die Verwendung der Operation-Methoden auf Resource-Objekten
"""
import os
import json
from dotenv import load_dotenv
from src.model import AwsEnviroment
from src.resources.lambda_function import LambdaFunction
from src.resources.s3 import S3
from src.resources.dynamodb import DynamoDB

load_dotenv()

env = AwsEnviroment(
    profile=os.getenv("AWS_PROFILE"),
    account=os.getenv("AWS_ACCOUNT"),
    region=os.getenv("AWS_REGION")
)

# === Lambda Beispiel ===
print("=== Lambda Invoke ===")
hello_lambda = LambdaFunction(
    function_name="hallo-welt",
    handler="lambda_function.lambda_handler",
    runtime="python3.13",
    code_path="./functions/hallo_welt",
    role_arn="arn:aws:iam::745243048623:role/aa-simple-hallo-welt-lambda-role-rename",
    env=env
)

# Invoke the Lambda
result = hello_lambda.invoke(payload={"name": "World"})
print(f"Lambda Result: {result}\n")

# === S3 Beispiel ===
print("=== S3 Operations ===")
bucket = S3(bucket_name="my-example-testmb-bucket-22", env=env)

# List objects
objects = bucket.list()
print(f"Objekte im Bucket: {objects}\n")

# Upload a file
# bucket.upload("./test.txt", "uploads/test.txt")

# Download a file
# bucket.download("uploads/test.txt", "./downloaded.txt")

# Delete an object
# bucket.delete("uploads/test.txt")

# === DynamoDB Beispiel ===
print("=== DynamoDB Operations ===")
todos_table = DynamoDB(
    table_name="todos",
    partition_key={'name': 'id', 'type': 'S'},
    billing_mode="PAY_PER_REQUEST",
    env=env
)

# Add an item
# todos_table.put_item({
#     'id': '123',
#     'title': 'Buy milk',
#     'completed': False
# })

# Get an item
# item = todos_table.get_item({'id': '123'})

# Scan all items
items = todos_table.scan()
print(f"Alle Todos ({len(items)} Items):")
for item in items:
    print(f"  - {item}")

print("\n✓ Alle Operationen funktionieren!")
