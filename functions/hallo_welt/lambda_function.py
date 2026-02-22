import json


def lambda_handler(event, context):
    """
    Lambda Handler für Hallo Welt Funktion.

    Args:
        event: Lambda Event mit optionalem 'name' Parameter
        context: Lambda Context

    Returns:
        dict: Response mit Statuscode und Body
    """
    # Query Parameter aus API Gateway Event
    query_params = event.get('queryStringParameters', {}) or {}
    name = query_params.get('name', 'Welt')

    message = f"Hallo {name}!! <3"

    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json'
        },
        'body': json.dumps({'message': message})
    }
