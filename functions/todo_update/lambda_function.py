import json
import time
import boto3
import os

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ.get('TABLE_NAME', 'todos'))


def lambda_handler(event, context):
    """
    Update a todo item.

    Path parameter: id
    Body: {"title": "Updated", "description": "Updated desc", "completed": true}
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

        body = json.loads(event.get('body', '{}'))

        update_expression = "SET updated_at = :updated_at"
        expression_values = {':updated_at': int(time.time())}

        if 'title' in body:
            update_expression += ", title = :title"
            expression_values[':title'] = body['title']

        if 'description' in body:
            update_expression += ", description = :description"
            expression_values[':description'] = body['description']

        if 'completed' in body:
            update_expression += ", completed = :completed"
            expression_values[':completed'] = body['completed']

        response = table.update_item(
            Key={'id': todo_id},
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_values,
            ReturnValues='ALL_NEW'
        )

        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps(response['Attributes'])
        }

    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': str(e)})
        }
