from dataclasses import dataclass

from abc import ABC, abstractmethod
from typing import TypeVar, Type
import boto3
from botocore.session import Session

T = TypeVar('T', bound='Resources')


@dataclass
class AwsEnviroment:
    profile: str = "bins-example-dev"
    account: str = "967243681795"
    region: str = "eu-central-1"


class Resources(ABC):  # Interface


    @classmethod
    @abstractmethod
    def list(cls: Type[T], env: AwsEnviroment) -> list[T]:
        pass

    @classmethod
    @abstractmethod
    def get(cls: Type[T], tech_id: str, env: AwsEnviroment) -> T:
        pass

    @abstractmethod
    def create(self):
        pass

    @abstractmethod
    def update(self):
        pass

    @abstractmethod
    def delete(self):
        pass

@dataclass
class AwsApp:
    name: str
    env: AwsEnviroment
    app_to_tech_id: dict[str, str]
    constructs: list[str]


class S3(Resources):
    pass

app = AwsApp(name="example_1", env=AwsEnviroment(), app_to_tech_id={}, constructs=[])

S3(app)



