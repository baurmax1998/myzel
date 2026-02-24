import os
from dotenv import load_dotenv
from src.model import AwsEnviroment


def load_env() -> AwsEnviroment:
    """Lädt Environment aus .env Datei"""
    load_dotenv()

    return AwsEnviroment(
        profile=os.getenv("AWS_PROFILE", "default"),
        region=os.getenv("AWS_REGION", "eu-central-1"),
        account=os.getenv("AWS_ACCOUNT", "123456789012")
    )
