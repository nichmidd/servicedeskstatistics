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
	cd functions/import-stats && sls plugin install -n serverless-google-cloudfunctions && pip3 install -r requirements.txt

.PHONY: test
test:
	cd functions/fetch-stats && pylint -ry main.py
	cd functions/fetch-open && pylint -ry main.py
	cd functions/fetch-closed && pylint -ry main.py
	cd functions/import-stats && pylint -ry main.py

.PHONY: deploy
deploy:
	cd functions/fetch-stats && sls deploy
	cd functions/fetch-open && sls deploy
	cd functions/fetch-closed && sls deploy
	cd functions/import-stats && sls deploy

.PHONY: destroy
destroy:
	cd functions/fetch-stats && sls remove
	cd functions/fetch-open && sls remove
	cd functions/fetch-closed && sls remove
	cd functions/import-stats && sls remove
