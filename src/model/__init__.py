from dataclasses import dataclass


@dataclass
class AwsEnviroment:
    profile: str = "bins-example-dev"
    account: str = "967243681795"
    region: str = "eu-central-1"


@dataclass
class AwsApp:
    name: str
    env: AwsEnviroment
    constructs: list