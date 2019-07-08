# ManageEngine Servicedesk Plus Statistics Tool

[![Build Status](https://travis-ci.org/nichmidd/servicedeskstatistics.svg?branch=master)](https://travis-ci.org/nichmidd/servicedeskstatistics)

## Version

v0.2.2

## Overview

This project utilises the SDP APIv3 to fetch details on all open and closed tickets
and then stores them in Google BigQuery for analysis

> Side note - the v3 API on the OnPrem version is **NOT** as fully functional as the documentation says it should be

The project is broken into 4 parts:

- fetch-stats
- fetch-open
- fetch-closed
- import-stats

## Deployment

You first need to create a new serviceaccount if Google Cloud and give it access to
the BigQuery, Cloud Functions and Google Storage API's

The 4 functions are deployed using the serverless framework to GCF  
(well, actually only 3 are at this point, but that is going to change)  
The simplest way to deploy this project is to clone and use the Makefile

```bash
git clone https://github.com/nichmidd/servicedeskstatistics.git
cd servicedeskstatistics
cp functions/fetch-stats/config.json.example functions/fetch-stats/config.json
cp functions/fetch-open/config.json.example functions/fetch-open/config.json
cp functions/fetch-closed/config.json.example functions/fetch-closed/config.json
cp functions/import-stats/config.json.example functions/import-stats/config.json
```

Now:

- edit the config.json to suit your environment  
- edit each serverless.yml to suit your environment  
- run the Makefile

```bash
make
```

## WORK IN PROGRESS
