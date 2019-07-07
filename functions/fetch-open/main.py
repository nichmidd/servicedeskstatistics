'''Need to fix - just here to make PyLint happy'''
import sys
import base64
import json
import io
import datetime
import requests
from requests.utils import requote_uri
import pytz
from retrying import retry
from google.cloud import storage

# Global variables
LOCALRUN = False
LOCALSTORE = False

def fetchopened(event, context):
    '''Need to fix - just here to make PyLint happy'''
    message = base64.b64decode(event['data']).decode('utf-8')
    if message == "DAILY":
        config = loadconfig()
        timespan = calctime()
        getopenedtickets(timespan, config)
        storeresults(timespan, config)
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
    with open('config.json', 'r') as configfile:
        configjson = json.load(configfile)
    return configjson

def calctime():
    '''Need to fix - just here to make PyLint happy'''
    local_tz = pytz.timezone('UTC')
    target_tz = pytz.timezone('Australia/Sydney')
    timeutc = datetime.datetime.utcnow()
    timenow = local_tz.localize(timeutc)
    timeaus = (target_tz.normalize(timenow)).strftime("%Y-%m-%d")
    baseenddate = (datetime.datetime.strptime(timeaus, "%Y-%m-%d") - datetime.timedelta(days=1))
    tspan = str(int((datetime.datetime.combine(baseenddate, datetime.time(23, 59, 59))).strftime('%s'))*1000)
    return tspan

def getopenedtickets(timespan, config):
    '''Need to fix - just here to make PyLint happy'''
    with open('queryOpened.json', 'r') as fileopened:
        queryjson = json.load(fileopened)
    # here we search for all tickets opened before the end of the search day
    queryjson["list_info"]["search_criteria"][0]["value"] = timespan
    baseurl = config["url"] + '/api/v3/requests?TECHNICIAN_KEY=' + config["technicianKey"]
    ticketcount = 0
    for statuscode in config["statusCodes"]:
        queryjson["list_info"]["search_criteria"][1]["value"]["id"] = statuscode
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
                ticketcount = ticketcount + 1
                reqcreated = datetime.datetime.fromtimestamp(int(int(request["created_time"]["value"])/1000)).strftime("%Y-%m-%d %H:%M:%S")
                resultstring = reqid+","+reqpri+","+reqsite+","+reqcreated+"\n"
                config["results"].append(resultstring)
            more = jsonresults["list_info"]["has_more_rows"]
            if more:
                resultsindex = resultsindex + 100

def storeresults(daydate, config):
    '''Need to fix - just here to make PyLint happy'''
    daystring = datetime.datetime.fromtimestamp(int(int(daydate) / 1000)).strftime('%Y-%m-%d')
    headerline = "jobid,priority,site,opened"+"\n"
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

def calctimemanualinput(manualtime):
    '''Need to fix - just here to make PyLint happy'''
    fintime = datetime.datetime.strptime(str(manualtime), "%Y-%m-%d")
    tspan = str(int((datetime.datetime.combine(fintime, datetime.time(23, 59, 59))).strftime('%s'))*1000)
    config = loadconfig()
    getopenedtickets(tspan, config)
    storeresults(tspan, config)

if __name__ == "__main__":
    DATESTOPROCESS = list()
    DATESTOPROCESS.append(sys.argv[1])
    if len(sys.argv) > 2:
        if sys.argv[2] == "local":
            LOCALSTORE = True
    LOCALRUN = True
    calctimemanualinput(DATESTOPROCESS[0])
