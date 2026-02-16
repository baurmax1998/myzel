from src.core import deploy, diff, destroy
from src.model import AwsEnviroment, AwsApp
from src.resources.s3 import S3


app = AwsApp(name="example_1", env=AwsEnviroment(), constructs={})

# S3 Bucket erstellen
app.constructs["my-example-bucket-testmb-22"] = S3(
    bucket_name="my-example-bucket-testmb-23",
    env=app.env
)

deploy(app)




