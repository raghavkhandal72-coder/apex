.PHONY: help install test benchmark serve diff redteam dlp-test audit-verify docker-build clean

help:
	@echo "Apex-Council Enterprise Developer Commands:"
	@echo "  make install        Install package in editable mode"
	@echo "  make test           Run the full 15-test unit suite"
	@echo "  make benchmark      Run the 5-challenge SWE Tournament"
	@echo "  make serve          Launch local Cyberpunk Web Studio (port 8080)"
	@echo "  make diff           Run pre-commit Git diff audit"
	@echo "  make audit-verify   Verify SOC2 cryptographic audit trail"
	@echo "  make docker-build   Build Docker container image"
	@echo "  make clean          Clean temporary caches and test artifacts"

install:
	pip install -e .

test:
	python -m unittest discover -s tests

benchmark:
	python -m apex_council benchmark

serve:
	python -m apex_council serve --port 8080

diff:
	python -m apex_council diff

audit-verify:
	python -m apex_council audit-verify

docker-build:
	docker build -t apex-council:latest .

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache build dist .coverage htmlcov
