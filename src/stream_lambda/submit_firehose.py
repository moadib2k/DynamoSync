import json

def getUpsertRecord(ddbRecord):
    print('Upsert ' + json.dumps(ddbRecord))
    
    firehoseRecord = ''
    # Parse the NewImage json element
    newImage = ddbRecord['NewImage']

    # construct firehose record from NewImage
    firehoseRecord = '{}'.format(newImage['Id']['S'])
    
    return firehoseRecord
   
def getDeleteRecord(ddbRecord):
    print('Delete '+  json.dumps(ddbRecord))
    return

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
        
    return 'Successfully processed {} records.'.format(len(event['Records']))
