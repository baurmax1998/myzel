from dataclasses import dataclass

from abc import ABC, abstractmethod
from typing import TypeVar, Type
import boto3
from botocore.session import Session
from src.core import deploy




app = AwsApp(name="example_1", env=AwsEnviroment(), app_to_tech_id={}, constructs=[])


# S3 Bucket erstellen
s3_bucket = S3(
    resource_id="my-example-bucket-testmb-22",
    bucket_name="my-example-bucket-testmb-22",
    env=app.env
)
app.constructs.append(s3_bucket)

deploy(app)




