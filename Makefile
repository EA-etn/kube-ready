.PHONY: install lint test check docker

install:        ## dev install
	python -m pip install -e ".[dev]"

lint:
	ruff check . && ruff format --check . && mypy --strict src

test:
	pytest

check:          ## run the tool on the examples
	kube-ready check examples/good --fail-on info
	-kube-ready check examples/bad --verbose

docker:
	docker build -t kube-ready:dev .
	docker run --rm -v "$$PWD/examples:/work:ro" kube-ready:dev check bad --verbose
