HERE = $(shell pwd)
BIN = $(HERE)/bin
PYTHON = $(BIN)/python
INSTALL = $(BIN)/pip install --no-deps
BUILD_DIRS = bin build include lib lib64 man share
VIRTUALENV = virtualenv

.PHONY: all test build clean docs

all: build

$(PYTHON):
	$(VIRTUALENV) $(VTENV_OPTS) .

build: $(PYTHON)
	$(PYTHON) setup.py develop
	$(BIN)/pip install tox

clean:
	rm -rf $(BUILD_DIRS)

test: build
	$(BIN)/tox

docs:  build
	$(BIN)/tox -e docs

docker-build:
	sudo docker build -t condprof:latest .

docker-run:
	sudo docker run --name condprof --rm -it condprof:latest

docker-push:
	sudo docker login
	sudo docker run --name condprof -it condprof:latest ls 
	sudo docker commit -m "savepoint" -a "condprof" condprof tarekziade/condprof:latest
	sudo docker push tarekziade/condprof
