# tests/conftest.py — Shared fixtures for VIA test suite
import pytest
from unittest.mock import AsyncMock, patch, MagicMock


class MockLLM:
    """Mock LLM provider that returns predictable responses."""
    def __init__(self, response=""):
        self._response = response

    def generate(self, prompt: str) -> str:
        return self._response

    async def agenerate(self, prompt: str) -> str:
        return self._response


@pytest.fixture
def mock_llm():
    """Returns a MockLLM instance with a default CEO-style JSON response."""
    return MockLLM(response='{"short_term_strategy":"Build MVP","long_term_vision":"Scale globally","departments":["backend","frontend"]}')


@pytest.fixture
def mock_llm_patched(mock_llm):
    """Patches the global llm instance in llm_provider."""
    with patch("backend.core.llm_provider.llm", mock_llm):
        yield mock_llm


@pytest.fixture
def sample_task():
    return "Build a hospital appointment booking system with departments and doctor profiles"


@pytest.fixture
def sample_history():
    return [
        {"task": "Build a todo app", "result": {"ceo_strategy": {"short_term_strategy": "CRUD app"}, "selected_departments": ["backend", "frontend"]}},
    ]
