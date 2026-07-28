# tests/test_intent_detector.py — Tests for 3-mode intent detection
import pytest
from backend.core.intent_detector import detect_intent


class TestBuildIntent:
    def test_build_me_phrase(self):
        assert detect_intent("Build me a todo app") == "build"

    def test_create_app(self):
        assert detect_intent("Create a hospital booking system") == "build"

    def test_deploy_phrase(self):
        assert detect_intent("Deploy a REST API for my blog") == "build"

    def test_make_application(self):
        assert detect_intent("Make a simple mobile gaming application") == "build"

    def test_generate_app(self):
        assert detect_intent("Generate a dashboard for inventory management") == "build"


class TestAnalyzeIntent:
    def test_analyze_phrase(self):
        assert detect_intent("Analyze my business plan for a SaaS product") == "analyze"

    def test_security_audit(self):
        assert detect_intent("Perform a security audit of my application") == "analyze"

    def test_create_plan(self):
        assert detect_intent("Give me a plan for scaling our infrastructure") == "analyze"

    def test_recommend_stack(self):
        assert detect_intent("What tech stack do you recommend for this?") == "analyze"


class TestChatIntent:
    def test_greeting(self):
        assert detect_intent("Hello") == "chat"

    def test_short_message(self):
        assert detect_intent("Hi VIA") == "chat"

    def test_question(self):
        assert detect_intent("What is Python used for?") == "chat"

    def test_thanks(self):
        assert detect_intent("Thanks!") == "chat"


class TestEdgeCases:
    def test_empty_like(self):
        assert detect_intent("ok cool") == "chat"

    def test_mixed_signals_build_wins(self):
        result = detect_intent("Build a project management tool with API backend and frontend dashboard")
        assert result == "build"
