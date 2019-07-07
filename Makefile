.PHONY: all
all: prebuild build test 

.PHONY: prebuild
prebuild:
	npm install -g serverless
	pip3 install pylint

.PHONY: build
build:
	cd functions/fetch-stats && sls plugin install -n serverless-google-cloudfunctions && pip3 install -r requirements.txt
	cd functions/fetch-open && sls plugin install -n serverless-google-cloudfunctions && pip3 install -r requirements.txt
	cd functions/fetch-closed && sls plugin install -n serverless-google-cloudfunctions && pip3 install -r requirements.txt

.PHONY: test
test:
	ls functions/fetch-stats/config.json
	ls functions/fetch-open/config.json
	ls functions/fetch-closed/config.json
	ls functions/import-stats/config.json
	ls ~/.gcloud/
	#cd functions/fetch-stats && pylint main.py
	#cd functions/fetch-open && pylint main.py
	#cd functions/fetch-closed && pylint main.py
