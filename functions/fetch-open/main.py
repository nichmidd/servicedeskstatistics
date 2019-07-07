import sys
import datetime
import pytz
import base64
import requests
import json
import io
from retrying import retry
from requests.utils import requote_uri
from google.cloud import storage

# Global variables
LocalRun = False
LocalStore = False

def fetchOpened(event, context):
    message = base64.b64decode(event['data']).decode('utf-8')
    if (message == "DAILY"):
        config = loadConfig()
        timeSpan = calcTime()
        getOpenedTickets(timeSpan, config)
        storeResults(timeSpan, config)
    else:
        print("Not Supported")
    return 200

@retry(wait_random_min=1000, wait_random_max=5000, stop_max_attempt_number=3)
def fetchData(urlToFetch):
    response = requests.get(urlToFetch)
    return response

def loadConfig():
    with open('config.json', 'r') as c:
        cC = json.load(c)
    return cC

def calcTime():
    local_tz = pytz.timezone('UTC')
    target_tz = pytz.timezone('Australia/Sydney')
    timeUtc = datetime.datetime.utcnow()
    timeNow = local_tz.localize(timeUtc)
    timeAus  = (target_tz.normalize(timeNow)).strftime("%Y-%m-%d")
    baseEndDate = (datetime.datetime.strptime(timeAus, "%Y-%m-%d") - datetime.timedelta(days=1))
    tSpan = str(int((datetime.datetime.combine(baseEndDate, datetime.time(23,59,59))).strftime('%s'))*1000)
    return tSpan

def getOpenedTickets(timeSpan, config):
    with open('queryOpened.json', 'r') as f:
        queryJson = json.load(f)
    # here we search for all tickets opened before the end of the search day
    queryJson["list_info"]["search_criteria"][0]["value"] = timeSpan
    baseUrl = config["url"] + '/api/v3/requests?TECHNICIAN_KEY=' + config["technicianKey"]
    ticketCount = 0
    for statusCode in config["statusCodes"]:
        queryJson["list_info"]["search_criteria"][1]["value"]["id"] = statusCode
        more = True
        resultsIndex = 1
        while (more):
            queryJson["list_info"]["start_index"] = resultsIndex
            encodedUri = requote_uri(json.dumps(queryJson))
            queryUrl = baseUrl + '&input_data=' + encodedUri
            response = fetchData(queryUrl)
            jsonResults = response.json()
            for request in jsonResults["requests"]:
                reqId = request["id"] 
                if (request["priority"]):
                    if (request["priority"]["name"] in config["priorityTranslations"]):
                        reqPri = config["priorityTranslations"][request["priority"]["name"]]["Priority"]
                    else:
                        reqPri = request["priority"]["name"]
                else:
                    reqPri = ""
                if (request["site"]):
                    if (request["site"]["name"] in config["siteTranslations"]):
                        reqSite = config["siteTranslations"][request["site"]["name"]]["Name"]
                    else:
                        reqSite = request["site"]["name"]
                else:
                    reqSite = "NONE"
                ticketCount = ticketCount + 1
                reqCreated = datetime.datetime.fromtimestamp(int(int(request["created_time"]["value"])/1000)).strftime("%Y-%m-%d %H:%M:%S")
                resultString = reqId+","+reqPri+","+reqSite+","+reqCreated+"\n"
                config["results"].append(resultString)
            more = jsonResults["list_info"]["has_more_rows"]
            if (more):
                resultsIndex = resultsIndex + 100
    return

def storeResults(dayDate, config):
    dayString = datetime.datetime.fromtimestamp(int(int(dayDate) / 1000)).strftime('%Y-%m-%d')
    headerLine = "jobid,priority,site,opened"+"\n"
    if (LocalRun):
        print(dayString)
    fileName = config["storageFolder"] + dayString + ".csv"
    if (LocalStore):
        fileName = "./"+fileName
        fH = open(fileName, 'w')
    else:
        if (LocalRun):
            storage_client = storage.Client.from_service_account_json(config["googleJSONAuthKey"])
        else:
            storage_client = storage.Client()
        bucket = storage_client.get_bucket(config["googleStorageBucket"])
        blob = bucket.blob(fileName)
        fH = io.StringIO()
    fH.write(headerLine)
    for k in config["results"]:
        fH.write(k)
    if (LocalStore):
        fH.close()
    else:
        blob.upload_from_file(fH,rewind=True,content_type='text/csv')
        fH.close()    
    return

def calcTimeManualInput(manualTime):
    target_tz = pytz.timezone('Australia/Sydney')
    finTime = datetime.datetime.strptime(str(manualTime), "%Y-%m-%d")
    tSpan = str(int((datetime.datetime.combine(finTime, datetime.time(23,59,59))).strftime('%s'))*1000)
    config = loadConfig()
    getOpenedTickets(tSpan, config)
    storeResults(tSpan, config)
    return

if __name__ == "__main__":
    datesToProcess = list()
    datesToProcess.append(sys.argv[1])
    if (len(sys.argv) > 2):
        if (sys.argv[2] == "local"):
            LocalStore = True
    LocalRun = True
    calcTimeManualInput(datesToProcess[0])
