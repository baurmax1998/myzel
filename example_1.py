import os
from dotenv import load_dotenv
from src.core import deploy, diff, destroy
from src.model import AwsEnviroment, AwsApp
from src.resources.cloudfront import CloudFront
from src.resources.iam_role import IamRole
from src.resources.lambda_function import LambdaFunction
from src.resources.s3 import S3
from src.resources.s3_deploy import S3Deploy

load_dotenv()

app = AwsApp(name="example_1", env=AwsEnviroment(profile=os.getenv("AWS_PROFILE"),
                                                 account=os.getenv("AWS_ACCOUNT"),
                                                 region=os.getenv("AWS_REGION")), constructs={})

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
app.constructs["my-bucket"] = my_bucket

app.constructs["website"] = S3Deploy(
    bucket_name=my_bucket.bucket_name,
    local_path="./web/",
    s3_path="",
    env=app.env
)

app.constructs["cloudfront"] = CloudFront(
    bucket_name=my_bucket.bucket_name,
    env=app.env
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

app.constructs["lambda"] = LambdaFunction(
    function_name="hallo-welt",
    handler="lambda_function.lambda_handler",
    runtime="python3.13",
    code_path="./functions/hallo_welt",
    role_arn=lambda_role.get_arn(),
    env=app.env
)

deploy(app)
