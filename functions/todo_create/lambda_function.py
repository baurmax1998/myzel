import json
import uuid
import time
import boto3
import os

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ.get('TABLE_NAME', 'todos'))


def lambda_handler(event, context):
    """
    Create a new todo item.

    Expected body: {"title": "My Todo", "description": "Optional description"}
    """
    try:
        body = json.loads(event.get('body', '{}'))
        title = body.get('title', '').strip()

        if not title:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'Title is required'})
            }

        todo_id = str(uuid.uuid4())
        timestamp = int(time.time())

        item = {
            'id': todo_id,
            'title': title,
            'description': body.get('description', ''),
            'completed': False,
            'created_at': timestamp,
            'updated_at': timestamp
        }

        table.put_item(Item=item)

        return {
            'statusCode': 201,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps(item)
        }

    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': str(e)})
        }
