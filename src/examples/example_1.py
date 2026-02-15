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
    def create(self) -> str:
        pass

    @abstractmethod
    def update(self, tech_id: str):
        pass

    @abstractmethod
    def delete(self):
        pass


class S3(Resources):
    """S3 Resource für AWS Bucket Management"""

    def __init__(
        self,
        bucket_name: str,
        env: AwsEnviroment
    ):
        self.bucket_name = bucket_name
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


            return cls(
                bucket_name=tech_id,
                env=env,
            )
        except Exception as e:
            print(f"Fehler beim Abrufen des Buckets {tech_id}: {e}")
            raise

    def create(self) -> str:
        """Erstelle einen neuen S3 Bucket und gebe die ARN zurück"""
        try:
            kwargs = {
                'Bucket': self.bucket_name,
                'ACL': 'private'
            }

            if self.env.region != 'us-east-1':
                kwargs['CreateBucketConfiguration'] = {
                    'LocationConstraint': self.env.region
                }

            self.s3_client.create_bucket(**kwargs)

            arn = f"arn:aws:s3:::{self.bucket_name}"
            print(f"S3 Bucket '{self.bucket_name}' erfolgreich erstellt")
            return arn
        except Exception as e:
            print(f"Fehler beim Erstellen des Buckets: {e}")
            raise

    def update(self, tech_id: str):
        """Update die S3 Bucket Konfiguration"""
        try:
            print(f"S3 Bucket '{self.bucket_name}' wird aktualisiert")
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

s3_elements = S3.list(app.env)
print("s3_elements")

# S3 Bucket erstellen
s3_bucket = S3(
    bucket_name="my-example-bucket-testmb",
    env=app.env
)
arn = s3_bucket.create()
print(f"Erstellte ARN: {arn}")



