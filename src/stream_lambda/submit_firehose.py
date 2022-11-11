import boto3
import json

kinesisClient = boto3.client('kinesis')

def getFireHoseRecord(sourceImage, eventType):

    firehoseRecord = {}
    for k in sourceImage.keys():
        firehoseRecord[k] = sourceImage[k]['S']
    firehoseRecord['dynamo_event'] = eventType
    return firehoseRecord

def writeToStream(record):
    data = json.dumps(record)
    kinesisClient.put_record(
        StreamName='sync_stack_ingest_stream',
        Data=data,
        PartitionKey=record['Id'])

def lambda_handler(event, context):
    print("Received event: " + json.dumps(event))
    for record in event['Records']:

        # get the root record
        ddbrecord = record['dynamodb']
        print("DynamoDB Record: " + json.dumps(ddbrecord))

        if record['eventName'] == 'INSERT':
            fRecord = getFireHoseRecord(ddbrecord ['NewImage'], 'INSERT')

        elif record['eventName'] == 'MODIFY':
            fRecord = getFireHoseRecord(ddbrecord ['NewImage'], 'MODIFY')

        elif record['eventName'] == 'REMOVE':
            fRecord = getFireHoseRecord(ddbrecord ['OldImage'], 'REMOVE')

        writeToStream(fRecord)
        
    return 'Successfully processed {} records.'.format(len(event['Records']))

