import json
import boto3
import os

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ.get('TABLE_NAME', 'todos'))


def lambda_handler(event, context):
    """
    Delete a todo item.

    Path parameter: id
    """
    try:
        path_params = event.get('pathParameters', {}) or {}
        todo_id = path_params.get('id')

        if not todo_id:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'ID is required'})
            }

        table.delete_item(Key={'id': todo_id})

        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'message': 'Todo deleted'})
        }

    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': str(e)})
        }
