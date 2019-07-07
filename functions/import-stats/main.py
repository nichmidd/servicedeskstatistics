'''Need to fix - just here to make PyLint happy'''
import sys
import json
import re
from google.cloud import bigquery

# Globals
LOCALRUN = False

def importstats(event, context):
    '''Need to fix - just here to make PyLint happy'''
    filename = event["name"]
    if LOCALRUN:
        print(filename)
        print(context)
    config = loadconfig()
    importtobq(config, filename)
    return 200

def loadconfig():
    '''Need to fix - just here to make PyLint happy'''
    with open('config.json', 'r') as fileconfig:
        configjson = json.load(fileconfig)
    return configjson

def importtobq(config, filename):
    '''Need to fix - just here to make PyLint happy'''
    runtype = ""
    regexpstats = re.compile('stats-stats', re.IGNORECASE)
    regexpopened = re.compile('stats-opened', re.IGNORECASE)
    regexpclosed = re.compile('stats-closed', re.IGNORECASE)
    if LOCALRUN:
        client = bigquery.Client.from_service_account_json(config["googleJSONAuthKey"])
    else:
        client = bigquery.Client()
    if regexpstats.match(filename):
        runtype = "STATS"
        if LOCALRUN:
            print("Stats Import")
        dataset_id = config["Stats"]["Dataset"]
        tablename = config["Stats"]["Table"]
        bucketname = config["Stats"]["Bucket"]
    elif regexpopened.match(filename):
        runtype = "OPENED"
        if LOCALRUN:
            print("Opened Import")
        dataset_id = config["Opened"]["Dataset"]
        tablename = config["Opened"]["Table"]
        bucketname = config["Opened"]["Bucket"]
    elif regexpclosed.match(filename):
        runtype = "CLOSED"
        if LOCALRUN:
            print("Closed Import")
        dataset_id = config["Closed"]["Dataset"]
        tablename = config["Closed"]["Table"]
        bucketname = config["Closed"]["Bucket"]
    else:
        print("Error: Unable to parse filename: "+filename)
        return
    dataset_ref = client.dataset(dataset_id)
    job_config = bigquery.LoadJobConfig()
    if runtype == "STATS":
        job_config.autodetect = True
    if runtype in ("OPENED", "CLOSED"):
        job_config.skip_leading_rows = 1
        job_config.max_bad_records = 1
    if runtype == "OPENED":
        job_config.write_disposition = bigquery.WriteDisposition.WRITE_TRUNCATE
    job_config.source_format = bigquery.SourceFormat.CSV
    uristring = "gs://" + bucketname + "/" + filename
    load_job = client.load_table_from_uri(uristring, dataset_ref.table(tablename), job_config=job_config)
    if LOCALRUN:
        print("Starting Job {}".format(load_job.job_id))
    load_job.result()
    desttable = client.get_table(dataset_ref.table(tablename))
    if LOCALRUN:
        print("Job Finished. Loaded {} rows".format(desttable.num_rows))

if __name__ == "__main__":
    MOCKEVENT = dict()
    MOCKCONTEXT = dict()
    MOCKEVENT["name"] = sys.argv[1]
    LOCALRUN = True
    importstats(MOCKEVENT, MOCKCONTEXT)
