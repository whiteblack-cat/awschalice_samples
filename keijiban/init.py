import boto3

def init(tablename):
    client = boto3.client('dynamodb')
    dynamodb = boto3.resource('dynamodb')

    try:
        table = dynamodb.create_table(
            TableName=tablename,
            KeySchema=[
                {
                    'AttributeName': 'hash',
                    'KeyType': 'HASH'
                },
                {
                    'AttributeName': 'range',
                    'KeyType': 'RANGE'
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'hash',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'range',
                    'AttributeType': 'S'
                },
            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 1,
                'WriteCapacityUnits': 1
            }
        )
        table.wait_until_exists()
    except client.exceptions.ResourceInUseException:
        pass

    client.update_time_to_live(
        TableName=tablename,
        TimeToLiveSpecification={
            'Enabled': True,
            'AttributeName': 'ttl'
        }
    )
