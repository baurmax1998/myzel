import boto3

from src.model import AwsEnviroment, Resources
from src.model.registry import register_resource


@register_resource("cloudfront")
class CloudFront(Resources):
    """CloudFront Resource für AWS CDN Distribution Management"""

    def __init__(
        self,
        origin_id: str,
        enabled: bool = True,
        default_root_object: str = "index.html",
        domain_name: str = None,
        env: AwsEnviroment = None
    ):
        self.origin_id = origin_id
        self.domain_name = domain_name
        self.enabled = enabled
        self.default_root_object = default_root_object
        self.env = env

    @classmethod
    def list(cls, env: AwsEnviroment) -> list['CloudFront']:
        """Liste alle CloudFront Distributionen auf"""
        session = boto3.session.Session(
            profile_name=env.profile,
            region_name=env.region
        )
        cloudfront_client = session.client('cloudfront')

        try:
            response = cloudfront_client.list_distributions()
            distributions = []

            for distribution in response.get('DistributionList', {}).get('Items', []):
                domain_name = distribution['DomainName']
                origin_id = distribution['Origins']['Items'][0]['Id']
                enabled = distribution['Enabled']
                default_root = distribution.get('DefaultRootObject', 'index.html')

                distributions.append(
                    cls(
                        domain_name=domain_name,
                        origin_id=origin_id,
                        enabled=enabled,
                        default_root_object=default_root,
                        env=env
                    )
                )
            return distributions
        except Exception as e:
            print(f"Fehler beim Auflisten der Distributionen: {e}")
            return []

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
            dist = response['Distribution']['DistributionConfig']
            domain_name = response['Distribution']['DomainName']
            origin_id = dist['Origins']['Items'][0]['Id']
            enabled = dist['Enabled']
            default_root = dist.get('DefaultRootObject', 'index.html')

            return cls(
                domain_name=domain_name,
                origin_id=origin_id,
                enabled=enabled,
                default_root_object=default_root,
                env=env
            )
        except Exception as e:
            print(f"Fehler beim Abrufen der Distribution {distribution_id}: {e}")
            raise

    def create(self, s3_bucket_domain: str = None) -> str:
        """Erstelle eine neue CloudFront Distribution"""
        if not s3_bucket_domain:
            raise ValueError("s3_bucket_domain erforderlich für CloudFront Distribution")

        session = boto3.session.Session(
            profile_name=self.env.profile,
            region_name=self.env.region
        )
        cloudfront_client = session.client('cloudfront')

        try:
            distribution_config = {
                'CallerReference': self.origin_id,
                'Origins': {
                    'Quantity': 1,
                    'Items': [
                        {
                            'Id': self.origin_id,
                            'DomainName': s3_bucket_domain,
                            'S3OriginConfig': {
                                'OriginAccessIdentity': ''
                            }
                        }
                    ]
                },
                'DefaultRootObject': self.default_root_object,
                'Comment': f'Distribution for {self.origin_id}',
                'DefaultCacheBehavior': {
                    'TargetOriginId': self.origin_id,
                    'ViewerProtocolPolicy': 'redirect-to-https',
                    'TrustedSigners': {
                        'Enabled': False,
                        'Quantity': 0
                    },
                    'ForwardedValues': {
                        'QueryString': False,
                        'Cookies': {'Forward': 'none'},
                        'Headers': {
                            'Quantity': 0
                        }
                    },
                    'MinTTL': 0
                },
                'CacheBehaviors': {
                    'Quantity': 0
                },
                'Enabled': self.enabled
            }

            response = cloudfront_client.create_distribution(DistributionConfig=distribution_config)
            distribution_id = response['Distribution']['Id']
            domain_name = response['Distribution']['DomainName']

            print(f"CloudFront Distribution '{distribution_id}' erfolgreich erstellt")
            print(f"Domain: {domain_name}")

            tech_id = self._create_tech_id(distribution_id)
            return tech_id

        except Exception as e:
            print(f"Fehler beim Erstellen der Distribution: {e}")
            raise

    def update(self, deployed_tech_id: str, new_value: 'CloudFront', s3_bucket_domain: str = None) -> str:
        """Update eine CloudFront Distribution"""
        deployed_id = self._extract_distribution_id(deployed_tech_id)
        session = boto3.session.Session(
            profile_name=new_value.env.profile,
            region_name=new_value.env.region
        )
        cloudfront_client = session.client('cloudfront')

        try:
            # Hole aktuelle Distribution
            response = cloudfront_client.get_distribution(Id=deployed_id)
            distribution_config = response['Distribution']['DistributionConfig']
            etag = response['ETag']

            # Update Felder
            if new_value.enabled != distribution_config['Enabled']:
                distribution_config['Enabled'] = new_value.enabled
                print(f"Update: Enabled = {new_value.enabled}")

            if new_value.default_root_object != distribution_config.get('DefaultRootObject', ''):
                distribution_config['DefaultRootObject'] = new_value.default_root_object
                print(f"Update: DefaultRootObject = {new_value.default_root_object}")

            if s3_bucket_domain and s3_bucket_domain != distribution_config['Origins']['Items'][0]['DomainName']:
                distribution_config['Origins']['Items'][0]['DomainName'] = s3_bucket_domain
                print(f"Update: S3 Origin = {s3_bucket_domain}")

            # Aktualisiere Distribution
            response = cloudfront_client.update_distribution(
                Id=deployed_id,
                DistributionConfig=distribution_config,
                IfMatch=etag
            )

            distribution_id = response['Distribution']['Id']
            print(f"CloudFront Distribution '{distribution_id}' erfolgreich aktualisiert")

            tech_id = self._create_tech_id(distribution_id)
            return tech_id

        except Exception as e:
            print(f"Fehler beim Update der Distribution: {e}")
            raise

    def delete(self, tech_id: str):
        """Lösche eine CloudFront Distribution"""
        distribution_id = self._extract_distribution_id(tech_id)
        session = boto3.session.Session(
            profile_name=self.env.profile,
            region_name=self.env.region
        )
        cloudfront_client = session.client('cloudfront')

        try:
            # Hole Distribution und ETag
            response = cloudfront_client.get_distribution(Id=distribution_id)
            etag = response['ETag']

            # Deaktiviere zuerst (CloudFront erfordert das vor Löschung)
            distribution_config = response['Distribution']['DistributionConfig']
            distribution_config['Enabled'] = False

            cloudfront_client.update_distribution(
                Id=distribution_id,
                DistributionConfig=distribution_config,
                IfMatch=etag
            )

            # Hole neuen ETag nach Update
            response = cloudfront_client.get_distribution(Id=distribution_id)
            etag = response['ETag']

            # Lösche Distribution
            cloudfront_client.delete_distribution(Id=distribution_id, IfMatch=etag)

            print(f"CloudFront Distribution '{distribution_id}' erfolgreich gelöscht")

        except Exception as e:
            print(f"Fehler beim Löschen der Distribution: {e}")
            raise

    @staticmethod
    def _create_tech_id(distribution_id: str) -> str:
        """Erstelle tech_id aus Distribution ID"""
        return f"arn:aws:cloudfront::{distribution_id}"

    @staticmethod
    def _extract_distribution_id(tech_id: str) -> str:
        """Extrahiere Distribution ID aus tech_id"""
        # Format: arn:aws:cloudfront::distribution-id
        return tech_id.split('::')[-1]

    def __repr__(self) -> str:
        return f"CloudFront(origin='{self.origin_id}', domain='{self.domain_name}', enabled={self.enabled})"
