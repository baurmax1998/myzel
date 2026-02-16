import boto3

from src.model import AwsEnviroment, Resources
from src.model.registry import register_resource


@register_resource("s3")
class S3(Resources):
    """S3 Resource für AWS Bucket Management"""

    def __init__(
        self,
        bucket_name: str,
        env: AwsEnviroment
    ):
        self.bucket_name = bucket_name
        self.env = env

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
                buckets.append(cls(bucket_name=bucket_name, env=env))
            return buckets
        except Exception as e:
            print(f"Fehler beim Auflisten der Buckets: {e}")
            return []

    @classmethod
    def get(cls, tech_id: str, env: AwsEnviroment) -> 'S3':
        """Hole einen spezifischen S3 Bucket aus ARN"""
        bucket_name = cls._extract_bucket_name(tech_id)
        session = boto3.session.Session(
            profile_name=env.profile,
            region_name=env.region
        )
        s3_client = session.client('s3')

        try:
            s3_client.head_bucket(Bucket=bucket_name)
            return cls(bucket_name=bucket_name, env=env)
        except Exception as e:
            print(f"Fehler beim Abrufen des Buckets {bucket_name}: {e}")
            raise

    def create(self) -> str:
        """Erstelle einen neuen S3 Bucket oder nutze existierenden"""
        session = boto3.session.Session(
            profile_name=self.env.profile,
            region_name=self.env.region
        )
        s3_client = session.client('s3')

        try:
            if self._bucket_exists(self.bucket_name, s3_client):
                print(f"S3 Bucket '{self.bucket_name}' existiert bereits")
            else:
                if self.env.region == 'us-east-1':
                    s3_client.create_bucket(Bucket=self.bucket_name)
                else:
                    s3_client.create_bucket(
                        Bucket=self.bucket_name,
                        CreateBucketConfiguration={'LocationConstraint': self.env.region}
                    )
                print(f"S3 Bucket '{self.bucket_name}' erfolgreich erstellt")

            arn = f"arn:aws:s3:::{self.bucket_name}"
            return arn
        except Exception as e:
            print(f"Fehler beim Erstellen des Buckets: {e}")
            raise

    def update(self, deployed_tech_id: str, new_value: 'S3') -> str:
        """Update S3 Bucket - Erstelle neuen Bucket, sync Inhalte und lösche alten"""
        deployed_bucket_name = self._extract_bucket_name(deployed_tech_id)
        new_bucket_name = new_value.bucket_name

        if deployed_bucket_name == new_bucket_name:
            print(f"S3 Bucket '{deployed_bucket_name}' ist bereits aktuell")
            arn = f"arn:aws:s3:::{deployed_bucket_name}"
            return arn

        session = boto3.session.Session(
            profile_name=new_value.env.profile,
            region_name=new_value.env.region
        )
        s3_client = session.client('s3')

        try:
            # 1. Neuen Bucket erstellen, falls er nicht existiert
            if new_value._bucket_exists(new_bucket_name, s3_client):
                print(f"S3 Bucket '{new_bucket_name}' existiert bereits")
            else:
                print(f"Erstelle neuen S3 Bucket '{new_bucket_name}'")
                if new_value.env.region == 'us-east-1':
                    s3_client.create_bucket(Bucket=new_bucket_name)
                else:
                    s3_client.create_bucket(
                        Bucket=new_bucket_name,
                        CreateBucketConfiguration={'LocationConstraint': new_value.env.region}
                    )

            # 2. Prüfe ob neuer Bucket leer ist
            response = s3_client.list_objects_v2(Bucket=new_bucket_name)
            if response.get('Contents'):
                print(f"Fehler: S3 Bucket '{new_bucket_name}' ist nicht leer")
                raise Exception(f"Ziel-Bucket '{new_bucket_name}' ist nicht leer")

            # 3. Sync Inhalte vom alten zum neuen Bucket
            if deployed_bucket_name:
                print(f"Synce Inhalte von '{deployed_bucket_name}' zu '{new_bucket_name}'")
                paginator = s3_client.get_paginator('list_objects_v2')
                pages = paginator.paginate(Bucket=deployed_bucket_name)

                for page in pages:
                    if 'Contents' in page:
                        for obj in page['Contents']:
                            key = obj['Key']
                            copy_source = {'Bucket': deployed_bucket_name, 'Key': key}
                            s3_client.copy_object(CopySource=copy_source, Bucket=new_bucket_name, Key=key)
                            print(f"  Kopiert: {key}")

            # 4. Lösche alten Bucket
            if deployed_bucket_name:
                print(f"Lösche alten S3 Bucket '{deployed_bucket_name}'")
                s3_client.delete_bucket(Bucket=deployed_bucket_name)

            arn = f"arn:aws:s3:::{new_bucket_name}"
            print(f"S3 Bucket erfolgreich von '{deployed_bucket_name}' zu '{new_bucket_name}' migriert")
            return arn

        except Exception as e:
            print(f"Fehler beim Update des Buckets: {e}")
            raise

    def delete(self, tech_id: str):
        """Lösche einen S3 Bucket"""
        session = boto3.session.Session(
            profile_name=self.env.profile,
            region_name=self.env.region
        )
        s3_client = session.client('s3')

        try:
            s3_client.delete_bucket(Bucket=tech_id)
            print(f"S3 Bucket '{tech_id}' erfolgreich gelöscht")
        except Exception as e:
            print(f"Fehler beim Löschen des Buckets: {e}")
            raise

    @staticmethod
    def _extract_bucket_name(arn: str) -> str:
        """Extrahiere Bucket-Namen aus ARN
        Format: arn:aws:s3:::bucket-name
        """
        return arn.split(':::')[-1]

    def _bucket_exists(self, bucket_name: str, s3_client) -> bool:
        """Prüfe ob ein Bucket existiert"""
        try:
            s3_client.head_bucket(Bucket=bucket_name)
            return True
        except:
            return False

    def __repr__(self) -> str:
        return f"S3(bucket='{self.bucket_name}')"
