from dataclasses import dataclass

from abc import ABC, abstractmethod


@dataclass
class AwsEnviroment:
    profile: str = "bins-example-dev"
    account: str = "967243681795"
    region: str = "eu-central-1"


class Resources(ABC):  # Interface

    @abstractmethod
    def list(self):
        pass

    @abstractmethod
    def get(self):
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
    constructs: list[str]
    app_to_tech_id: dict[str, str]


class S3(Resources):



app = AwsApp(name="example_1", env=AwsEnviroment(), app_to_tech_id={})

S3(a)
