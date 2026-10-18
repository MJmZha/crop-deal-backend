import time

import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_token(client):
    email = f"test_{time.time()}@example.com"
    password = "test123"

    register_response = client.post(
        "/api/auth/register",
        json={
            "name": "Test User",
            "email": email,
            "password": password,
            "role": "farmer",
            "location": "Colombo",
        },
    )
    assert register_response.status_code == 200, register_response.text

    login_response = client.post(
        "/api/auth/login",
        data={"username": email, "password": password},
    )
    assert login_response.status_code == 200, login_response.text

    return login_response.json()["access_token"]
