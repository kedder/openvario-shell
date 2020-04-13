all: test

ctags:
	ctags -R `pipenv --venv` src
	ln -sf tags .tags

test:
	pytest tests

coverage:
	pytest --cov=ovshell --cov-report=html --cov-report=term tests

.PHONY: black-check
black-check:
	black --check setup.py src tests

.PHONY: black
black:
	black setup.py src tests

.PHONY: mypy
mypy:
	mypy src tests

.PHONY: mypy-report
mypy-report:
	mypy src tests \
		--html-report mypy-reports/html \
		--txt-report mypy-reports/txt
	@cat mypy-reports/txt/index.txt
	@echo "HTML report generated in mypy-reports/html/index.html"

.PHONY: reset-rootfs
reset-rootfs:
	mkdir -p var
	rm -rf var/rootfs
	cp -r rootfs-ref var/rootfs
