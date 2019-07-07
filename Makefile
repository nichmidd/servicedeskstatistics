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
	sls install
	pip3 install -r requirements.txt

.PHONY: test
test:
	pylint .
