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

# Global Variables
OneDay = 86400 * 1000
FourDays = (4 * OneDay)
SevenDays = (7 * OneDay)
TwoWeeks = (2 * SevenDays)
FourWeeks = (4 * SevenDays)
SixWeeks = (6 * SevenDays)
LocalRun = False
LocalStore = False

def fetchStats(event, context):
    message = base64.b64decode(event['data']).decode('utf-8')
    if (message == "DAILY"):
        config = loadConfig()
        timeSpan = calcTime()
        getOpenTickets(timeSpan, config)
        getClosedTickets(timeSpan, config)
        getOutstandingClosed(timeSpan, config)
        getOutstandingOpen(timeSpan, config)
        storeResults(timeSpan[0], config)
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
        for k in cC["results"]:
            cC["results"][k]["TotalOpened"] = "0"
            cC["results"][k]["TotalClosed"] = "0"
            cC["results"][k]["TotalOutstanding"] = "0"
            cC["results"][k]["Out6W"] = "0"
            cC["results"][k]["Out4W"] = "0"
            cC["results"][k]["Out2W"] = "0"
            cC["results"][k]["Out7D"] = "0"
            cC["results"][k]["Out4D"] = "0"
            cC["results"][k]["OutL4D"] = "0"
            cC["results"][k]["ClosedSameDay"] = "0"
        return cC

def calcTime():
    local_tz = pytz.timezone('UTC')
    target_tz = pytz.timezone('Australia/Sydney')
    timeUtc = datetime.datetime.utcnow()
    timeNow = local_tz.localize(timeUtc)
    timeAus  = (target_tz.normalize(timeNow)).strftime("%Y-%m-%d")
    # because this is running in google on utc we don't want to go a day ago
    # no, you are an idiot!!! read the code 2 lines up!
    baseStartDate = (datetime.datetime.strptime(timeAus, "%Y-%m-%d") - datetime.timedelta(days=1))
    #baseStartDate = datetime.datetime.strptime(timeAus, "%Y-%m-%d")
    baseEndDate = (datetime.datetime.strptime(timeAus, "%Y-%m-%d") - datetime.timedelta(days=1))
    tSpan = []
    tSpan.append(str(int((datetime.datetime.combine(baseStartDate, datetime.time(0,0,0))).strftime('%s'))*1000))
    tSpan.append(str((int((datetime.datetime.combine(baseEndDate, datetime.time(23,59,59))).strftime('%s'))*1000)+999))
    return tSpan

def calcTimeManualInput(manualTimes):
    target_tz = pytz.timezone('Australia/Sydney')
    startTime = datetime.datetime.strptime(str(manualTimes[0]), "%Y-%m-%d")
    startTime = datetime.datetime.combine(startTime, datetime.time(0,0,0))
    startTime = target_tz.localize(startTime)
    finTime = datetime.datetime.strptime(str(manualTimes[1]), "%Y-%m-%d")
    finTime = datetime.datetime.combine(finTime, datetime.time(23,59,59))
    finTime = target_tz.localize(finTime)
    eTime = "0"
    fTime = str((int(finTime.strftime('%s')) * 1000) + 999)
    while (int(fTime) > int(eTime)):
        # we have to reset the config on each time or the numbers just keep growing
        config = loadConfig()
        sTime = str(int(startTime.strftime('%s')) * 1000)
        endTime = datetime.datetime.combine(startTime, datetime.time(23,59,59))
        eTime = str((int(endTime.strftime('%s'))*1000)+999)
        tSpan = [sTime, eTime]
        getOpenTickets(tSpan, config)
        getClosedTickets(tSpan, config)
        getOutstandingClosed(tSpan, config)
        getOutstandingOpen(tSpan, config)
        storeResults(tSpan[0], config)
        startTime = startTime + datetime.timedelta(days=1)
    return

def getOpenTickets(timeSpan, config):
    with open('queryOpened.json', 'r') as f:
        queryJson = json.load(f)
    queryJson["list_info"]["search_criteria"][0]["value"] = timeSpan[0]
    queryJson["list_info"]["search_criteria"][1]["value"] = timeSpan[1]
    baseUrl = config["url"] + '/api/v3/requests?TECHNICIAN_KEY=' + config["technicianKey"]
    more = True
    resultsIndex = 1
    ticketCount = 0
    while (more):
        queryJson["list_info"]["start_index"] = resultsIndex
        encodedUri = requote_uri(json.dumps(queryJson))
        queryUrl = baseUrl + '&input_data=' + encodedUri
        response = fetchData(queryUrl)
        jsonResults = response.json()
        for request in jsonResults["requests"]:
            reqId = request["id"]
            # translate local priorities to standard ones
            if (request["priority"]):
                if (request["priority"]["name"] in config["priorityTranslations"]):
                    reqPri = config["priorityTranslations"][request["priority"]["name"]]["Priority"]
                else:
                    reqPri = request["priority"]["name"]
            else:
                reqPri = ""
            # translate extra sites to other ones
            if (request["site"]):
                if (request["site"]["name"] in config["siteTranslations"]):
                    reqSite = config["siteTranslations"][request["site"]["name"]]["Name"]
                else:
                    reqSite = request["site"]["name"]
            else:
                reqSite = "NONE"
            if reqSite in config["results"]:
                config["results"][reqSite]["TotalOpened"] = str(int(config["results"][reqSite]["TotalOpened"]) + 1)
            else:
                config["UnknownSites"].append(reqSite)
                reqSite = "UNKNOWN"
                config["results"][reqSite]["TotalOpened"] = str(int(config["results"][reqSite]["TotalOpened"]) + 1)
            if (request["resolved_time"]):
                if (request["resolved_time"]["value"] < timeSpan[1]):
                    config["results"][reqSite]["ClosedSameDay"] = str(int(config["results"][reqSite]["ClosedSameDay"]) + 1)
            ticketCount = ticketCount + 1
        more = jsonResults["list_info"]["has_more_rows"]
        if (more):
            resultsIndex = resultsIndex + 100
    return

def getClosedTickets(timeSpan, config):
    with open('queryClosed.json', 'r') as f:
        queryJson = json.load(f)
    queryJson["list_info"]["search_criteria"][0]["value"] = timeSpan[0]
    queryJson["list_info"]["search_criteria"][1]["value"] = timeSpan[1]
    baseUrl = config["url"] + '/api/v3/requests?TECHNICIAN_KEY=' + config["technicianKey"]
    more = True
    resultsIndex = 1
    ticketCount = 0
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
            if reqSite in config["results"]:
                config["results"][reqSite]["TotalClosed"] = str(int(config["results"][reqSite]["TotalClosed"]) + 1)
            else:
                config["UnknownSites"].append(reqSite)
                reqSite = "UNKNOWN"
                config["results"][reqSite]["TotalClosed"] = str(int(config["results"][reqSite]["TotalClosed"]) + 1)
            ticketCount = ticketCount + 1
        more = jsonResults["list_info"]["has_more_rows"]
        if (more):
            resultsIndex = resultsIndex + 100
    return

def getOutstandingClosed(timeSpan, config):
    with open('queryOutstandingClosed.json', 'r') as f:
        queryJson = json.load(f)
    queryJson["list_info"]["search_criteria"][0]["value"] = timeSpan[0]
    queryJson["list_info"]["search_criteria"][1]["value"] = timeSpan[1]
    baseUrl = config["url"] + '/api/v3/requests?TECHNICIAN_KEY=' + config["technicianKey"]
    more = True
    resultsIndex = 1
    ticketCount = 0
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
            if reqSite in config["results"]:
                config["results"][reqSite]["TotalOutstanding"] = str(int(config["results"][reqSite]["TotalOutstanding"]) + 1)
            else:
                config["UnknownSites"].append(reqSite)
                reqSite = "UNKNOWN"
                config["results"][reqSite]["TotalOutstanding"] = str(int(config["results"][reqSite]["TotalOutstanding"]) + 1)
            ticketAge = int(timeSpan[0]) - int(request["created_time"]["value"])
            if (ticketAge > SixWeeks):
                config["results"][reqSite]["Out6W"] = str(int(config["results"][reqSite]["Out6W"]) + 1)
            elif (ticketAge > FourWeeks):
                config["results"][reqSite]["Out4W"] = str(int(config["results"][reqSite]["Out4W"]) + 1)
            elif (ticketAge > TwoWeeks):
                config["results"][reqSite]["Out2W"] = str(int(config["results"][reqSite]["Out2W"]) + 1)
            elif (ticketAge > SevenDays):
                config["results"][reqSite]["Out7D"] = str(int(config["results"][reqSite]["Out7D"]) + 1)
            elif (ticketAge > FourDays):
                config["results"][reqSite]["Out4D"] = str(int(config["results"][reqSite]["Out4D"]) + 1)
            else:
                config["results"][reqSite]["OutL4D"] = str(int(config["results"][reqSite]["OutL4D"]) + 1)
            ticketCount = ticketCount + 1
        more = jsonResults["list_info"]["has_more_rows"]
        if (more):
            resultsIndex = resultsIndex + 100
    return

def getOutstandingOpen(timeSpan, config):
    with open('queryOutstandingOpen.json', 'r') as f:
        queryJson = json.load(f)
    queryJson["list_info"]["search_criteria"][0]["value"] = timeSpan[0]
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
                if reqSite in config["results"]:
                    config["results"][reqSite]["TotalOutstanding"] = str(int(config["results"][reqSite]["TotalOutstanding"]) + 1)
                else:
                    config["UnknownSites"].append(reqSite)
                    reqSite = "UNKNOWN"
                    config["results"][reqSite]["TotalOutstanding"] = str(int(config["results"][reqSite]["TotalOutstanding"]) + 1)
                ticketAge = int(timeSpan[0]) - int(request["created_time"]["value"])
                if (ticketAge > SixWeeks):
                    config["results"][reqSite]["Out6W"] = str(int(config["results"][reqSite]["Out6W"]) + 1)
                elif (ticketAge > FourWeeks):
                    config["results"][reqSite]["Out4W"] = str(int(config["results"][reqSite]["Out4W"]) + 1)
                elif (ticketAge > TwoWeeks):
                    config["results"][reqSite]["Out2W"] = str(int(config["results"][reqSite]["Out2W"]) + 1)
                elif (ticketAge > SevenDays):
                    config["results"][reqSite]["Out7D"] = str(int(config["results"][reqSite]["Out7D"]) + 1)
                elif (ticketAge > FourDays):
                    config["results"][reqSite]["Out4D"] = str(int(config["results"][reqSite]["Out4D"]) + 1)
                else:
                    config["results"][reqSite]["OutL4D"] = str(int(config["results"][reqSite]["OutL4D"]) + 1)
                ticketCount = ticketCount + 1
            more = jsonResults["list_info"]["has_more_rows"]
            if (more):
                resultsIndex = resultsIndex + 100
    return

def storeResults(dayDate, config):
    dayString = datetime.datetime.fromtimestamp(int(int(dayDate) / 1000)).strftime('%Y-%m-%d')
    headerLine = "date,site,opened,closed,outstanding,cosd,6w,4w,2w,7d,4d,l4d"+"\n"
    fileName = config["storageFolder"] + dayString + ".csv"
    if (LocalRun):
        print(dayString)
        if (len(config["UnknownSites"])):
            print(config["UnknownSites"])
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
    for k in sorted(config["results"]):
        outS = dayString
        outS = outS+","+str(k)
        outS = outS+","+config["results"][k]["TotalOpened"]
        outS = outS+","+config["results"][k]["TotalClosed"]
        outS = outS+","+config["results"][k]["TotalOutstanding"]
        outS = outS+","+config["results"][k]["ClosedSameDay"]
        outS = outS+","+config["results"][k]["Out6W"]
        outS = outS+","+config["results"][k]["Out4W"]
        outS = outS+","+config["results"][k]["Out2W"]
        outS = outS+","+config["results"][k]["Out7D"]
        outS = outS+","+config["results"][k]["Out4D"]
        outS = outS+","+config["results"][k]["OutL4D"]
        outS = outS+"\n"
        fH.write(outS)
    if (LocalStore):
        fH.close()
    else:
        blob.upload_from_file(fH,rewind=True,content_type='text/csv')
        fH.close()
    return

if __name__ == "__main__":
    datesToProcess = []
    datesToProcess.append(sys.argv[1])
    datesToProcess.append(sys.argv[2])
    if (len(sys.argv) > 3):
        if (sys.argv[3] == "local"):
            LocalStore = True
    LocalRun = True
    calcTimeManualInput(datesToProcess)
