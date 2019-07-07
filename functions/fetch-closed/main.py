'''Need to fix - just here to make PyLint happy'''
import sys
import datetime
import base64
import json
import io
import requests
from requests.utils import requote_uri
import pytz
from retrying import retry
from google.cloud import storage

# Global variables
LOCALRUN = False
LOCALSTORE = False

def fetchclosed(event, context):
    '''Need to fix - just here to make PyLint happy'''
    message = base64.b64decode(event['data']).decode('utf-8')
    if message == "DAILY":
        config = loadconfig()
        timespan = calctime()
        getclosedtickets(timespan, config)
        storeresults(timespan[0], config)
    else:
        print("Not Supported")
        print(context)
    return 200

@retry(wait_random_min=1000, wait_random_max=5000, stop_max_attempt_number=3)
def fetchdata(urltofetch):
    '''Need to fix - just here to make PyLint happy'''
    response = requests.get(urltofetch)
    return response

def loadconfig():
    '''Need to fix - just here to make PyLint happy'''
    with open('config.json', 'r') as config:
        configjson = json.load(config)
    return configjson

def calctime():
    '''Need to fix - just here to make PyLint happy'''
    local_tz = pytz.timezone('UTC')
    target_tz = pytz.timezone('Australia/Sydney')
    timeutc = datetime.datetime.utcnow()
    timenow = local_tz.localize(timeutc)
    timeaus = (target_tz.normalize(timenow)).strftime("%Y-%m-%d")
    basestartdate = (datetime.datetime.strptime(timeaus, "%Y-%m-%d") - datetime.timedelta(days=1))
    baseenddate = (datetime.datetime.strptime(timeaus, "%Y-%m-%d") - datetime.timedelta(days=1))
    tspan = []
    tspan.append(str(int((datetime.datetime.combine(basestartdate, datetime.time(0, 0, 0))).strftime('%s'))*1000))
    tspan.append(str((int((datetime.datetime.combine(baseenddate, datetime.time(23, 59, 59))).strftime('%s'))*1000)+999))
    return tspan

def getclosedtickets(timespan, config):
    '''Need to fix - just here to make PyLint happy'''
    with open('queryClosed.json', 'r') as queryfile:
        queryjson = json.load(queryfile)
    queryjson["list_info"]["search_criteria"][0]["value"] = timespan[0]
    queryjson["list_info"]["search_criteria"][1]["value"] = timespan[1]
    baseurl = config["url"] + '/api/v3/requests?TECHNICIAN_KEY=' + config["technicianKey"]
    more = True
    resultsindex = 1
    while more:
        queryjson["list_info"]["start_index"] = resultsindex
        encodeduri = requote_uri(json.dumps(queryjson))
        queryurl = baseurl + '&input_data=' + encodeduri
        response = fetchdata(queryurl)
        jsonresults = response.json()
        for request in jsonresults["requests"]:
            reqid = request["id"]
            if request["priority"]:
                if request["priority"]["name"] in config["priorityTranslations"]:
                    reqpri = config["priorityTranslations"][request["priority"]["name"]]["Priority"]
                else:
                    reqpri = request["priority"]["name"]
            else:
                reqpri = ""
            if request["site"]:
                if request["site"]["name"] in config["siteTranslations"]:
                    reqsite = config["siteTranslations"][request["site"]["name"]]["Name"]
                else:
                    reqsite = request["site"]["name"]
            else:
                reqsite = "NONE"
            reqcreated = datetime.datetime.fromtimestamp(int(int(request["created_time"]["value"])/1000)).strftime("%Y-%m-%d %H:%M:%S")
            reqclosed = datetime.datetime.fromtimestamp(int(int(request["resolved_time"]["value"])/1000)).strftime("%Y-%m-%d %H:%M:%S")
            resultstring = reqid+","+reqpri+","+reqsite+","+reqcreated+","+reqclosed+"\n"
            config["results"].append(resultstring)
        more = jsonresults["list_info"]["has_more_rows"]
        if more:
            resultsindex = resultsindex + 100

def storeresults(daydate, config):
    '''Need to fix - just here to make PyLint happy'''
    daystring = datetime.datetime.fromtimestamp(int(int(daydate) / 1000)).strftime('%Y-%m-%d')
    headerline = "jobid,priority,site,opened,closed"+"\n"
    if LOCALRUN:
        print(daystring)
    filename = config["storageFolder"] + daystring + ".csv"
    if LOCALSTORE:
        filename = "./"+filename
        filehandle = open(filename, 'w')
    else:
        if LOCALRUN:
            storage_client = storage.Client.from_service_account_json(config["googleJSONAuthKey"])
        else:
            storage_client = storage.Client()
        bucket = storage_client.get_bucket(config["googleStorageBucket"])
        blob = bucket.blob(filename)
        filehandle = io.StringIO()
    filehandle.write(headerline)
    for resultskey in config["results"]:
        filehandle.write(resultskey)
    if LOCALSTORE:
        filehandle.close()
    else:
        blob.upload_from_file(filehandle, rewind=True, content_type='text/csv')
        filehandle.close()

def calctimemanualinput(manualtimes):
    '''Need to fix - just here to make PyLint happy'''
    starttime = datetime.datetime.strptime(str(manualtimes[0]), "%Y-%m-%d")
    starttime = datetime.datetime.combine(starttime, datetime.time(0, 0, 0))
    fintime = datetime.datetime.strptime(str(manualtimes[1]), "%Y-%m-%d")
    fintime = datetime.datetime.combine(fintime, datetime.time(23, 59, 59))
    etime = "0"
    ftime = str((int(fintime.strftime('%s')) * 1000) + 999)
    while int(ftime) > int(etime):
        config = loadconfig()
        stime = str(int(starttime.strftime('%s')) * 1000)
        endtime = datetime.datetime.combine(starttime, datetime.time(23, 59, 59))
        etime = str((int(endtime.strftime('%s'))*1000)+999)
        tspan = [stime, etime]
        getclosedtickets(tspan, config)
        storeresults(tspan[0], config)
        starttime = starttime + datetime.timedelta(days=1)

if __name__ == "__main__":
    DATES_TO_PROCESS = []
    DATES_TO_PROCESS.append(sys.argv[1])
    DATES_TO_PROCESS.append(sys.argv[2])
    if len(sys.argv) > 3:
        if sys.argv[3] == "local":
            LOCALSTORE = True
    LOCALRUN = True
    calctimemanualinput(DATES_TO_PROCESS)
