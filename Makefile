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
	cd functions/fetch-stats && pylint main.py && exit 0
	cd functions/fetch-open && pylint main.py && exit 0
	cd functions/fetch-closed && pylint main.py && exit 0
