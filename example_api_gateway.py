import os
from dotenv import load_dotenv
from src.core import deploy
from src.model import AwsEnviroment, AwsApp
from src.resources.iam_role import IamRole
from src.resources.lambda_function import LambdaFunction
from src.resources.api_gateway import ApiGateway

load_dotenv()

app = AwsApp(
    name="example_api_gateway",
    env=AwsEnviroment(
        profile=os.getenv("AWS_PROFILE"),
        account=os.getenv("AWS_ACCOUNT"),
        region=os.getenv("AWS_REGION")
    ),
    constructs={}
)

lambda_role = IamRole(
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
    description="IAM Role für Hallo Welt Lambda Function",
    env=app.env
)
app.constructs["lambda-role"] = lambda_role

hallo_lambda = LambdaFunction(
    function_name="hallo-welt",
    handler="lambda_function.lambda_handler",
    runtime="python3.13",
    code_path="./functions/hallo_welt",
    role_arn=lambda_role.get_arn(),
    env=app.env
)
app.constructs["lambda"] = hallo_lambda

api_gateway = ApiGateway(
    api_name="hallo-welt-api",
    routes={
        "/hello": {
            "method": "GET",
            "lambda_arn": f"arn:aws:lambda:{app.env.region}:{app.env.account}:function:hallo-welt",
            "lambda_name": "hallo-welt"
        }
    },
    description="API Gateway für Hallo Welt Lambda",
    env=app.env
)
app.constructs["api-gateway"] = api_gateway

deploy(app)
