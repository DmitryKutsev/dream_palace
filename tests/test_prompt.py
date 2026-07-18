import pytest
from fastapi import HTTPException

from dream_palace.agents.prompts.orchestrator import ORCHESTRATOR_INSTRUCTION
from dream_palace.interface.telegram.webhook import verify_webhook_secret


def test_orchestrator_prompt_contains_required_guardrails() -> None:
    prompt = ORCHESTRATOR_INSTRUCTION.lower()
    assert "choose dream" in prompt
    assert "telegram id" in prompt
    assert "authenticated telegram update" in prompt
    assert "chronological order" in prompt
    assert "recurring across dreams" in prompt
    assert "do not diagnose" in prompt


def test_webhook_secret_is_required_and_verified() -> None:
    verify_webhook_secret("expected", "expected")
    with pytest.raises(HTTPException) as error:
        verify_webhook_secret("expected", "wrong")
    assert error.value.status_code == 403
