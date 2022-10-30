import boto3
import json

kinesisClient = boto3.client('kinesis')

def getUpsertRecord(ddbRecord):
    print('Upsert ' + json.dumps(ddbRecord))
    
    # Parse the NewImage json element
    newImage = ddbRecord['NewImage']

    # construct firehose record from NewImage
    firehoseRecord = {}
    firehoseRecord['Id'] = newImage['Id']['S']
    
    return firehoseRecord
   
def getDeleteRecord(ddbRecord):
    print('Delete '+  json.dumps(ddbRecord))
    return

def writeToStream(record):
    data = json.dumps(record)
    kinesisClient.put_record(
        StreamName='sync_stack_ingest_stream',
        Data=data,
        PartitionKey=record['Id'])

def lambda_handler(event, context):
    print("Received event: " + json.dumps(event, indent=2))
    for record in event['Records']:
        print("DynamoDB Record: " + json.dumps(record['dynamodb'], indent=2))
        if record['eventName'] == 'INSERT':
            fRecord = getUpsertRecord(record['dynamodb'])
        elif record['eventName'] == 'MODIFY':
            fRecord = getUpsertRecord(record['dynamodb'])
        elif record['eventName'] == 'REMOVE':
            fRecord = getDeleteRecord(record['dynamodb'])

        writeToStream(fRecord)

        
    return 'Successfully processed {} records.'.format(len(event['Records']))
