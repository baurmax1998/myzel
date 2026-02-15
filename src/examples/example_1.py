from dataclasses import dataclass

from abc import ABC, abstractmethod
from typing import TypeVar, Type
import boto3
from botocore.session import Session
from src.core import deploy

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
    def get_resource_id(self) -> str:
        """Gebe eine fachliche resource_id zurück (z.B. bucket_name für S3)"""
        pass

    @abstractmethod
    def create(self) -> str:
        pass

    @abstractmethod
    def update(self, field: str = None, old_value: str = None, new_value: str = None):
        pass

    @abstractmethod
    def delete(self, tech_id: str):
        pass


class S3(Resources):
    """S3 Resource für AWS Bucket Management"""

    def __init__(
        self,
        resource_id: str,
        bucket_name: str,
        env: AwsEnviroment
    ):
        self.resource_id = resource_id
        self.bucket_name = bucket_name
        self.env = env
        self.aws_id = None
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
                bucket_name = bucket['Name']
                buckets.append(cls(resource_id=bucket_name, bucket_name=bucket_name, env=env))
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
                resource_id=tech_id,
                bucket_name=tech_id,
                env=env,
            )
        except Exception as e:
            print(f"Fehler beim Abrufen des Buckets {tech_id}: {e}")
            raise

    def read(self) -> dict:
        """Lese den aktuellen State des S3 Buckets von AWS"""
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            # Bucket existiert, gebe Properties zurück
            return {
                "bucket_name": self.bucket_name
            }
        except Exception:
            # Bucket existiert nicht
            return None

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
            self.aws_id = arn
            print(f"S3 Bucket '{self.bucket_name}' erfolgreich erstellt")
            return arn
        except Exception as e:
            print(f"Fehler beim Erstellen des Buckets: {e}")
            raise

    def update(self, field: str = None, old_value: str = None, new_value: str = None):
        """Update die S3 Bucket Konfiguration"""
        try:
            if field == "bucket_name":
                # Für bucket_name: alter Bucket muss gelöscht und neuer erstellt werden
                # (S3 Buckets können nicht umbenannt werden)
                print(f"S3 Bucket wird umbenannt: {old_value} -> {new_value}")

                # 1. Lösche den alten Bucket
                if old_value:
                    try:
                        self.s3_client.delete_bucket(Bucket=old_value)
                        print(f"  ✓ Alter Bucket '{old_value}' gelöscht")
                    except Exception as e:
                        print(f"  ⚠ Konnte alten Bucket nicht löschen: {e}")

                # 2. Erstelle neuen Bucket
                self.bucket_name = new_value
                kwargs = {
                    'Bucket': self.bucket_name,
                    'ACL': 'private'
                }
                if self.env.region != 'us-east-1':
                    kwargs['CreateBucketConfiguration'] = {
                        'LocationConstraint': self.env.region
                    }
                self.s3_client.create_bucket(**kwargs)
                self.aws_id = f"arn:aws:s3:::{self.bucket_name}"
                print(f"  ✓ Neuer Bucket '{new_value}' erstellt")
            else:
                print(f"S3 Bucket '{self.bucket_name}' wird aktualisiert: {field}={new_value}")
        except Exception as e:
            print(f"Fehler beim Update des Buckets: {e}")
            raise

    def delete(self, tech_id: str = None):
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

    def get_resource_id(self) -> str:
        """Gebe die fachliche resource_id zurück"""
        return self.resource_id

    def __repr__(self) -> str:
        return f"S3(bucket='{self.bucket_name}', region='{self.env.region}')"


@dataclass
class AwsApp:
    name: str
    env: AwsEnviroment
    app_to_tech_id: dict
    constructs: list

app = AwsApp(name="example_1", env=AwsEnviroment(), app_to_tech_id={}, constructs=[])


# S3 Bucket erstellen
s3_bucket = S3(
    resource_id="my-example-bucket-testmb-22",
    bucket_name="my-example-bucket-testmb-23",
    env=app.env
)
app.constructs.append(s3_bucket)

deploy(app)




