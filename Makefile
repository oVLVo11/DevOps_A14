# E4 一键命令（BuildChecker）。每次执行 make 生成新的 work/<时间>/，不覆盖旧记录。
SHELL      := /bin/bash
SERVICE    := buildchecker
STUDENT_ID := $(or $(shell git config user.name 2>/dev/null),local)
IMAGE      := e4-$(SERVICE):$(STUDENT_ID)
STAMP      := $(shell date +%Y%m%d-%H%M%S)
RUN        := work/$(STAMP)
TIMEOUT    := 600
BASE_IMAGE := $(shell sed -n 's/^ARG BASE_IMAGE=//p' services/$(SERVICE)/Dockerfile)
export STUDENT_ID
COMPOSE    := docker compose -p e4-$(SERVICE)-$(shell echo $(STUDENT_ID) | tr A-Z a-z)

.PHONY: all doctor build test smoke scan shell lock clean

all: doctor build test smoke scan
	@echo "证据目录：$(RUN)"

$(RUN):
	@mkdir -p $(RUN)

.env:
	cp .env.example .env && chmod 600 .env
	@echo "已从 .env.example 生成 .env（权限 600），需要时再填写。"

doctor: | $(RUN)
	python3 scripts/doctor.py --out $(RUN)/env.json

build: .env | $(RUN)
	$(COMPOSE) build --progress=plain 2>&1 | tee $(RUN)/build.log; test $${PIPESTATUS[0]} -eq 0
	docker image inspect $(IMAGE) --format '{"image":"$(IMAGE)","id":"{{.Id}}","arch":"{{.Architecture}}","created":"{{.Created}}"}' | tee $(RUN)/image.json
	$(COMPOSE) run --rm --no-deps $(SERVICE) cat /opt/toolchain.lock | tee $(RUN)/toolchain.lock

test: .env | $(RUN)
	timeout $(TIMEOUT) $(COMPOSE) run --rm -T --interactive=false $(SERVICE) pytest 2>&1 | tee $(RUN)/test.log; test $${PIPESTATUS[0]} -eq 0

smoke: .env | $(RUN)
	timeout $(TIMEOUT) $(COMPOSE) run --rm -T --interactive=false $(SERVICE) python3 -m $(SERVICE) smoke | tee $(RUN)/smoke.json; test $${PIPESTATUS[0]} -eq 0

scan: | $(RUN)
	python3 scripts/secret_scan.py . --history --image $(IMAGE) | tee $(RUN)/secret-scan.txt; test $${PIPESTATUS[0]} -eq 0

shell: .env
	@mkdir -p work
	$(COMPOSE) run --rm --user $$(id -u):$$(id -g) -e HOME=/tmp -v "$$PWD/work:/app/work" $(SERVICE) bash

lock:
	docker run --rm --user $$(id -u):$$(id -g) -e HOME=/tmp -v "$$PWD":/src -w /src $(BASE_IMAGE) sh -c '\
	  python3 -m venv /tmp/v && /tmp/v/bin/pip install -q uv==0.12.19 && \
	  /tmp/v/bin/uv pip compile requirements-dev.in --generate-hashes --python-version 3.13 --python-platform linux -o requirements-dev.lock'

clean:
	-docker image rm $(IMAGE)
