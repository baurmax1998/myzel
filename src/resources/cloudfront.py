import time
import uuid

import boto3

from src.model import AwsEnviroment, Resources
from src.model.registry import register_resource


@register_resource("cloudfront")
class CloudFront(Resources):
    """CloudFront Resource für AWS CDN Distribution Management"""

    def __init__(
        self,
        bucket_name: str,
        env: AwsEnviroment
    ):
        self.bucket_name = bucket_name
        self.env = env

    @classmethod
    def get(cls, tech_id: str, env: AwsEnviroment) -> 'CloudFront':
        """Hole eine spezifische CloudFront Distribution"""
        distribution_id = cls._extract_distribution_id(tech_id)
        session = boto3.session.Session(
            profile_name=env.profile,
            region_name=env.region
        )
        cloudfront_client = session.client('cloudfront')

        try:
            response = cloudfront_client.get_distribution(Id=distribution_id)
            distribution = response['Distribution']

            origin_domain = distribution['DistributionConfig']['Origins']['Items'][0]['DomainName']
            bucket_name = origin_domain.split('.s3.')[0]

            return cls(bucket_name=bucket_name, env=env)
        except Exception as e:
            print(f"Fehler beim Abrufen der Distribution {distribution_id}: {e}")
            raise

    def create(self) -> str:
        """Erstelle eine neue CloudFront Distribution mit OAC"""
        session = boto3.session.Session(
            profile_name=self.env.profile,
            region_name=self.env.region
        )
        cloudfront_client = session.client('cloudfront')
        s3_client = session.client('s3')

        bucket_location = s3_client.get_bucket_location(Bucket=self.bucket_name)
        bucket_region = bucket_location['LocationConstraint'] or 'us-east-1'

        s3_domain = f"{self.bucket_name}.s3.{bucket_region}.amazonaws.com"
        origin_id = f"{s3_domain}-{uuid.uuid4().hex[:11]}"

        oac_response = cloudfront_client.create_origin_access_control(
            OriginAccessControlConfig={
                'Name': f'OAC-{self.bucket_name}-{uuid.uuid4().hex[:8]}',
                'Description': f'Origin Access Control for {self.bucket_name}',
                'SigningProtocol': 'sigv4',
                'SigningBehavior': 'always',
                'OriginAccessControlOriginType': 's3'
            }
        )
        oac_id = oac_response['OriginAccessControl']['Id']

        distribution_config = {
            'CallerReference': str(uuid.uuid4()),
            'Comment': f'CloudFront distribution for {self.bucket_name}',
            'Enabled': True,
            'Origins': {
                'Quantity': 1,
                'Items': [
                    {
                        'Id': origin_id,
                        'DomainName': s3_domain,
                        'OriginPath': '',
                        'CustomHeaders': {
                            'Quantity': 0
                        },
                        'S3OriginConfig': {
                            'OriginAccessIdentity': '',
                            'OriginReadTimeout': 30
                        },
                        'ConnectionAttempts': 3,
                        'ConnectionTimeout': 10,
                        'OriginShield': {
                            'Enabled': False
                        },
                        'OriginAccessControlId': oac_id
                    }
                ]
            },
            'OriginGroups': {
                'Quantity': 0
            },
            'DefaultCacheBehavior': {
                'TargetOriginId': origin_id,
                'ViewerProtocolPolicy': 'redirect-to-https',
                'AllowedMethods': {
                    'Quantity': 2,
                    'Items': ['HEAD', 'GET'],
                    'CachedMethods': {
                        'Quantity': 2,
                        'Items': ['HEAD', 'GET']
                    }
                },
                'Compress': True,
                'CachePolicyId': '658327ea-f89d-4fab-a63d-7e88639e58f6',
                'OriginRequestPolicyId': '88a5eaf4-2fd4-4709-b370-b4c650ea3fcf',
                'TrustedSigners': {
                    'Enabled': False,
                    'Quantity': 0
                },
                'TrustedKeyGroups': {
                    'Enabled': False,
                    'Quantity': 0
                },
                'SmoothStreaming': False,
                'FieldLevelEncryptionId': ''
            },
            'CacheBehaviors': {
                'Quantity': 0
            },
            'CustomErrorResponses': {
                'Quantity': 0
            },
            'DefaultRootObject': '',
            'Aliases': {
                'Quantity': 0
            },
            'PriceClass': 'PriceClass_All',
            'ViewerCertificate': {
                'CloudFrontDefaultCertificate': True,
                'MinimumProtocolVersion': 'TLSv1.2_2021',
                'CertificateSource': 'cloudfront'
            },
            'HttpVersion': 'http2and3',
            'IsIPV6Enabled': True
        }

        response = cloudfront_client.create_distribution(
            DistributionConfig=distribution_config
        )

        distribution = response['Distribution']
        arn = distribution['ARN']

        print(f"CloudFront Distribution erstellt: {distribution['Id']}")
        print(f"Domain Name: {distribution['DomainName']}")
        print(f"Status: {distribution['Status']}")

        return arn

    def update(self, deployed_tech_id: str, new_value: 'CloudFront') -> str:
        """Update eine CloudFront Distribution"""
        distribution_id = self._extract_distribution_id(deployed_tech_id)

        session = boto3.session.Session(
            profile_name=new_value.env.profile,
            region_name=new_value.env.region
        )
        cloudfront_client = session.client('cloudfront')
        s3_client = session.client('s3')

        response = cloudfront_client.get_distribution_config(Id=distribution_id)
        distribution_config = response['DistributionConfig']
        etag = response['ETag']

        current_origin_domain = distribution_config['Origins']['Items'][0]['DomainName']
        current_bucket = current_origin_domain.split('.s3.')[0]

        if current_bucket == new_value.bucket_name:
            print(f"CloudFront Distribution {distribution_id} ist bereits aktuell")
            return deployed_tech_id

        bucket_location = s3_client.get_bucket_location(Bucket=new_value.bucket_name)
        bucket_region = bucket_location['LocationConstraint'] or 'us-east-1'
        new_s3_domain = f"{new_value.bucket_name}.s3.{bucket_region}.amazonaws.com"

        distribution_config['Origins']['Items'][0]['DomainName'] = new_s3_domain
        print(f"Aktualisiere Origin Domain zu: {new_s3_domain}")

        update_response = cloudfront_client.update_distribution(
            DistributionConfig=distribution_config,
            Id=distribution_id,
            IfMatch=etag
        )

        updated_distribution = update_response['Distribution']
        print(f"CloudFront Distribution {distribution_id} erfolgreich aktualisiert")
        print(f"Status: {updated_distribution['Status']}")

        return updated_distribution['ARN']

    def delete(self, tech_id: str):
        """Lösche eine CloudFront Distribution"""
        distribution_id = self._extract_distribution_id(tech_id)

        session = boto3.session.Session(
            profile_name=self.env.profile,
            region_name=self.env.region
        )
        cloudfront_client = session.client('cloudfront')

        response = cloudfront_client.get_distribution_config(Id=distribution_id)
        distribution_config = response['DistributionConfig']
        etag = response['ETag']

        if distribution_config['Enabled']:
            print(f"Distribution {distribution_id} ist enabled. Deaktiviere sie zuerst...")

            distribution_config['Enabled'] = False
            cloudfront_client.update_distribution(
                DistributionConfig=distribution_config,
                Id=distribution_id,
                IfMatch=etag
            )

            print("Distribution deaktiviert. Warte auf Deployment...")

            while True:
                response = cloudfront_client.get_distribution(Id=distribution_id)
                status = response['Distribution']['Status']
                print(f"Status: {status}")

                if status == 'Deployed':
                    print("Distribution ist deployed und deaktiviert")
                    etag = response['ETag']
                    break

                time.sleep(30)
        else:
            print(f"Distribution {distribution_id} ist bereits deaktiviert")

        print(f"Lösche Distribution {distribution_id}...")
        cloudfront_client.delete_distribution(
            Id=distribution_id,
            IfMatch=etag
        )

        print(f"CloudFront Distribution {distribution_id} erfolgreich gelöscht")

    @staticmethod
    def _extract_distribution_id(arn: str) -> str:
        """Extrahiere Distribution ID aus ARN"""
        return arn.split('/')[-1]

    def __repr__(self) -> str:
        return f"CloudFront(bucket='{self.bucket_name}')"
