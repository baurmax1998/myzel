from src.core import deploy
from src.model import AwsEnviroment, AwsApp
from src.resources.s3 import S3




app = AwsApp(name="example_1", env=AwsEnviroment(), constructs=[])


# S3 Bucket erstellen
s3_bucket = S3(
    resource_id="my-example-bucket-testmb-22",
    bucket_name="my-example-bucket-testmb-22",
    env=app.env
)
app.constructs.append(s3_bucket)

deploy(app)




