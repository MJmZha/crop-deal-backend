import time


def test_full_assessment_high_risk(client, auth_token):
    response = client.post(
        "/assess/full",
        json={
            "crop_name": "Rice",
            "quantity_kg": 1000,
            "offered_price_per_kg": 40,
            "market_price_per_kg": 120,
            "buyer_verified": False,
            "payment_method": "cash_on_delivery",
            "distance_km": 80,
        },
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["risk_score"] >= 70
    assert data["risk_level"] in {"High", "Medium"}
    assert data["recommendation"] in {"REJECT", "NEGOTIATE"}


def test_full_assessment_low_risk(client, auth_token):
    response = client.post(
        "/assess/full",
        json={
            "crop_name": "Rice",
            "quantity_kg": 1000,
            "offered_price_per_kg": 160,
            "market_price_per_kg": 120,
            "buyer_verified": True,
            "payment_method": "advance",
            "distance_km": 10,
        },
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["risk_score"] < 35
    assert data["risk_level"] == "Low"
    assert data["recommendation"] == "ACCEPT"


def test_full_assessment_requires_auth(client):
    response = client.post(
        "/assess/full",
        json={
            "crop_name": "Rice",
            "quantity_kg": 100,
            "offered_price_per_kg": 50,
            "market_price_per_kg": 100,
            "buyer_verified": True,
            "payment_method": "advance",
            "distance_km": 10,
        },
    )

    assert response.status_code == 401
