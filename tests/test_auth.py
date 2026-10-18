import time


def test_register_user(client):
    email = f"test_{time.time()}@example.com"
    response = client.post(
        "/api/auth/register",
        json={
            "name": "Test Farmer",
            "email": email,
            "password": "test123",
            "role": "farmer",
            "location": "Colombo",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == email
    assert data["role"] == "farmer"
    assert "user_id" in data


def test_register_duplicate_email(client):
    email = f"test_{time.time()}@example.com"
    payload = {
        "name": "Test Farmer",
        "email": email,
        "password": "test123",
        "role": "farmer",
        "location": "Colombo",
    }

    first = client.post("/api/auth/register", json=payload)
    assert first.status_code == 200

    second = client.post("/api/auth/register", json=payload)
    assert second.status_code == 400
    assert "already exists" in second.json()["detail"].lower()


def test_login_success(client):
    email = f"test_{time.time()}@example.com"
    password = "test123"

    client.post(
        "/api/auth/register",
        json={
            "name": "Test Farmer",
            "email": email,
            "password": password,
            "role": "farmer",
            "location": "Colombo",
        },
    )

    response = client.post(
        "/api/auth/login",
        data={"username": email, "password": password},
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == email


def test_login_invalid_credentials(client):
    email = f"test_{time.time()}@example.com"

    client.post(
        "/api/auth/register",
        json={
            "name": "Test Farmer",
            "email": email,
            "password": "test123",
            "role": "farmer",
            "location": "Colombo",
        },
    )

    response = client.post(
        "/api/auth/login",
        data={"username": email, "password": "wrongpass"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password"


def test_get_me_protected(auth_token, client):
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert "user_id" in data
    assert "email" in data
    assert data["role"] == "farmer"


def test_get_me_no_token(client):
    response = client.get("/api/auth/me")

    assert response.status_code == 401
