# tests/conftest.py
import os
import sys
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import config
config.DB_PATH = os.path.join(os.path.dirname(__file__), "test_finance_hub.db")

from app import create_app

@pytest.fixture
def app():
    application = create_app(testing=True)
    yield application

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture(autouse=True)
def clean_db():
    if os.path.exists(config.DB_PATH):
        os.remove(config.DB_PATH)
    from database import init_db
    init_db()
    yield
    if os.path.exists(config.DB_PATH):
        os.remove(config.DB_PATH)
