import os
from dotenv import load_dotenv
from src.core import deploy, diff, destroy
from src.model import AwsEnviroment, AwsApp
from src.resources.api_gateway import ApiGateway
from src.resources.cloudfront import CloudFront
from src.resources.dynamodb import DynamoDB
from src.resources.iam_role import IamRole
from src.resources.lambda_function import LambdaFunction
from src.resources.s3 import S3
from src.resources.s3_deploy import S3Deploy

load_dotenv()

app = AwsApp(name="example_1", env=AwsEnviroment(profile=os.getenv("AWS_PROFILE"),
                                                 account=os.getenv("AWS_ACCOUNT"),
                                                 region=os.getenv("AWS_REGION")), constructs={})

# IAM Roles zuerst erstellen
hello_role = IamRole(
    role_name="hallo-welt-lambda-role",
    assume_role_policy={
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {
                "Service": "lambda.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
        }]
    },
    managed_policies=[
        "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
    ],
    description="IAM Role für Hello Lambda",
    env=app.env
)
app.constructs["hello-role"] = hello_role

lambda_role = IamRole(
    role_name="lambda-todo-role",
    assume_role_policy={
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {
                "Service": "lambda.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
        }]
    },
    managed_policies=[
        "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
    ],
    inline_policies={
        "DynamoDBAccess": {
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Action": [
                    "dynamodb:PutItem",
                    "dynamodb:GetItem",
                    "dynamodb:UpdateItem",
                    "dynamodb:DeleteItem",
                    "dynamodb:Scan",
                    "dynamodb:Query"
                ],
                "Resource": f"arn:aws:dynamodb:{app.env.region}:{app.env.account}:table/todos"
            }]
        }
    },
    description="IAM Role für Lambda Functions mit DynamoDB Zugriff",
    env=app.env
)
app.constructs["01-hello-role"] = hello_role
app.constructs["02-lambda-role"] = lambda_role

# DynamoDB Todo Table
todo_table = DynamoDB(
    table_name="todos",
    partition_key={'name': 'id', 'type': 'S'},
    billing_mode="PAY_PER_REQUEST",
    env=app.env
)
app.constructs["03-todo-table"] = todo_table

# S3 Bucket erstellen
my_bucket = S3(bucket_name="my-example-testmb-bucket-22", policy={
    "Version": "2008-10-17",
    "Id": "PolicyForCloudFrontPrivateContent",
    "Statement": [{
        "Sid": "AllowCloudFrontServicePrincipal",
        "Effect": "Allow",
        "Principal": {"Service": "cloudfront.amazonaws.com"},
        "Action": "s3:GetObject",
        "Resource": "arn:aws:s3:::my-example-testmb-bucket-22/*"
    }]
}, env=app.env)
app.constructs["04-my-bucket"] = my_bucket

app.constructs["05-website"] = S3Deploy(
    bucket_name=my_bucket.bucket_name,
    local_path="./web/",
    s3_path="",
    env=app.env
)

# Lambda Functions
app.constructs["10-lambda-hello"] = LambdaFunction(
    function_name="hallo-welt",
    handler="lambda_function.lambda_handler",
    runtime="python3.13",
    code_path="./functions/hallo_welt",
    role_arn=hello_role.get_arn(),
    env=app.env
)

app.constructs["11-lambda-todo-create"] = LambdaFunction(
    function_name="todo-create",
    handler="lambda_function.lambda_handler",
    runtime="python3.13",
    code_path="./functions/todo_create",
    role_arn=lambda_role.get_arn(),
    environment_variables={"TABLE_NAME": "todos"},
    env=app.env
)

app.constructs["12-lambda-todo-list"] = LambdaFunction(
    function_name="todo-list",
    handler="lambda_function.lambda_handler",
    runtime="python3.13",
    code_path="./functions/todo_list",
    role_arn=lambda_role.get_arn(),
    environment_variables={"TABLE_NAME": "todos"},
    env=app.env
)

app.constructs["13-lambda-todo-update"] = LambdaFunction(
    function_name="todo-update",
    handler="lambda_function.lambda_handler",
    runtime="python3.13",
    code_path="./functions/todo_update",
    role_arn=lambda_role.get_arn(),
    environment_variables={"TABLE_NAME": "todos"},
    env=app.env
)

app.constructs["14-lambda-todo-delete"] = LambdaFunction(
    function_name="todo-delete",
    handler="lambda_function.lambda_handler",
    runtime="python3.13",
    code_path="./functions/todo_delete",
    role_arn=lambda_role.get_arn(),
    environment_variables={"TABLE_NAME": "todos"},
    env=app.env
)

# API Gateway
api_gateway = ApiGateway(
    api_name="my-app-api",
    routes={
        "/api/hello": {
            "method": "GET",
            "lambda_arn": f"arn:aws:lambda:{app.env.region}:{app.env.account}:function:hallo-welt",
            "lambda_name": "hallo-welt"
        },
        "/api/todos": {
            "method": "GET",
            "lambda_arn": f"arn:aws:lambda:{app.env.region}:{app.env.account}:function:todo-list",
            "lambda_name": "todo-list"
        },
        "/api/todos/create": {
            "method": "POST",
            "lambda_arn": f"arn:aws:lambda:{app.env.region}:{app.env.account}:function:todo-create",
            "lambda_name": "todo-create"
        },
        "/api/todos/{id}": {
            "method": "PUT",
            "lambda_arn": f"arn:aws:lambda:{app.env.region}:{app.env.account}:function:todo-update",
            "lambda_name": "todo-update"
        },
        "/api/todos/{id}": {
            "method": "DELETE",
            "lambda_arn": f"arn:aws:lambda:{app.env.region}:{app.env.account}:function:todo-delete",
            "lambda_name": "todo-delete"
        }
    },
    description="API Gateway für App",
    env=app.env
)
app.constructs["20-api-gateway"] = api_gateway

# CloudFront
app.constructs["30-cloudfront"] = CloudFront(
    bucket_name=my_bucket.bucket_name,
    api_gateway_endpoint=f"https://uvjfr5s7d6.execute-api.{app.env.region}.amazonaws.com",
    env=app.env
)



deploy(app)
