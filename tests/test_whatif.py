

def test_whatif_improvement(client, auth_token):
    assessment = client.post(
        "/assess/full",
        json={
            "crop_name": "Rice",
            "quantity_kg": 500,
            "offered_price_per_kg": 60,
            "market_price_per_kg": 120,
            "buyer_verified": False,
            "payment_method": "cash_on_delivery",
            "distance_km": 60,
        },
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assessment_id = assessment.json()["assessment_id"]

    response = client.post(
        "/simulate/whatif",
        json={
            "assessment_id": assessment_id,
            "changes": {
                "offered_price_per_kg": 140,
                "payment_method": "advance",
                "buyer_verified": True,
            },
        },
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["is_simulated"] is True
    assert data["label"] == "⚠️ SIMULATED SCENARIO — not a real deal"
    assert "risk_score_change" in data
    assert "recommendation_changed" in data


def test_whatif_extreme_improvement(client, auth_token):
    assessment = client.post(
        "/assess/full",
        json={
            "crop_name": "Rice",
            "quantity_kg": 500,
            "offered_price_per_kg": 30,
            "market_price_per_kg": 120,
            "buyer_verified": False,
            "payment_method": "cash_on_delivery",
            "distance_km": 90,
        },
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assessment_id = assessment.json()["assessment_id"]

    response = client.post(
        "/simulate/whatif",
        json={
            "assessment_id": assessment_id,
            "changes": {
                "offered_price_per_kg": 200,
                "payment_method": "advance",
                "buyer_verified": True,
                "distance_km": 5,
            },
        },
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["risk_score_change"] < 0
    assert data["is_simulated"] is True


def test_whatif_requires_auth(client):
    response = client.post(
        "/simulate/whatif",
        json={
            "assessment_id": "fake-assessment-id",
            "changes": {"offered_price_per_kg": 200},
        },
    )

    assert response.status_code == 401
