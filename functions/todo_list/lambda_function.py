import json
import boto3
import os

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ.get('TABLE_NAME', 'todos'))


def lambda_handler(event, context):
    """
    List all todo items.
    """
    try:
        response = table.scan()
        items = response.get('Items', [])

        items.sort(key=lambda x: x.get('created_at', 0), reverse=True)

        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'todos': items})
        }

    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': str(e)})
        }
