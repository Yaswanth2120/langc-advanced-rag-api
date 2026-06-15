PYTHON ?= python
IMAGE ?= docuintelai

.PHONY: install test run eval docker-build docker-run

install:
	$(PYTHON) -m pip install -r requirements.txt

test:
	$(PYTHON) -m unittest discover -s tests

run:
	$(PYTHON) -m uvicorn app.main:app --host 0.0.0.0 --port 8000

eval:
	$(PYTHON) -m evals.run_eval

docker-build:
	docker build -t $(IMAGE) .

docker-run:
	docker run $$([ -f .env ] && echo --env-file .env) -p 8000:8000 $(IMAGE)
