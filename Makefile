.PHONY: help test check build demo lint doctor clean

help:
	@echo "Apex Developer Commands (Standard Library Only):"
	@echo "  make test           Run full 272-test unit suite"
	@echo "  make check          Verify zero external dependencies (pip = 0)"
	@echo "  make build          Compile standalone zipapp (dist/apex.pyz)"
	@echo "  make demo           Run 20-second binary search repair demo"
	@echo "  make lint           Run built-in zero-dependency AST linter"
	@echo "  make doctor         Run pre-flight launch health check"
	@echo "  make clean          Clean build caches and temporary artifacts"

test:
	python -m unittest discover -s tests

check:
	python tools/check_stdlib_only.py apex_council tools

build:
	python scripts/build_pyz.py

demo:
	python dist/apex.pyz cegis binary_search.py --tests-file tests.txt

lint:
	python -m apex_council.lint.rules . --format text

doctor:
	python tools/doctor.py

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache build dist .coverage htmlcov
