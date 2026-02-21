import boto3

from src.model import AwsEnviroment, Resources
from src.model.registry import register_resource


@register_resource("cloudfront")
class CloudFront(Resources):
    """CloudFront Resource für AWS CDN Distribution Management"""

    def __init__(
        self,
        name: str = None,
        env: AwsEnviroment = None
    ):
        self.name = name
        self.env = env

    @classmethod
    def get(cls, tech_id: str, env: AwsEnviroment) -> 'CloudFront':
        """Hole eine spezifische CloudFront Distribution"""
        pass

    def create(self) -> str:
        """Erstelle eine neue CloudFront Distribution mit OAC"""
        pass

    def update(self, deployed_tech_id: str, new_value: 'CloudFront') -> str:
        """Update eine CloudFront Distribution"""
        pass

    def delete(self, tech_id: str):
        """Lösche eine CloudFront Distribution"""
        pass
