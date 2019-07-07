.PHONY: all
all: test

.PHONY: test
test:
	python3 -V
	pip3 -V
	node --version
	npm --version
	npm install -g serverless
	sls --version