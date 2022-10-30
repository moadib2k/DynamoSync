
-- Note that the default role has to be set in the console
-- https://github.com/aws/aws-cdk/issues/22551 traking the cr for this


-- Link Redshift to the kinesis stream
CREATE EXTERNAL SCHEMA kinesis_schema
FROM KINESIS
IAM_ROLE default;

-- create a materialized view of the stream 
CREATE MATERIALIZED VIEW ingest_stream AS
SELECT approximate_arrival_timestamp, partition_key, shard_id, sequence_number, kinesis_data,
	CAST(JSON_EXTRACT_PATH_TEXT(from_varbyte(kinesis_data, 'utf-8'), 'Id', true) AS VARCHAR(36)) as Id
FROM kinesis_schema.sync_stack_ingest_stream
WHERE is_utf8(kinesis_data) AND is_valid_json(from_varbyte(kinesis_data, 'utf-8'));

-- refresh the stream
REFRESH MATERIALIZED VIEW ingest_stream;

