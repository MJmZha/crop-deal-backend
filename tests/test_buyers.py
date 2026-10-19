import time


def register_and_login(client, *, role, name="Test User"):
    email = f"{role}_{int(time.time() * 1000)}@example.com"
    password = "test123"

    register_response = client.post(
        "/api/auth/register",
        json={
            "name": name,
            "email": email,
            "password": password,
            "role": role,
            "location": "Colombo",
        },
    )
    assert register_response.status_code == 200, register_response.text

    login_response = client.post(
        "/api/auth/login",
        data={"username": email, "password": password},
    )
    assert login_response.status_code == 200, login_response.text

    return login_response.json()["access_token"], email


def make_requirement_payload(**overrides):
    payload = {
        "crop_name": "Tomato",
        "quantity_kg": 200,
        "quality_grade": "Any",
        "max_price_per_kg": 200,
        "location": "Colombo",
        "deadline": "2026-11-01",
        "notes": "Need fresh tomatoes for a bulk order",
    }
    payload.update(overrides)
    return payload


def create_requirement(client, token, **overrides):
    response = client.post(
        "/api/buyers/requirements",
        json=make_requirement_payload(**overrides),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_create_buyer_requirement(client):
    token, _ = register_and_login(client, role="buyer", name="Buyer User")

    response = client.post(
        "/api/buyers/requirements",
        json=make_requirement_payload(),
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["crop_name"] == "Tomato"
    assert data["location"] == "Colombo"
    assert "requirement_id" in data


def test_create_requirement_forbidden(client):
    token, _ = register_and_login(client, role="farmer", name="Farmer User")

    response = client.post(
        "/api/buyers/requirements",
        json=make_requirement_payload(),
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Only buyers can create purchase requirements."


def test_list_buyer_requirements(client):
    token, _ = register_and_login(client, role="buyer", name="List Buyer")
    created = create_requirement(client, token)

    response = client.get(
        "/api/buyers/requirements",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert any(item["requirement_id"] == created["requirement_id"] for item in data)


def test_get_requirement_by_id(client):
    token, _ = register_and_login(client, role="buyer", name="Single Buyer")
    created = create_requirement(client, token)

    response = client.get(
        f"/api/buyers/requirements/{created['requirement_id']}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["requirement_id"] == created["requirement_id"]
    assert data["crop_name"] == "Tomato"


def test_find_matches_perfect_score(client):
    token, _ = register_and_login(client, role="buyer", name="Match Buyer")
    requirement = create_requirement(client, token, crop_name="Tomato", quantity_kg=200, max_price_per_kg=200, location="Colombo")

    listing_response = client.post(
        "/crop-details/save",
        json={
            "crop_name": "Tomato",
            "quantity_kg": 300,
            "expected_price_per_kg": 180,
            "location": "Colombo",
            "farmer": "Farmer Test",
        },
    )
    assert listing_response.status_code == 200, listing_response.text

    response = client.post(
        "/api/matching/find",
        json={"requirement_id": requirement["requirement_id"]},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total_matches"] >= 1
    assert any(match["match_score"] == 100 for match in data["matches"])


def test_find_matches_no_match(client):
    token, _ = register_and_login(client, role="buyer", name="No Match Buyer")
    requirement = create_requirement(client, token, crop_name="Paddy", quantity_kg=150, max_price_per_kg=180, location="Colombo")

    client.post(
        "/crop-details/save",
        json={
            "crop_name": "Tomato",
            "quantity_kg": 300,
            "expected_price_per_kg": 100,
            "location": "Colombo",
            "farmer": "Farmer Test",
        },
    )

    response = client.post(
        "/api/matching/find",
        json={"requirement_id": requirement["requirement_id"]},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total_matches"] == 0


def test_matching_requires_auth(client):
    response = client.post(
        "/api/matching/find",
        json={"requirement_id": "test-requirement-id"},
    )

    assert response.status_code == 401
