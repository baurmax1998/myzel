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


class S3(Resources):
    """S3 Resource für AWS Bucket Management"""

    def __init__(
        self,
        bucket_name: str,
        env: AwsEnviroment,
        acl: str = "private",
        versioning: bool = False,
        encryption: bool = False,
        public_access_block: bool = True
    ):
        self.bucket_name = bucket_name
        self.acl = acl
        self.versioning = versioning
        self.encryption = encryption
        self.public_access_block = public_access_block
        self.env = env
        self.s3_client = boto3.session.Session(
            profile_name=env.profile,
            region_name=env.region
        ).client('s3')

    @classmethod
    def list(cls, env: AwsEnviroment) -> list['S3']:
        """Liste alle S3 Buckets auf"""
        session = boto3.session.Session(
            profile_name=env.profile,
            region_name=env.region
        )
        s3_client = session.client('s3')

        try:
            response = s3_client.list_buckets()
            buckets = []
            for bucket in response.get('Buckets', []):
                buckets.append(cls(bucket_name=bucket['Name'], env=env))
            return buckets
        except Exception as e:
            print(f"Fehler beim Auflisten der Buckets: {e}")
            return []

    @classmethod
    def get(cls, tech_id: str, env: AwsEnviroment) -> 'S3':
        """Hole einen spezifischen S3 Bucket anhand des Namens"""
        session = boto3.session.Session(
            profile_name=env.profile,
            region_name=env.region
        )
        s3_client = session.client('s3')

        try:
            # Prüfe ob Bucket existiert
            s3_client.head_bucket(Bucket=tech_id)

            # Hole Bucket Konfiguration
            versioning = s3_client.get_bucket_versioning(Bucket=tech_id)
            encryption = s3_client.get_bucket_encryption(Bucket=tech_id) if tech_id else None
            acl = s3_client.get_bucket_acl(Bucket=tech_id)

            return cls(
                bucket_name=tech_id,
                env=env,
                acl=acl.get('Owner', {}).get('ID', 'private'),
                versioning=versioning.get('Status') == 'Enabled',
                encryption=encryption is not None
            )
        except Exception as e:
            print(f"Fehler beim Abrufen des Buckets {tech_id}: {e}")
            raise

    def create(self):
        """Erstelle einen neuen S3 Bucket"""
        try:
            kwargs = {
                'Bucket': self.bucket_name,
                'ACL': self.acl
            }

            if self.env.region != 'us-east-1':
                kwargs['CreateBucketConfiguration'] = {
                    'LocationConstraint': self.env.region
                }

            self.s3_client.create_bucket(**kwargs)

            # Versioning aktivieren wenn konfiguriert
            if self.versioning:
                self.s3_client.put_bucket_versioning(
                    Bucket=self.bucket_name,
                    VersioningConfiguration={'Status': 'Enabled'}
                )

            # Server-side encryption aktivieren wenn konfiguriert
            if self.encryption:
                self.s3_client.put_bucket_encryption(
                    Bucket=self.bucket_name,
                    ServerSideEncryptionConfiguration={
                        'Rules': [{
                            'ApplyServerSideEncryptionByDefault': {
                                'SSEAlgorithm': 'AES256'
                            }
                        }]
                    }
                )

            # Public Access Block wenn konfiguriert
            if self.public_access_block:
                self.s3_client.put_public_access_block(
                    Bucket=self.bucket_name,
                    PublicAccessBlockConfiguration={
                        'BlockPublicAcls': True,
                        'IgnorePublicAcls': True,
                        'BlockPublicPolicy': True,
                        'RestrictPublicBuckets': True
                    }
                )

            print(f"S3 Bucket '{self.bucket_name}' erfolgreich erstellt")
        except Exception as e:
            print(f"Fehler beim Erstellen des Buckets: {e}")
            raise

    def update(self):
        """Update die S3 Bucket Konfiguration"""
        try:
            # Versioning Update
            self.s3_client.put_bucket_versioning(
                Bucket=self.bucket_name,
                VersioningConfiguration={
                    'Status': 'Enabled' if self.versioning else 'Suspended'
                }
            )

            # Encryption Update
            if self.encryption:
                self.s3_client.put_bucket_encryption(
                    Bucket=self.bucket_name,
                    ServerSideEncryptionConfiguration={
                        'Rules': [{
                            'ApplyServerSideEncryptionByDefault': {
                                'SSEAlgorithm': 'AES256'
                            }
                        }]
                    }
                )

            # Public Access Block Update
            self.s3_client.put_public_access_block(
                Bucket=self.bucket_name,
                PublicAccessBlockConfiguration={
                    'BlockPublicAcls': self.public_access_block,
                    'IgnorePublicAcls': self.public_access_block,
                    'BlockPublicPolicy': self.public_access_block,
                    'RestrictPublicBuckets': self.public_access_block
                }
            )

            print(f"S3 Bucket '{self.bucket_name}' erfolgreich aktualisiert")
        except Exception as e:
            print(f"Fehler beim Update des Buckets: {e}")
            raise

    def delete(self):
        """Lösche den S3 Bucket und alle Objekte darin"""
        try:
            # Lösche alle Objekte im Bucket
            paginator = self.s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=self.bucket_name)

            for page in pages:
                if 'Contents' in page:
                    for obj in page['Contents']:
                        self.s3_client.delete_object(
                            Bucket=self.bucket_name,
                            Key=obj['Key']
                        )

            # Lösche den leeren Bucket
            self.s3_client.delete_bucket(Bucket=self.bucket_name)
            print(f"S3 Bucket '{self.bucket_name}' erfolgreich gelöscht")
        except Exception as e:
            print(f"Fehler beim Löschen des Buckets: {e}")
            raise

    def __repr__(self) -> str:
        return f"S3(bucket='{self.bucket_name}', region='{self.env.region}')"


@dataclass
class AwsApp:
    name: str
    env: AwsEnviroment
    app_to_tech_id: dict[str, str]
    constructs: list[Resources]

app = AwsApp(name="example_1", env=AwsEnviroment(), app_to_tech_id={}, constructs=[])



