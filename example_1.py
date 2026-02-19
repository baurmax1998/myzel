import os
from dotenv import load_dotenv
from src.core import deploy, diff, destroy
from src.model import AwsEnviroment, AwsApp
from src.resources.s3 import S3
from src.resources.s3_deploy import S3Deploy

load_dotenv()

app = AwsApp(name="example_1", env=AwsEnviroment(profile=os.getenv("AWS_PROFILE"),
                                                 account=os.getenv("AWS_ACCOUNT"),
                                                 region=os.getenv("AWS_REGION")), constructs={})

# S3 Bucket erstellen
my_bucket = S3(bucket_name="my-example-bucket-testmb-23", env=app.env)
app.constructs["my-example-bucket-testmb-22"] = my_bucket

app.constructs["website"] = S3Deploy(
    bucket_name=my_bucket.bucket_name,
    local_path="./web",  # Dein web Ordner
    s3_path="website/v1",
    env=app.env
)

deploy(app)
