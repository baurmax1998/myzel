import boto3

from src.model import AwsEnviroment, Resources
from src.model.registry import register_resource


@register_resource("dynamodb")
class DynamoDB(Resources):
    """DynamoDB Resource für AWS DynamoDB Table Management"""

    def __init__(
        self,
        table_name: str,
        partition_key: dict,
        env: AwsEnviroment,
        sort_key: dict = None,
        billing_mode: str = "PAY_PER_REQUEST",
        global_secondary_indexes: list = None,
        stream_enabled: bool = False
    ):
        """
        Args:
            table_name: Name der DynamoDB Tabelle
            partition_key: Dict mit 'name' und 'type' (S, N, B)
            sort_key: Optional, Dict mit 'name' und 'type'
            billing_mode: PAY_PER_REQUEST oder PROVISIONED
            global_secondary_indexes: Optional, Liste von GSI Configs
            stream_enabled: Stream für CDC aktivieren
        """
        self.table_name = table_name
        self.partition_key = partition_key
        self.sort_key = sort_key
        self.billing_mode = billing_mode
        self.global_secondary_indexes = global_secondary_indexes or []
        self.stream_enabled = stream_enabled
        self.env = env

    @classmethod
    def get(cls, tech_id: str, env: AwsEnviroment) -> 'DynamoDB':
        """Hole eine spezifische DynamoDB Tabelle"""
        table_name = cls._extract_table_name(tech_id)
        session = boto3.session.Session(
            profile_name=env.profile,
            region_name=env.region
        )
        dynamodb_client = session.client('dynamodb')

        try:
            response = dynamodb_client.describe_table(TableName=table_name)
            table = response['Table']

            partition_key = None
            sort_key = None
            for key_schema in table['KeySchema']:
                if key_schema['KeyType'] == 'HASH':
                    for attr in table['AttributeDefinitions']:
                        if attr['AttributeName'] == key_schema['AttributeName']:
                            partition_key = {'name': attr['AttributeName'], 'type': attr['AttributeType']}
                elif key_schema['KeyType'] == 'RANGE':
                    for attr in table['AttributeDefinitions']:
                        if attr['AttributeName'] == key_schema['AttributeName']:
                            sort_key = {'name': attr['AttributeName'], 'type': attr['AttributeType']}

            return cls(
                table_name=table['TableName'],
                partition_key=partition_key,
                sort_key=sort_key,
                billing_mode=table.get('BillingModeSummary', {}).get('BillingMode', 'PAY_PER_REQUEST'),
                stream_enabled=table.get('StreamSpecification', {}).get('StreamEnabled', False),
                env=env
            )
        except Exception as e:
            print(f"Fehler beim Abrufen der DynamoDB Tabelle {table_name}: {e}")
            raise

    def create(self) -> str:
        """Erstelle eine neue DynamoDB Tabelle oder verwende existierende"""
        session = boto3.session.Session(
            profile_name=self.env.profile,
            region_name=self.env.region
        )
        dynamodb_client = session.client('dynamodb')

        try:
            response = dynamodb_client.describe_table(TableName=self.table_name)
            print(f"DynamoDB Tabelle existiert bereits: {self.table_name}")
            return response['Table']['TableArn']
        except dynamodb_client.exceptions.ResourceNotFoundException:
            pass

        attribute_definitions = [
            {
                'AttributeName': self.partition_key['name'],
                'AttributeType': self.partition_key['type']
            }
        ]

        key_schema = [
            {
                'AttributeName': self.partition_key['name'],
                'KeyType': 'HASH'
            }
        ]

        if self.sort_key:
            attribute_definitions.append({
                'AttributeName': self.sort_key['name'],
                'AttributeType': self.sort_key['type']
            })
            key_schema.append({
                'AttributeName': self.sort_key['name'],
                'KeyType': 'RANGE'
            })

        table_config = {
            'TableName': self.table_name,
            'KeySchema': key_schema,
            'AttributeDefinitions': attribute_definitions,
            'BillingMode': self.billing_mode
        }

        if self.stream_enabled:
            table_config['StreamSpecification'] = {
                'StreamEnabled': True,
                'StreamViewType': 'NEW_AND_OLD_IMAGES'
            }

        if self.global_secondary_indexes:
            table_config['GlobalSecondaryIndexes'] = self.global_secondary_indexes
            for gsi in self.global_secondary_indexes:
                for key in gsi['KeySchema']:
                    attr_name = key['AttributeName']
                    if not any(attr['AttributeName'] == attr_name for attr in attribute_definitions):
                        attribute_definitions.append({
                            'AttributeName': attr_name,
                            'AttributeType': 'S'
                        })

        response = dynamodb_client.create_table(**table_config)

        arn = response['TableDescription']['TableArn']
        print(f"DynamoDB Tabelle erstellt: {self.table_name}")
        print(f"ARN: {arn}")
        print(f"Partition Key: {self.partition_key['name']} ({self.partition_key['type']})")
        if self.sort_key:
            print(f"Sort Key: {self.sort_key['name']} ({self.sort_key['type']})")
        print(f"Billing Mode: {self.billing_mode}")

        print("Warte auf Tabelle...")
        waiter = dynamodb_client.get_waiter('table_exists')
        waiter.wait(TableName=self.table_name)
        print("Tabelle ist bereit")

        return arn

    def update(self, deployed_tech_id: str, new_value: 'DynamoDB') -> str:
        """Update eine DynamoDB Tabelle"""
        table_name = self._extract_table_name(deployed_tech_id)

        session = boto3.session.Session(
            profile_name=new_value.env.profile,
            region_name=new_value.env.region
        )
        dynamodb_client = session.client('dynamodb')

        try:
            response = dynamodb_client.describe_table(TableName=table_name)
            arn = response['Table']['TableArn']

            print(f"DynamoDB Tabelle {table_name} ist bereits aktuell")
            return arn

        except Exception as e:
            print(f"Fehler beim Update der DynamoDB Tabelle: {e}")
            raise

    def delete(self, tech_id: str):
        """Lösche eine DynamoDB Tabelle"""
        table_name = self._extract_table_name(tech_id)

        session = boto3.session.Session(
            profile_name=self.env.profile,
            region_name=self.env.region
        )
        dynamodb_client = session.client('dynamodb')

        try:
            dynamodb_client.delete_table(TableName=table_name)
            print(f"DynamoDB Tabelle gelöscht: {table_name}")

            print("Warte auf Löschung...")
            waiter = dynamodb_client.get_waiter('table_not_exists')
            waiter.wait(TableName=table_name)
            print("Tabelle wurde gelöscht")

        except Exception as e:
            print(f"Fehler beim Löschen der DynamoDB Tabelle: {e}")
            raise

    @staticmethod
    def _extract_table_name(arn: str) -> str:
        """Extrahiere Table Name aus ARN"""
        return arn.split('/')[-1]

    def __repr__(self) -> str:
        return f"DynamoDB(table='{self.table_name}')"
