import os
from dotenv import load_dotenv
from src.core import deploy, diff, destroy
from src.model import AwsEnviroment, AwsApp
from src.resources.cloudfront import CloudFront
from src.resources.lambda_function import LambdaFunction
from src.resources.s3 import S3
from src.resources.s3_deploy import S3Deploy

load_dotenv()

app = AwsApp(name="example_lambda", env=AwsEnviroment(profile=os.getenv("AWS_PROFILE"),
                                                 account=os.getenv("AWS_ACCOUNT"),
                                                 region=os.getenv("AWS_REGION")), constructs={})

app.constructs["lambda"] =  LambdaFunction(
    function_name="hallo-welt",
    handler="lambda_function.lambda_handler",
    runtime="python3.13",
    code_path="./functions/hallo_welt",
    role_arn="arn:aws:iam::...:role/lambda-role",
    env=app.env
)

deploy(app)
