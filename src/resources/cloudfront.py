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
        env: AwsEnviroment,
        bucket_name: str = None,
        api_gateway_endpoint: str = None,
        distribution_name: str = None,
        _skip_validation: bool = False
    ):
        self.bucket_name = bucket_name
        self.api_gateway_endpoint = api_gateway_endpoint
        self.distribution_name = distribution_name
        self.env = env

        if not _skip_validation and not bucket_name and not api_gateway_endpoint:
            raise ValueError("Entweder bucket_name oder api_gateway_endpoint muss angegeben werden")

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
        except cloudfront_client.exceptions.NoSuchDistribution:
            return cls(env=env, _skip_validation=True)
        except Exception as e:
            print(f"Fehler beim Abrufen der Distribution {distribution_id}: {e}")
            raise

    def create(self) -> str:
        """Erstelle eine neue CloudFront Distribution"""
        session = boto3.session.Session(
            profile_name=self.env.profile,
            region_name=self.env.region
        )
        cloudfront_client = session.client('cloudfront')

        origins = []
        behaviors = []
        comment_parts = []

        if self.bucket_name:
            s3_client = session.client('s3')
            bucket_location = s3_client.get_bucket_location(Bucket=self.bucket_name)
            bucket_region = bucket_location['LocationConstraint'] or 'us-east-1'
            s3_domain = f"{self.bucket_name}.s3.{bucket_region}.amazonaws.com"
            s3_origin_id = f"s3-{uuid.uuid4().hex[:11]}"

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

            origins.append({
                'Id': s3_origin_id,
                'DomainName': s3_domain,
                'OriginPath': '',
                'CustomHeaders': {'Quantity': 0},
                'S3OriginConfig': {
                    'OriginAccessIdentity': '',
                    'OriginReadTimeout': 30
                },
                'ConnectionAttempts': 3,
                'ConnectionTimeout': 10,
                'OriginShield': {'Enabled': False},
                'OriginAccessControlId': oac_id
            })
            comment_parts.append(f"S3: {self.bucket_name}")

        if self.api_gateway_endpoint:
            api_domain = self.api_gateway_endpoint.replace('https://', '')
            api_origin_id = f"api-{uuid.uuid4().hex[:11]}"

            origins.append({
                'Id': api_origin_id,
                'DomainName': api_domain,
                'OriginPath': '',
                'CustomHeaders': {'Quantity': 0},
                'CustomOriginConfig': {
                    'HTTPPort': 80,
                    'HTTPSPort': 443,
                    'OriginProtocolPolicy': 'https-only',
                    'OriginSslProtocols': {
                        'Quantity': 1,
                        'Items': ['TLSv1.2']
                    },
                    'OriginReadTimeout': 30,
                    'OriginKeepaliveTimeout': 5
                },
                'ConnectionAttempts': 3,
                'ConnectionTimeout': 10,
                'OriginShield': {'Enabled': False}
            })
            comment_parts.append(f"API: {api_domain}")

            behaviors.append({
                'PathPattern': '/api/*',
                'TargetOriginId': api_origin_id,
                'ViewerProtocolPolicy': 'https-only',
                'AllowedMethods': {
                    'Quantity': 7,
                    'Items': ['GET', 'HEAD', 'OPTIONS', 'PUT', 'POST', 'PATCH', 'DELETE'],
                    'CachedMethods': {
                        'Quantity': 2,
                        'Items': ['HEAD', 'GET']
                    }
                },
                'Compress': True,
                'CachePolicyId': '4135ea2d-6df8-44a3-9df3-4b5a84be39ad',
                'OriginRequestPolicyId': 'b689b0a8-53d0-40ab-baf2-68738e2966ac',
                'TrustedSigners': {'Enabled': False, 'Quantity': 0},
                'TrustedKeyGroups': {'Enabled': False, 'Quantity': 0},
                'FieldLevelEncryptionId': ''
            })

        default_origin_id = origins[0]['Id'] if origins else None

        distribution_config = {
            'CallerReference': str(uuid.uuid4()),
            'Comment': f"CloudFront: {', '.join(comment_parts)}" if comment_parts else 'CloudFront Distribution',
            'Enabled': True,
            'Origins': {
                'Quantity': len(origins),
                'Items': origins
            },
            'OriginGroups': {'Quantity': 0},
            'DefaultCacheBehavior': {
                'TargetOriginId': default_origin_id,
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
                'TrustedSigners': {'Enabled': False, 'Quantity': 0},
                'TrustedKeyGroups': {'Enabled': False, 'Quantity': 0},
                'SmoothStreaming': False,
                'FieldLevelEncryptionId': ''
            },
            'CacheBehaviors': {
                'Quantity': len(behaviors),
                'Items': behaviors
            } if behaviors else {'Quantity': 0},
            'CustomErrorResponses': {'Quantity': 0},
            'DefaultRootObject': '',
            'Aliases': {'Quantity': 0},
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

        response = cloudfront_client.get_distribution_config(Id=distribution_id)
        distribution_config = response['DistributionConfig']
        etag = response['ETag']

        current_origins = {origin['DomainName']: origin for origin in distribution_config['Origins']['Items']}
        needs_update = False

        new_origins = []
        new_behaviors = []

        if new_value.bucket_name:
            s3_client = session.client('s3')
            bucket_location = s3_client.get_bucket_location(Bucket=new_value.bucket_name)
            bucket_region = bucket_location['LocationConstraint'] or 'us-east-1'
            s3_domain = f"{new_value.bucket_name}.s3.{bucket_region}.amazonaws.com"

            if s3_domain not in current_origins:
                print(f"Füge S3 Origin hinzu: {s3_domain}")
                needs_update = True

                oac_response = cloudfront_client.create_origin_access_control(
                    OriginAccessControlConfig={
                        'Name': f'OAC-{new_value.bucket_name}-{uuid.uuid4().hex[:8]}',
                        'Description': f'Origin Access Control for {new_value.bucket_name}',
                        'SigningProtocol': 'sigv4',
                        'SigningBehavior': 'always',
                        'OriginAccessControlOriginType': 's3'
                    }
                )
                oac_id = oac_response['OriginAccessControl']['Id']

                s3_origin_id = f"s3-{uuid.uuid4().hex[:11]}"
                new_origins.append({
                    'Id': s3_origin_id,
                    'DomainName': s3_domain,
                    'OriginPath': '',
                    'CustomHeaders': {'Quantity': 0},
                    'S3OriginConfig': {
                        'OriginAccessIdentity': '',
                        'OriginReadTimeout': 30
                    },
                    'ConnectionAttempts': 3,
                    'ConnectionTimeout': 10,
                    'OriginShield': {'Enabled': False},
                    'OriginAccessControlId': oac_id
                })
            else:
                for origin in distribution_config['Origins']['Items']:
                    if s3_domain in origin['DomainName']:
                        new_origins.append(origin)
                        break

        if new_value.api_gateway_endpoint:
            api_domain = new_value.api_gateway_endpoint.replace('https://', '')

            if api_domain not in current_origins:
                print(f"Füge API Gateway Origin hinzu: {api_domain}")
                needs_update = True

                api_origin_id = f"api-{uuid.uuid4().hex[:11]}"
                new_origins.append({
                    'Id': api_origin_id,
                    'DomainName': api_domain,
                    'OriginPath': '',
                    'CustomHeaders': {'Quantity': 0},
                    'CustomOriginConfig': {
                        'HTTPPort': 80,
                        'HTTPSPort': 443,
                        'OriginProtocolPolicy': 'https-only',
                        'OriginSslProtocols': {
                            'Quantity': 1,
                            'Items': ['TLSv1.2']
                        },
                        'OriginReadTimeout': 30,
                        'OriginKeepaliveTimeout': 5
                    },
                    'ConnectionAttempts': 3,
                    'ConnectionTimeout': 10,
                    'OriginShield': {'Enabled': False}
                })

                new_behaviors.append({
                    'PathPattern': '/api/*',
                    'TargetOriginId': api_origin_id,
                    'ViewerProtocolPolicy': 'https-only',
                    'AllowedMethods': {
                        'Quantity': 7,
                        'Items': ['GET', 'HEAD', 'OPTIONS', 'PUT', 'POST', 'PATCH', 'DELETE'],
                        'CachedMethods': {
                            'Quantity': 2,
                            'Items': ['HEAD', 'GET']
                        }
                    },
                    'Compress': True,
                    'CachePolicyId': '4135ea2d-6df8-44a3-9df3-4b5a84be39ad',
                    'OriginRequestPolicyId': 'b689b0a8-53d0-40ab-baf2-68738e2966ac',
                    'TrustedSigners': {'Enabled': False, 'Quantity': 0},
                    'TrustedKeyGroups': {'Enabled': False, 'Quantity': 0},
                    'FieldLevelEncryptionId': ''
                })
            else:
                for origin in distribution_config['Origins']['Items']:
                    if api_domain in origin['DomainName']:
                        new_origins.append(origin)
                        break
                for behavior in distribution_config.get('CacheBehaviors', {}).get('Items', []):
                    if behavior['PathPattern'] == '/api/*':
                        new_behaviors.append(behavior)

        if not needs_update:
            print(f"CloudFront Distribution {distribution_id} ist bereits aktuell")
            return deployed_tech_id

        distribution_config['Origins'] = {
            'Quantity': len(new_origins),
            'Items': new_origins
        }

        if distribution_config['DefaultCacheBehavior']['TargetOriginId'] not in [o['Id'] for o in new_origins]:
            distribution_config['DefaultCacheBehavior']['TargetOriginId'] = new_origins[0]['Id']

        distribution_config['CacheBehaviors'] = {
            'Quantity': len(new_behaviors),
            'Items': new_behaviors
        } if new_behaviors else {'Quantity': 0}

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

        try:
            response = cloudfront_client.get_distribution_config(Id=distribution_id)
            distribution_config = response['DistributionConfig']
            etag = response['ETag']
        except cloudfront_client.exceptions.NoSuchDistribution:
            print(f"CloudFront Distribution {distribution_id} existiert nicht")
            return

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
