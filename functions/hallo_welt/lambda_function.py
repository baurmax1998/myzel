
def lambda_handler(event, context):
    """
    Lambda Handler für Hallo Welt Funktion.

    Args:
        event: Lambda Event mit optionalem 'name' Parameter
        context: Lambda Context

    Returns:
        dict: Response mit Statuscode und Body
    """
    name = event.get('name', 'Welt')

    message = f"Hallo {name}!! <3"

    return {
        'statusCode': 200,
        'body': message
    }
