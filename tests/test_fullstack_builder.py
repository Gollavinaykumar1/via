# tests/test_fullstack_builder.py — Tests for app type detection and file generation
import pytest
from backend.core.fullstack_builder import detect_app_type, generate_backend_files


class TestDetectAppType:
    def test_frontend_only_landing(self):
        assert detect_app_type("Build a landing page for my startup") == "frontend"

    def test_frontend_portfolio(self):
        assert detect_app_type("Create a portfolio showcase website") == "frontend"

    def test_fullstack_with_api(self):
        assert detect_app_type("Build a quiz app with API and scoring") == "fullstack"

    def test_fullstack_game(self):
        assert detect_app_type("Create a game leaderboard tracker") == "fullstack"

    def test_fullstack_db_with_login(self):
        assert detect_app_type("Build an app with user login and data storage") == "fullstack_db"

    def test_fullstack_db_crud(self):
        assert detect_app_type("Create a CRUD application for managing users") == "fullstack_db"

    def test_fullstack_db_postgresql(self):
        assert detect_app_type("Build a system with PostgreSQL database") == "fullstack_db"


class TestGenerateBackendFiles:
    def test_frontend_returns_empty(self):
        files = generate_backend_files("landing page", "frontend")
        assert files == {}

    def test_fullstack_has_main_py(self):
        files = generate_backend_files("Build a quiz app", "fullstack")
        assert "main.py" in files
        assert "requirements.txt" in files
        assert "render.yaml" in files

    def test_fullstack_db_has_models(self):
        files = generate_backend_files("Build a user management system", "fullstack_db")
        assert "database.py" in files
        assert "models.py" in files
        assert "main.py" in files

    def test_main_py_has_fastapi(self):
        files = generate_backend_files("Build a todo app", "fullstack")
        assert "FastAPI" in files["main.py"]
        assert "uvicorn" in files["main.py"]

    def test_requirements_has_fastapi(self):
        files = generate_backend_files("Build a blog", "fullstack")
        assert "fastapi" in files["requirements.txt"]

    def test_gitignore_generated(self):
        files = generate_backend_files("Build an app", "fullstack")
        assert ".gitignore" in files
        assert "__pycache__" in files[".gitignore"]
