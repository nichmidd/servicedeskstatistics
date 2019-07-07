.PHONY: all
all: prebuild build test 

.PHONY: prebuild
prebuild:
	npm install -g serverless
	pip3 install pylint

.PHONY: build
build:
	pwd
	cd functions/fetch-stats
	sls plugin install -n serverless-google-cloudfunctions
	pip3 install -r requirements.txt
	cd ../fetch-open
	sls plugin install -n serverless-google-cloudfunctions
	pip3 install -r requirements.txt
	cd ../fetch-closed
	sls plugin install -n serverless-google-cloudfunctions
	pip3 install -r requirements.txt

.PHONY: test
test:
	cd ~/build/nichmidd/servicedeskstatistics
	cd functions/fetch-stats
	pylint .
