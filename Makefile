.PHONY: install lint format test check run agent-run terraform-fmt
install:
	uv sync --group dev
lint:
	uv run ruff check .
format:
	uv run ruff format .
test:
	uv run pytest
check: lint test terraform-fmt
run:
	uv run uvicorn dream_palace.app:app --reload --port 8080
agent-run:
	azd ai agent run
terraform-fmt:
	terraform fmt -check -recursive infra
