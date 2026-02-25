import os
from dotenv import load_dotenv
from src.model import AwsEnviroment, MyzelApp
from src.resources.api_gateway import ApiGateway
from src.resources.cloudfront import CloudFront
from src.resources.dynamodb import DynamoDB
from src.resources.iam_role import IamRole
from src.resources.lambda_function import LambdaFunction
from src.resources.s3 import S3
from src.resources.s3_deploy import S3Deploy

load_dotenv()

app = MyzelApp(
    name="example_1",
    env=AwsEnviroment(
        profile=os.getenv("AWS_PROFILE"),
        account=os.getenv("AWS_ACCOUNT"),
        region=os.getenv("AWS_REGION")
    ),
    constructs={}
)

# S3 Bucket (can be created before deployment)
my_bucket = S3(
    bucket_name="my-example-testmb-bucket-22",
    policy={
        "Version": "2008-10-17",
        "Id": "PolicyForCloudFrontPrivateContent",
        "Statement": [{
            "Sid": "AllowCloudFrontServicePrincipal",
            "Effect": "Allow",
            "Principal": {"Service": "cloudfront.amazonaws.com"},
            "Action": "s3:GetObject",
            "Resource": "arn:aws:s3:::my-example-testmb-bucket-22/*"
        }]
    },
    env=app.env
)

# Transactional Deployment
with app.begin_deploy() as deploy_ctx:
    # Create and deploy IAM Roles first (other Lambda functions depend on them)
    hello_role = IamRole(
        role_name="hallo-welt-lambda-role",
        assume_role_policy={
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Principal": {"Service": "lambda.amazonaws.com"},
                "Action": "sts:AssumeRole"
            }]
        },
        managed_policies=["arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"],
        description="IAM Role für Hello Lambda",
        env=app.env
    )
    deploy_ctx.add_resource("01-hello-role", hello_role)

    lambda_role = IamRole(
        role_name="lambda-todo-role",
        assume_role_policy={
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Principal": {"Service": "lambda.amazonaws.com"},
                "Action": "sts:AssumeRole"
            }]
        },
        managed_policies=["arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"],
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
    deploy_ctx.add_resource("02-lambda-role", lambda_role)

    # Deploy DynamoDB table and S3 bucket
    todo_table = DynamoDB(
        table_name="todos",
        partition_key={'name': 'id', 'type': 'S'},
        billing_mode="PAY_PER_REQUEST",
        env=app.env
    )
    deploy_ctx.add_resource("03-todo-table", todo_table)

    deploy_ctx.add_resource("04-my-bucket", my_bucket)
    deploy_ctx.add_resource("05-website", S3Deploy(
        bucket_name=my_bucket.bucket_name,
        local_path="./web/",
        s3_path="",
        env=app.env
    ))

    # Now create Lambda functions (they have the real ARNs from deployed roles)
    hello_lambda = LambdaFunction(
        function_name="hallo-welt",
        handler="lambda_function.lambda_handler",
        runtime="python3.13",
        code_path="./functions/hallo_welt",
        role_arn=hello_role.get_arn(),  # Real ARN from deployed role
        env=app.env
    )
    deploy_ctx.add_resource("10-lambda-hello", hello_lambda)

    lambda_todo_create = LambdaFunction(
        function_name="todo-create",
        handler="lambda_function.lambda_handler",
        runtime="python3.13",
        code_path="./functions/todo_create",
        role_arn=lambda_role.get_arn(),  # Real ARN from deployed role
        environment_variables={"TABLE_NAME": "todos"},
        env=app.env
    )
    deploy_ctx.add_resource("11-lambda-todo-create", lambda_todo_create)

    lambda_todo_list = LambdaFunction(
        function_name="todo-list",
        handler="lambda_function.lambda_handler",
        runtime="python3.13",
        code_path="./functions/todo_list",
        role_arn=lambda_role.get_arn(),  # Real ARN from deployed role
        environment_variables={"TABLE_NAME": "todos"},
        env=app.env
    )
    deploy_ctx.add_resource("12-lambda-todo-list", lambda_todo_list)

    lambda_todo_update = LambdaFunction(
        function_name="todo-update",
        handler="lambda_function.lambda_handler",
        runtime="python3.13",
        code_path="./functions/todo_update",
        role_arn=lambda_role.get_arn(),  # Real ARN from deployed role
        environment_variables={"TABLE_NAME": "todos"},
        env=app.env
    )
    deploy_ctx.add_resource("13-lambda-todo-update", lambda_todo_update)

    lambda_todo_delete = LambdaFunction(
        function_name="todo-delete",
        handler="lambda_function.lambda_handler",
        runtime="python3.13",
        code_path="./functions/todo_delete",
        role_arn=lambda_role.get_arn(),  # Real ARN from deployed role
        environment_variables={"TABLE_NAME": "todos"},
        env=app.env
    )
    deploy_ctx.add_resource("14-lambda-todo-delete", lambda_todo_delete)

    # Create API Gateway and CloudFront
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
            "/api/todos/{id}/update": {
                "method": "PUT",
                "lambda_arn": f"arn:aws:lambda:{app.env.region}:{app.env.account}:function:todo-update",
                "lambda_name": "todo-update"
            },
            "/api/todos/{id}/delete": {
                "method": "DELETE",
                "lambda_arn": f"arn:aws:lambda:{app.env.region}:{app.env.account}:function:todo-delete",
                "lambda_name": "todo-delete"
            }
        },
        description="API Gateway für App",
        env=app.env
    )
    deploy_ctx.add_resource("20-api-gateway", api_gateway)

    cloudfront = CloudFront(
        bucket_name=my_bucket.bucket_name,
        api_gateway_endpoint=f"https://r5kaifpzh4.execute-api.{app.env.region}.amazonaws.com",
        env=app.env
    )
    deploy_ctx.add_resource("30-cloudfront", cloudfront)
