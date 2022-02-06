all: black isort mypy test

ctags:
	ctags -R `poetry env info --path` src
	ln -sf tags .tags

test:
	pytest tests

coverage:
	pytest \
		--cov=ovshell --cov=ovshell_xcsoar --cov=ovshell_core --cov=ovshell_fileman \
		--cov=ovshell_connman --cov=ovshell_google \
		--cov-report=html --cov-report=term \
		tests

.PHONY: black-check
black-check:
	black --check setup.py src tests

.PHONY: black
black:
	black setup.py src tests

isort:
	isort setup.py src tests

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
