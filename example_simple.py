import os
from dotenv import load_dotenv
from src.model import AwsEnviroment, MyzelApp
from src.resources.iam_role import IamRole
from src.resources.lambda_function import LambdaFunction

load_dotenv()

app = MyzelApp(
    name="example_simple",
    env=AwsEnviroment(
        profile=os.getenv("AWS_PROFILE"),
        account=os.getenv("AWS_ACCOUNT"),
        region=os.getenv("AWS_REGION")
    ),
    constructs={}
)
# Transactional deployment
with app.begin_deploy() as deploy_ctx:
    # Create and deploy IAM role first
    hello_role = IamRole(
        role_name="aa-simple-hallo-welt-lambda-role-rename",
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
    deploy_ctx.add_resource("hello-role", hello_role)

    # Create Lambda function after role deployment (now hello_role has the real ARN)
    hello_lambda = LambdaFunction(
        function_name="aa-hallo-welt",
        handler="lambda_function.lambda_handler",
        runtime="python3.13",
        code_path="./functions/hallo_welt",
        role_arn=hello_role.get_arn(),  # Now this gets the real ARN from AWS
        env=app.env
    )
    deploy_ctx.add_resource("hello-lambda", hello_lambda)
