# tests/test_agents.py — Unit tests for agents with mock LLM
import pytest
from unittest.mock import patch, AsyncMock
from tests.conftest import MockLLM


@pytest.mark.asyncio
async def test_ceo_agent_parses_json():
    mock = MockLLM('{"short_term_strategy":"Build MVP fast","long_term_vision":"Scale to 1M users","departments":["backend","frontend","security"]}')
    with patch("backend.agents.ceo_agent.llm", mock):
        from backend.agents.ceo_agent import ceo_agent
        result = await ceo_agent("Build a todo app")
        assert "short_term_strategy" in result
        assert "departments" in result
        assert "backend" in result["departments"]


@pytest.mark.asyncio
async def test_ceo_agent_fallback():
    mock = MockLLM("This is not valid JSON at all")
    with patch("backend.agents.ceo_agent.llm", mock):
        from backend.agents.ceo_agent import ceo_agent
        result = await ceo_agent("Build something")
        assert "departments" in result
        assert len(result["departments"]) > 0


@pytest.mark.asyncio
async def test_backend_agent_returns_department():
    mock = MockLLM('{"department":"Backend Engineering","architecture":"FastAPI","database":{"primary":"PostgreSQL"},"api_design":{"style":"REST"},"services":["UserService"],"key_recommendations":["Use async"]}')
    with patch("backend.agents.backend_agent.llm", mock):
        from backend.agents.backend_agent import backend_agent
        result = await backend_agent("Build a booking system", "Build fast", "")
        assert result["department"] == "Backend Engineering"


@pytest.mark.asyncio
async def test_security_agent_returns_department():
    mock = MockLLM('{"department":"Security","threat_model":{"top_threats":["XSS"]},"authentication":{"strategy":"JWT"},"encryption":{"in_transit":"TLS"},"risk_mitigation":["Rate limit"],"compliance":["OWASP"]}')
    with patch("backend.agents.security_agent.llm", mock):
        from backend.agents.security_agent import security_agent
        result = await security_agent("Build a banking app", "", "")
        assert result["department"] == "Security Engineering"


@pytest.mark.asyncio
async def test_hr_agent_returns_report():
    mock = MockLLM("Team Structure:\n- 1 Tech Lead\n- 2 Backend Engineers\nHiring Timeline:\nMonth 1: Core team")
    with patch("backend.agents.hr_agent.llm", mock):
        from backend.agents.hr_agent import hr_agent
        result = await hr_agent("Build a SaaS platform", "", "")
        assert result["department"] == "Human Resources"
        assert result["status"] == "success"
