# API Documentation

## Base URL

```text
http://127.0.0.1:8000
```

## Authentication

Protected endpoints require a Bearer token returned by the login endpoint.

### Authorization Header

```http
Authorization: Bearer <access_token>
```

If the token is missing or invalid, the API returns:

```json
{
  "detail": "Not authenticated"
}
```

or

```json
{
  "detail": "Invalid or expired token"
}
```

## Endpoints

### 1. GET /

Returns a welcome message.

**Response example**

```json
{
  "message": "Welcome to the Crop Deal Risk and Loss Prevention Decision Support System API.",
  "status": "success"
}
```

---

### 2. GET /health

Checks the status of the backend.

**Response example**

```json
{
  "status": "healthy",
  "message": "Server is running successfully."
}
```

---

### 3. POST /api/auth/register

Register a new user account.

**Request body**

```json
{
  "name": "Test Farmer",
  "email": "farmer@test.com",
  "password": "test123",
  "role": "farmer",
  "location": "Colombo"
}
```

**Response**

```json
{
  "user_id": "7a5b5dd2-45d8-40fe-a475-2f9d2ef18dcc",
  "name": "Test Farmer",
  "email": "farmer@test.com",
  "role": "farmer",
  "location": "Colombo"
}
```

**Errors**
- 400: Duplicate email
- 422: Invalid payload
- 503: Firebase unavailable

---

### 4. POST /api/auth/login

Login using email and password form data.

**Request**

```bash
curl -X POST http://127.0.0.1:8000/api/auth/login \
  -d "username=farmer@test.com&password=test123"
```

**Response**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "user_id": "7a5b5dd2-45d8-40fe-a475-2f9d2ef18dcc",
    "name": "Test Farmer",
    "email": "farmer@test.com",
    "role": "farmer",
    "location": "Colombo"
  }
}
```

**Errors**
- 401: Invalid email/password
- 503: Firebase unavailable

---

### 5. GET /api/auth/me

Returns the profile of the authenticated user.

**Headers**

```http
Authorization: Bearer <token>
```

**Response**

```json
{
  "user_id": "7a5b5dd2-45d8-40fe-a475-2f9d2ef18dcc",
  "name": "Test Farmer",
  "email": "farmer@test.com",
  "role": "farmer",
  "location": "Colombo"
}
```

**Errors**
- 401: Missing/invalid token
- 503: Firebase unavailable

---

### 6. POST /crop-details

Save crop listing information.

**Request body**

```json
{
  "crop_name": "Rice",
  "quantity_kg": 1000,
  "expected_price_per_kg": 110,
  "farmer": "Test Farmer",
  "location": "Colombo"
}
```

**Response**

```json
{
  "success": true,
  "message": "Crop details saved successfully.",
  "documentId": "abc123",
  "data": {
    "cropName": "Rice",
    "quantityKg": 1000,
    "expectedPricePerKg": 110,
    "farmer": "Test Farmer",
    "location": "Colombo"
  }
}
```

---

### 7. POST /risk-assessment

Prototype rule-based risk analysis without JWT protection.

**Request body**

```json
{
  "crop_name": "Rice",
  "quantity_kg": 1000,
  "offered_price_per_kg": 40,
  "market_price_per_kg": 120,
  "buyer_verified": false,
  "payment_method": "cash_on_delivery"
}
```

**Response**

```json
{
  "prototype_rule_based_assessment": true,
  "risk_score": 80,
  "risk_level": "High",
  "crop_name": "Rice",
  "quantity_kg": 1000,
  "offered_price_per_kg": 40,
  "market_price_per_kg": 120,
  "buyer_verified": false,
  "payment_method": "cash_on_delivery",
  "price_difference_percent": 66.67,
  "reasons": [
    "Offered price is substantially below the current market price...",
    "Buyer is not verified...",
    "Cash-on-delivery payment is riskier..."
  ],
  "suggested_precautions": [
    "Verify the buyer identity...",
    "Use a written agreement..."
  ]
}
```

---

### 8. POST /assess/full

Full protected assessment with user identity and Firestore persistence.

**Authentication**

```http
Authorization: Bearer <token>
```

**Request body**

```json
{
  "crop_name": "Rice",
  "quantity_kg": 1000,
  "offered_price_per_kg": 40,
  "market_price_per_kg": 120,
  "buyer_verified": false,
  "payment_method": "cash_on_delivery",
  "distance_km": 80
}
```

**Response**

```json
{
  "assessment_id": "ff7a0d9d-...",
  "risk_score": 85,
  "risk_level": "High",
  "recommendation": "REJECT",
  "financial_exposure": 2550.0,
  "reasons": [
    "Offered price is substantially below the current market price...",
    "Buyer is not verified...",
    "Cash-on-delivery payment is riskier...",
    "Distance exceeds 50 km..."
  ],
  "farmer_must_decide": true,
  "disclaimer": "Prototype rule-based assessment only"
}
```

**Errors**
- 401: Missing or invalid token
- 503: Firebase unavailable

---

### 9. POST /simulate/whatif

Run a simulated comparison between an original deal and a modified scenario.

**Authentication**

```http
Authorization: Bearer <token>
```

**Request body**

```json
{
  "assessment_id": "63325c07-...",
  "changes": {
    "offered_price_per_kg": 230,
    "payment_method": "advance",
    "buyer_verified": true,
    "distance_km": 15
  }
}
```

**Response**

```json
{
  "scenario_id": "a2a4ea67-...",
  "label": "⚠️ SIMULATED SCENARIO — not a real deal",
  "original": {
    "crop_name": "Rice",
    "quantity_kg": 1000,
    "offered_price_per_kg": 40,
    "market_price_per_kg": 120,
    "buyer_verified": false,
    "payment_method": "cash_on_delivery",
    "distance_km": 80,
    "risk_score": 85,
    "risk_level": "High",
    "recommendation": "REJECT"
  },
  "updated": {
    "crop_name": "Rice",
    "quantity_kg": 1000,
    "offered_price_per_kg": 230,
    "market_price_per_kg": 120,
    "buyer_verified": true,
    "payment_method": "advance",
    "distance_km": 15,
    "risk_score": 25,
    "risk_level": "Low",
    "recommendation": "ACCEPT"
  },
  "risk_score_change": -60,
  "recommendation_changed": true,
  "is_simulated": true
}
```

**Errors**
- 401: Missing or invalid token
- 403: Assessment does not belong to current user
- 404: Assessment ID not found
- 422: Invalid change payload

---

### 10. GET /firebase-test

Checks whether Firebase is connected.

**Response example**

```json
{
  "status": "success",
  "message": "Firebase is working!",
  "data": {
    "status": "connected",
    "project": "crop-deal-risk-system"
  }
}
```

---

## Error Codes

| Status Code | Meaning |
| --- | --- |
| 200 | Request succeeded |
| 400 | Bad request / duplicate user |
| 401 | Unauthorized (missing or invalid token) |
| 403 | Forbidden (user does not own resource) |
| 404 | Not found |
| 422 | Validation error |
| 503 | Firebase or service unavailable |

## Notes

- This backend is a prototype rule-based system, not a trained ML model.
- Use the JWT returned by login for all protected routes.
- All scenario results are saved under the `scenarios` collection with `is_simulated: true`.
