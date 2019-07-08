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

# Global Variables
ONEDAY = 86400 * 1000
FOURDAYS = (4 * ONEDAY)
SEVENDAYS = (7 * ONEDAY)
TWOWEEKS = (2 * SEVENDAYS)
FOURWEEKS = (4 * SEVENDAYS)
SIXWEEKS = (6 * SEVENDAYS)
LOCALRUN = False
LOCALSTORE = False

def fetchstats(event, context):
    '''Need to fix - just here to make PyLint happy'''
    message = base64.b64decode(event['data']).decode('utf-8')
    if message == "DAILY":
        config = loadconfig()
        timespan = calctime()
        getopentickets(timespan, config)
        getclosedtickets(timespan, config)
        getoutstandingclosed(timespan, config)
        getoutstandingopen(timespan, config)
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
    with open('config.json', 'r') as configfile:
        configjson = json.load(configfile)
        for resultskey in configjson["results"]:
            configjson["results"][resultskey]["TotalOpened"] = "0"
            configjson["results"][resultskey]["TotalClosed"] = "0"
            configjson["results"][resultskey]["Totaloutstanding"] = "0"
            configjson["results"][resultskey]["Out6W"] = "0"
            configjson["results"][resultskey]["Out4W"] = "0"
            configjson["results"][resultskey]["Out2W"] = "0"
            configjson["results"][resultskey]["Out7D"] = "0"
            configjson["results"][resultskey]["Out4D"] = "0"
            configjson["results"][resultskey]["OutL4D"] = "0"
            configjson["results"][resultskey]["ClosedSameDay"] = "0"
        return configjson

def calctime():
    '''Need to fix - just here to make PyLint happy'''
    local_tz = pytz.timezone('UTC')
    target_tz = pytz.timezone('Australia/Sydney')
    timeutc = datetime.datetime.utcnow()
    timenow = local_tz.localize(timeutc)
    timeaus = (target_tz.normalize(timenow)).strftime("%Y-%m-%d")
    # because this is running in google on utc we don't want to go a day ago
    # no, you are an idiot!!! read the code 2 lines up!
    basestartdate = (datetime.datetime.strptime(timeaus, "%Y-%m-%d") - datetime.timedelta(days=1))
    #baseStartDate = datetime.datetime.strptime(timeAus, "%Y-%m-%d")
    baseenddate = (datetime.datetime.strptime(timeaus, "%Y-%m-%d") - datetime.timedelta(days=1))
    tspan = []
    tspan.append(str(int((datetime.datetime.combine(basestartdate, datetime.time(0, 0, 0))).strftime('%s'))*1000))
    tspan.append(str((int((datetime.datetime.combine(baseenddate, datetime.time(23, 59, 59))).strftime('%s'))*1000)+999))
    return tspan

def calctimemanualinput(manualtimes):
    '''Need to fix - just here to make PyLint happy'''
    target_tz = pytz.timezone('Australia/Sydney')
    starttime = datetime.datetime.strptime(str(manualtimes[0]), "%Y-%m-%d")
    starttime = datetime.datetime.combine(starttime, datetime.time(0, 0, 0))
    starttime = target_tz.localize(starttime)
    fintime = datetime.datetime.strptime(str(manualtimes[1]), "%Y-%m-%d")
    fintime = datetime.datetime.combine(fintime, datetime.time(23, 59, 59))
    fintime = target_tz.localize(fintime)
    etime = "0"
    ftime = str((int(fintime.strftime('%s')) * 1000) + 999)
    while int(ftime) > int(etime):
        # we have to reset the config on each time or the numbers just keep growing
        config = loadconfig()
        stime = str(int(starttime.strftime('%s')) * 1000)
        endtime = datetime.datetime.combine(starttime, datetime.time(23, 59, 59))
        etime = str((int(endtime.strftime('%s'))*1000)+999)
        tspan = [stime, etime]
        getopentickets(tspan, config)
        getclosedtickets(tspan, config)
        getoutstandingclosed(tspan, config)
        getoutstandingopen(tspan, config)
        storeresults(tspan[0], config)
        starttime = starttime + datetime.timedelta(days=1)

def getopentickets(timespan, config):
    '''Need to fix - just here to make PyLint happy'''
    with open('queryOpened.json', 'r') as fileopen:
        queryjson = json.load(fileopen)
    queryjson["list_info"]["search_criteria"][0]["value"] = timespan[0]
    queryjson["list_info"]["search_criteria"][1]["value"] = timespan[1]
    baseurl = config["url"] + '/api/v3/requests?TECHNICIAN_KEY=' + config["technicianKey"]
    more = True
    resultsindex = 1
    ticketcount = 0
    while more:
        queryjson["list_info"]["start_index"] = resultsindex
        encodeduri = requote_uri(json.dumps(queryjson))
        queryurl = baseurl + '&input_data=' + encodeduri
        response = fetchdata(queryurl)
        jsonresults = response.json()
        for request in jsonresults["requests"]:
            #reqid = request["id"]
            # translate local priorities to standard ones
            #if (request["priority"]):
            #    if (request["priority"]["name"] in config["priorityTranslations"]):
            #        reqpri = config["priorityTranslations"][request["priority"]["name"]]["Priority"]
            #    else:
            #        reqpri = request["priority"]["name"]
            #else:
            #    reqpri = ""
            # translate extra sites to other ones
            if request["site"]:
                if request["site"]["name"] in config["siteTranslations"]:
                    reqsite = config["siteTranslations"][request["site"]["name"]]["Name"]
                else:
                    reqsite = request["site"]["name"]
            else:
                reqsite = "NONE"
            if reqsite in config["results"]:
                config["results"][reqsite]["TotalOpened"] = str(int(config["results"][reqsite]["TotalOpened"]) + 1)
            else:
                config["UnknownSites"].append(reqsite)
                reqsite = "UNKNOWN"
                config["results"][reqsite]["TotalOpened"] = str(int(config["results"][reqsite]["TotalOpened"]) + 1)
            if request["resolved_time"]:
                if request["resolved_time"]["value"] < timespan[1]:
                    config["results"][reqsite]["ClosedSameDay"] = str(int(config["results"][reqsite]["ClosedSameDay"]) + 1)
            ticketcount = ticketcount + 1
        more = jsonresults["list_info"]["has_more_rows"]
        if more:
            resultsindex = resultsindex + 100

def getclosedtickets(timespan, config):
    '''Need to fix - just here to make PyLint happy'''
    with open('queryClosed.json', 'r') as fileclosed:
        queryjson = json.load(fileclosed)
    queryjson["list_info"]["search_criteria"][0]["value"] = timespan[0]
    queryjson["list_info"]["search_criteria"][1]["value"] = timespan[1]
    baseurl = config["url"] + '/api/v3/requests?TECHNICIAN_KEY=' + config["technicianKey"]
    more = True
    resultsindex = 1
    ticketcount = 0
    while more:
        queryjson["list_info"]["start_index"] = resultsindex
        encodeduri = requote_uri(json.dumps(queryjson))
        queryurl = baseurl + '&input_data=' + encodeduri
        response = fetchdata(queryurl)
        jsonresults = response.json()
        for request in jsonresults["requests"]:
            #reqid = request["id"]
            #if (request["priority"]):
            #    if (request["priority"]["name"] in config["priorityTranslations"]):
            #        reqpri = config["priorityTranslations"][request["priority"]["name"]]["Priority"]
            #    else:
            #        reqpri = request["priority"]["name"]
            #else:
            #    reqpri = ""
            if request["site"]:
                if request["site"]["name"] in config["siteTranslations"]:
                    reqsite = config["siteTranslations"][request["site"]["name"]]["Name"]
                else:
                    reqsite = request["site"]["name"]
            else:
                reqsite = "NONE"
            if reqsite in config["results"]:
                config["results"][reqsite]["TotalClosed"] = str(int(config["results"][reqsite]["TotalClosed"]) + 1)
            else:
                config["UnknownSites"].append(reqsite)
                reqsite = "UNKNOWN"
                config["results"][reqsite]["TotalClosed"] = str(int(config["results"][reqsite]["TotalClosed"]) + 1)
            ticketcount = ticketcount + 1
        more = jsonresults["list_info"]["has_more_rows"]
        if more:
            resultsindex = resultsindex + 100

def getoutstandingclosed(timespan, config):
    '''Need to fix - just here to make PyLint happy'''
    with open('queryoutstandingClosed.json', 'r') as filequery:
        queryjson = json.load(filequery)
    queryjson["list_info"]["search_criteria"][0]["value"] = timespan[0]
    queryjson["list_info"]["search_criteria"][1]["value"] = timespan[1]
    baseurl = config["url"] + '/api/v3/requests?TECHNICIAN_KEY=' + config["technicianKey"]
    more = True
    resultsindex = 1
    ticketcount = 0
    while more:
        queryjson["list_info"]["start_index"] = resultsindex
        encodeduri = requote_uri(json.dumps(queryjson))
        queryurl = baseurl + '&input_data=' + encodeduri
        response = fetchdata(queryurl)
        jsonresults = response.json()
        for request in jsonresults["requests"]:
            #reqid = request["id"]
            #if (request["priority"]):
            #    if (request["priority"]["name"] in config["priorityTranslations"]):
            #        reqpri = config["priorityTranslations"][request["priority"]["name"]]["Priority"]
            #    else:
            #        reqpri = request["priority"]["name"]
            #else:
            #    reqpri = ""
            if request["site"]:
                if request["site"]["name"] in config["siteTranslations"]:
                    reqsite = config["siteTranslations"][request["site"]["name"]]["Name"]
                else:
                    reqsite = request["site"]["name"]
            else:
                reqsite = "NONE"
            if reqsite in config["results"]:
                config["results"][reqsite]["Totaloutstanding"] = str(int(config["results"][reqsite]["Totaloutstanding"]) + 1)
            else:
                config["UnknownSites"].append(reqsite)
                reqsite = "UNKNOWN"
                config["results"][reqsite]["Totaloutstanding"] = str(int(config["results"][reqsite]["Totaloutstanding"]) + 1)
            ticketage = int(timespan[0]) - int(request["created_time"]["value"])
            if ticketage > SIXWEEKS:
                config["results"][reqsite]["Out6W"] = str(int(config["results"][reqsite]["Out6W"]) + 1)
            elif ticketage > FOURWEEKS:
                config["results"][reqsite]["Out4W"] = str(int(config["results"][reqsite]["Out4W"]) + 1)
            elif ticketage > TWOWEEKS:
                config["results"][reqsite]["Out2W"] = str(int(config["results"][reqsite]["Out2W"]) + 1)
            elif ticketage > SEVENDAYS:
                config["results"][reqsite]["Out7D"] = str(int(config["results"][reqsite]["Out7D"]) + 1)
            elif ticketage > FOURDAYS:
                config["results"][reqsite]["Out4D"] = str(int(config["results"][reqsite]["Out4D"]) + 1)
            else:
                config["results"][reqsite]["OutL4D"] = str(int(config["results"][reqsite]["OutL4D"]) + 1)
            ticketcount = ticketcount + 1
        more = jsonresults["list_info"]["has_more_rows"]
        if more:
            resultsindex = resultsindex + 100

def getoutstandingopen(timespan, config):
    '''Need to fix - just here to make PyLint happy'''
    with open('queryoutstandingOpen.json', 'r') as fileopenout:
        queryjson = json.load(fileopenout)
    queryjson["list_info"]["search_criteria"][0]["value"] = timespan[0]
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
                #reqid = request["id"]
                #if (request["priority"]):
                #    if (request["priority"]["name"] in config["priorityTranslations"]):
                #        reqpri = config["priorityTranslations"][request["priority"]["name"]]["Priority"]
                #    else:
                #        reqpri = request["priority"]["name"]
                #else:
                #    reqpri = ""
                if request["site"]:
                    if request["site"]["name"] in config["siteTranslations"]:
                        reqsite = config["siteTranslations"][request["site"]["name"]]["Name"]
                    else:
                        reqsite = request["site"]["name"]
                else:
                    reqsite = "NONE"
                if reqsite in config["results"]:
                    config["results"][reqsite]["Totaloutstanding"] = str(int(config["results"][reqsite]["Totaloutstanding"]) + 1)
                else:
                    config["UnknownSites"].append(reqsite)
                    reqsite = "UNKNOWN"
                    config["results"][reqsite]["Totaloutstanding"] = str(int(config["results"][reqsite]["Totaloutstanding"]) + 1)
                ticketage = int(timespan[0]) - int(request["created_time"]["value"])
                if ticketage > SIXWEEKS:
                    config["results"][reqsite]["Out6W"] = str(int(config["results"][reqsite]["Out6W"]) + 1)
                elif ticketage > FOURWEEKS:
                    config["results"][reqsite]["Out4W"] = str(int(config["results"][reqsite]["Out4W"]) + 1)
                elif ticketage > TWOWEEKS:
                    config["results"][reqsite]["Out2W"] = str(int(config["results"][reqsite]["Out2W"]) + 1)
                elif ticketage > SEVENDAYS:
                    config["results"][reqsite]["Out7D"] = str(int(config["results"][reqsite]["Out7D"]) + 1)
                elif ticketage > FOURDAYS:
                    config["results"][reqsite]["Out4D"] = str(int(config["results"][reqsite]["Out4D"]) + 1)
                else:
                    config["results"][reqsite]["OutL4D"] = str(int(config["results"][reqsite]["OutL4D"]) + 1)
                ticketcount = ticketcount + 1
            more = jsonresults["list_info"]["has_more_rows"]
            if more:
                resultsindex = resultsindex + 100

def storeresults(daydate, config):
    '''Need to fix - just here to make PyLint happy'''
    daystring = datetime.datetime.fromtimestamp(int(int(daydate) / 1000)).strftime('%Y-%m-%d')
    headerline = "date,site,opened,closed,outstanding,cosd,6w,4w,2w,7d,4d,l4d"+"\n"
    filename = config["storageFolder"] + daystring + ".csv"
    if LOCALRUN:
        print(daystring)
        if config["UnknownSites"]:
            print(config["UnknownSites"])
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
    for resultskey in sorted(config["results"]):
        outstr = daystring
        outstr = outstr+","+str(resultskey)
        outstr = outstr+","+config["results"][resultskey]["TotalOpened"]
        outstr = outstr+","+config["results"][resultskey]["TotalClosed"]
        outstr = outstr+","+config["results"][resultskey]["Totaloutstanding"]
        outstr = outstr+","+config["results"][resultskey]["ClosedSameDay"]
        outstr = outstr+","+config["results"][resultskey]["Out6W"]
        outstr = outstr+","+config["results"][resultskey]["Out4W"]
        outstr = outstr+","+config["results"][resultskey]["Out2W"]
        outstr = outstr+","+config["results"][resultskey]["Out7D"]
        outstr = outstr+","+config["results"][resultskey]["Out4D"]
        outstr = outstr+","+config["results"][resultskey]["OutL4D"]
        outstr = outstr+"\n"
        filehandle.write(outstr)
    if LOCALSTORE:
        filehandle.close()
    else:
        blob.upload_from_file(filehandle, rewind=True, content_type='text/csv')
        filehandle.close()

if __name__ == "__main__":
    DATESTOPROCESS = []
    DATESTOPROCESS.append(sys.argv[1])
    DATESTOPROCESS.append(sys.argv[2])
    if len(sys.argv) > 3:
        if sys.argv[3] == "local":
            LOCALSTORE = True
    LOCALRUN = True
    calctimemanualinput(DATESTOPROCESS)
