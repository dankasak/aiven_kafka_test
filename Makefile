#
## template from http://www.itnotes.de/docker/development/tools/2014/08/31/speed-up-your-docker-workflow-with-a-makefile/
#
#
#include env_make
NS = tesla.duckdns.org
VERSION = latest

NAME = os_stats_through_kafka
INSTANCE = default

.PHONY: build push shell run start stop rm release

.ONESHELL:
build:
	docker build -t $(NS)/$(NAME):$(VERSION) .

push:
	docker push $(NS)/$(NAME):$(VERSION)

shell:
	docker run --rm --name $(NAME)-$(INSTANCE) --entrypoint '' -i -t $(PORTS) $(VOLUMES) $(ENV) $(NS)/$(NAME):$(VERSION) /bin/sh

run-test:
	docker run --rm --name $(NAME)-$(INSTANCE) $(PORTS) $(VOLUMES) $(ENV) $(NS)/$(NAME):$(VERSION) '--help'

rm:
	docker rm $(NAME)-$(INSTANCE)

release: build
	make push -e VERSION=$(VERSION)

default: build
