.PHONY: all
all: prebuild build test 

.PHONY: prebuild
prebuild:
	python3 -V
	pip3 -V
	node --version
	npm --version
	npm install -g serverless
	sls --version
	pip3 install pylint

.PHONY: build
build:
	cd ~/servicedeskstatistics/functions/fetch-stats
	sls install
	pip3 install -r requirements.txt

.PHONY: test
test:
	cd ~/servicedeskstatistics/functions/fetch-stats
	pylint .
