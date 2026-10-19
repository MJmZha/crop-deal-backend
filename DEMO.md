# Supervisor Demo Script

## Project: Crop Deal Risk Decision Support System

This demo walkthrough shows a fast, realistic live API demonstration of the backend system in under 5–7 minutes.

## Objectives

- Show secure user registration and login
- Demonstrate risk assessment logic
- Show protected API usage with JWT authentication
- Demonstrate the what-if simulator for alternative deal scenarios
- Highlight Firestore persistence and structured outputs

## Demo Flow

### 1. Open the API docs

- Go to: `http://127.0.0.1:8000/docs`
- Explain that the project exposes a clean FastAPI Swagger interface.
- Mention that the app uses Firebase Firestore for data persistence.

### 2. Show the health endpoint

Request:

```bash
GET /health
```

Expected output:

```json
{
  "status": "healthy",
  "message": "Server is running successfully."
}
```

Explain:
- Backend is running
- Firebase connectivity is configured
- API is ready for demo

### 3. Register a user

Request:

```bash
POST /api/auth/register
```

Body:

```json
{
  "name": "Test Farmer",
  "email": "farmer@test.com",
  "password": "test123",
  "role": "farmer",
  "location": "Colombo"
}
```

Expected output:

```json
{
  "user_id": "...",
  "name": "Test Farmer",
  "email": "farmer@test.com",
  "role": "farmer",
  "location": "Colombo"
}
```

Explain:
- User is saved to Firestore under the `users` collection
- Password is hashed with bcrypt
- Email uniqueness is enforced

### 4. Login to receive JWT

Request:

```bash
POST /api/auth/login
```

Form data:

```text
username=farmer@test.com
password=test123
```

Expected output:

```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "user": {
    "user_id": "...",
    "name": "Test Farmer",
    "email": "farmer@test.com",
    "role": "farmer",
    "location": "Colombo"
  }
}
```

Explain:
- JWT is issued with `sub` = user_id and `role`
- Token is required for protected endpoints

### 5. Show protected profile access

Request:

```bash
GET /api/auth/me
Authorization: Bearer <token>
```

Expected output:

```json
{
  "user_id": "...",
  "name": "Test Farmer",
  "email": "farmer@test.com",
  "role": "farmer",
  "location": "Colombo"
}
```

Explain:
- Authentication is enforced behind the JWT middleware
- Protected API behavior is working

### 6. Run a full risk assessment

Request:

```bash
POST /assess/full
Authorization: Bearer <token>
```

Body:

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

Expected output:

```json
{
  "assessment_id": "...",
  "risk_score": 85,
  "risk_level": "High",
  "recommendation": "REJECT",
  "financial_exposure": 2550.0,
  "reasons": [
    "Offered price is substantially below the current market price...",
    "Buyer is not verified...",
    "Cash-on-delivery payment is riskier..."
  ]
}
```

Explain:
- This is a prototype rule-based decision support model
- The API saves the assessment to Firestore
- The system flags the risk to help a farmer decide

### 7. Demonstrate what-if simulation

Use the assessment ID returned from the previous step.

Request:

```bash
POST /simulate/whatif
Authorization: Bearer <token>
```

Body:

```json
{
  "assessment_id": "<assessment_id>",
  "changes": {
    "offered_price_per_kg": 140,
    "payment_method": "advance",
    "buyer_verified": true,
    "distance_km": 15
  }
}
```

Expected output:

```json
{
  "scenario_id": "...",
  "label": "⚠️ SIMULATED SCENARIO — not a real deal",
  "risk_score_change": -30,
  "recommendation_changed": true,
  "is_simulated": true,
  "original": {
    "risk_score": 85,
    "risk_level": "High",
    "recommendation": "REJECT"
  },
  "updated": {
    "risk_score": 55,
    "risk_level": "Medium",
    "recommendation": "NEGOTIATE"
  }
}
```

Explain:
- This simulates a modified negotiation scenario
- It compares original vs updated conditions
- It saves the result to the `scenarios` collection

## Expected Demo Outcomes

- Registration succeeds
- Login returns JWT token
- Protected endpoints fail without token
- High-risk deal is flagged with a reasoned recommendation
- What-if changes reduce risk in a simulated scenario
- Firestore stores user, assessment, and scenario records

## Screenshots / Demo Placeholders

Use these placeholders during presentation:

- Screenshot 1: Swagger UI homepage
- Screenshot 2: Register endpoint response
- Screenshot 3: Login response with JWT token
- Screenshot 4: /assess/full result with risk score
- Screenshot 5: /simulate/whatif comparison output
- Screenshot 6: Firebase Firestore collections

## Suggested Presentation Script

> “This backend performs automated crop deal risk analysis for farmers. It stores secure user profiles, issues JWT access tokens, evaluates crop deal conditions, and supports what-if simulations before a real deal is made.”

> “The system is designed to help users make informed decisions by comparing the original deal scenario with a modified scenario, without committing to a real transaction.”

## Closing Message

The project demonstrates a secure, modular, and demo-ready backend that can be extended into a full farmer decision dashboard, web frontend, or AI-based recommendation engine in later stages.
