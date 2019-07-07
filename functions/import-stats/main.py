import sys
import json
import re
from google.cloud import bigquery 

# Globals
LocalRun = False

def importStats(event, context):
    fileName = event["name"]
    if (LocalRun):
        print(fileName)
    config = loadConfig()
    importToBQ(config, fileName)
    return 200
    
def loadConfig():
    with open('config.json', 'r') as c:
        cC = json.load(c)
    return cC

def importToBQ(config, filename):
    runType = ""
    ra = re.compile('stats-stats', re.IGNORECASE)
    rb = re.compile('stats-opened', re.IGNORECASE)
    rc = re.compile('stats-closed', re.IGNORECASE)
    if (LocalRun):
        client = bigquery.Client.from_service_account_json(config["googleJSONAuthKey"])
    else:
        client = bigquery.Client()
    if (ra.match(filename)):
        runType = "STATS"
        if (LocalRun):
            print("Stats Import")
        dataset_id = config["Stats"]["Dataset"]
        tableName = config["Stats"]["Table"]
        bucketName = config["Stats"]["Bucket"]
    elif (rb.match(filename)):
        runType = "OPENED"
        if (LocalRun):
            print("Opened Import")
        dataset_id = config["Opened"]["Dataset"]
        tableName = config["Opened"]["Table"]
        bucketName = config["Opened"]["Bucket"]
    elif (rc.match(filename)):
        runType = "CLOSED"
        if (LocalRun):
            print("Closed Import")
        dataset_id = config["Closed"]["Dataset"]
        tableName = config["Closed"]["Table"]
        bucketName = config["Closed"]["Bucket"]
    else:
        print("Error: Unable to parse filename: "+filename)
        return
    dataset_ref = client.dataset(dataset_id)
    job_config = bigquery.LoadJobConfig()
    if (runType == "STATS"):
        job_config.autodetect = True
    if runType in ("OPENED","CLOSED"):
        job_config.skip_leading_rows = 1
        job_config.max_bad_records = 1
    if (runType == "OPENED"):
        job_config.write_disposition = bigquery.WriteDisposition.WRITE_TRUNCATE
    job_config.source_format = bigquery.SourceFormat.CSV
    uriString = "gs://" + bucketName + "/" + filename
    load_job = client.load_table_from_uri(uriString, dataset_ref.table(tableName), job_config=job_config)
    if (LocalRun):
        print("Starting Job {}".format(load_job.job_id))
    load_job.result()
    destTable = client.get_table(dataset_ref.table(tableName))
    if (LocalRun):
        print("Job Finished. Loaded {} rows".format(destTable.num_rows))
    return

if __name__ == "__main__":
    mockEvent = dict()
    mockContext = dict()
    mockEvent["name"] = sys.argv[1]
    LocalRun = True
    importStats(mockEvent, mockContext)
