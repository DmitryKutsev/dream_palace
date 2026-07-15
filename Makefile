.PHONY: install lint format test check run terraform-fmt
install:
	uv sync --all-groups
lint:
	uv run ruff check .
format:
	uv run ruff format .
test:
	uv run pytest
check: lint test terraform-fmt
run:
	uv run uvicorn dream_palace.webhook:app --reload --port 8080
terraform-fmt:
	terraform fmt -check -recursive infra
