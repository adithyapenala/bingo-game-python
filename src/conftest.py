"""
This module configures test environment for app test in /test folder
"""

import pytest
from fastapi import FastAPI
from main import app as fastapi_app

@pytest.fixture()
def app():
    fastapi_app.config.update({
        "TESTING": True,
        "DATABASE_URI": "sqlite:///:memory:",  # use in-memory DB for tests
    })
    yield fastapi_app

@pytest.fixture()
def client(app: FastAPI):
    return app.test_client() # TODO: fix

@pytest.fixture()
def runner(app: FastAPI):
    return app.test_cli_runner() # TODO: fix