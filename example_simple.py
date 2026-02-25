import os
from dotenv import load_dotenv
from src.core import deploy
from src.model import AwsEnviroment, MyzelApp
from src.resources.iam_role import IamRole
from src.resources.lambda_function import LambdaFunction

load_dotenv()

app = MyzelApp(name="example_simple", env=AwsEnviroment(profile=os.getenv("AWS_PROFILE"),
                                                        account=os.getenv("AWS_ACCOUNT"),
                                                        region=os.getenv("AWS_REGION")), constructs={})

hello_role = IamRole(role_name="simple-hallo-welt-lambda-role",
                     assume_role_policy={"Version": "2012-10-17", "Statement": [
                         {"Effect": "Allow", "Principal": {"Service": "lambda.amazonaws.com"},
                          "Action": "sts:AssumeRole"}]},
                     managed_policies=["arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"],
                     description="IAM Role für Hello Lambda", env=app.env)

app.constructs["hello-role"] = hello_role

app.constructs["10-lambda-hello"] = LambdaFunction(
    function_name="hallo-welt",
    handler="lambda_function.lambda_handler",
    runtime="python3.13",
    code_path="./functions/hallo_welt",
    role_arn=hello_role.get_arn(),
    env=app.env
)

deploy(app)
