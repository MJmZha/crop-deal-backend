# Crop Deal Risk Decision Support System

A FastAPI-based backend for evaluating crop trading risks, authenticating users, and running simulated deal scenarios before a real transaction is confirmed.

## Overview

This backend helps farmers and buyers assess whether a crop deal is financially safe. It calculates a risk score for transactions using a rule-based assessment model, stores assessments in Firebase Firestore, supports JWT-based authentication, and allows scenario testing through a what-if simulation engine.

The project is designed for real-world demo use, API smoke testing, and future integration with a frontend dashboard or mobile app.

## Key Features

- JWT-based authentication and authorization
- User registration and login
- Protected profile retrieval
- Risk assessment for crop deals
- Full assessment with distance and financial exposure logic
- What-if simulation engine for decision comparison
- Firebase Firestore storage for users, assessments, and scenarios
- RESTful API design with FastAPI
- Pydantic validation and structured error responses
- Test coverage with pytest
- Demo-friendly API endpoints for live presentations

## Endpoints Included

The backend exposes 14+ API routes, including:

1. GET /
2. GET /health
3. POST /api/auth/register
4. POST /api/auth/login
5. GET /api/auth/me
6. POST /crop-details
7. POST /risk-assessment
8. GET /firebase-test
9. POST /crop-details/save
10. GET /crop-details/list
11. POST /assess/full
12. POST /simulate/whatif
13. 404 custom handler
14. 500 custom handler

## Tech Stack

- FastAPI
- Python 3.13+
- Firebase Admin SDK + Firestore
- JWT authentication via python-jose
- Password hashing via bcrypt
- Pydantic v2
- Pytest
- Uvicorn

## Project Structure

```text
crop-deal-backend/
├── main.py
├── firebase_config.py
├── firebase-credentials.json
├── requirements.txt
├── README.md
├── DEMO.md
├── API_DOCS.md
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_auth.py
│   ├── test_assessment.py
│   └── test_whatif.py
└── .venv/
```

## Setup Instructions

### 1. Clone the project

```bash
git clone <your-repository-url>
cd crop-deal-backend
```

### 2. Create and activate a virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the project root or export variables in your shell:

```env
SECRET_KEY=your-super-secret-key
FIREBASE_PROJECT_ID=crop-deal-risk-system
GOOGLE_APPLICATION_CREDENTIALS=firebase-credentials.json
```

### 5. Firebase setup

1. Create a Firebase project.
2. Enable Firestore Database.
3. Generate a service account JSON key.
4. Download the JSON file and place it as:
   - `firebase-credentials.json`
5. Set the project ID to `crop-deal-risk-system` or update the environment variable accordingly.

## Environment Variables

| Variable | Required | Description |
| --- | --- | --- |
| `SECRET_KEY` | Yes | Secret key used for JWT signing |
| `FIREBASE_PROJECT_ID` | Yes | Firebase project ID |
| `GOOGLE_APPLICATION_CREDENTIALS` | Yes | Path to Firebase service account JSON |

## Running the Server

Start the API in development mode:

```bash
uvicorn main:app --reload
```

Then open:

- http://127.0.0.1:8000
- http://127.0.0.1:8000/docs
- http://127.0.0.1:8000/redoc

## Running Tests

```bash
pytest tests/ -v
```

## API Endpoint Summary

| Method | Endpoint | Auth Required | Description |
| --- | --- | --- | --- |
| GET | `/` | No | Welcome message |
| GET | `/health` | No | Server health check |
| POST | `/api/auth/register` | No | Register new user |
| POST | `/api/auth/login` | No | Login and return JWT |
| GET | `/api/auth/me` | Yes | Get current authenticated user |
| POST | `/crop-details` | No | Save crop listing |
| POST | `/risk-assessment` | No | Prototype risk calculation |
| GET | `/firebase-test` | No | Firebase connectivity test |
| POST | `/crop-details/save` | No | Save crop listing to Firestore |
| GET | `/crop-details/list` | No | List all crop listings |
| POST | `/assess/full` | Yes | Full risk assessment + Firestore save |
| POST | `/simulate/whatif` | Yes | Simulate a changed deal scenario |

## Example JWT Flow

1. Register a new user.
2. Login with email and password.
3. Copy the returned `access_token`.
4. Send it in the `Authorization: Bearer <token>` header.
5. Use the token to call protected routes.

## Demo Use Case

A farmer can:

- Register an account
- Login securely
- Enter a crop deal scenario
- View risk assessment output
- Test alternative pricing or payment changes
- Compare original vs changed scenario
- Save simulation as a scenario record

## Notes

This project is a prototype decision support system and uses rule-based scoring rather than a trained AI model. It is intended for demonstrations, proof-of-concept validation, and future integration with analytics or ML models.

---

For more detailed endpoint behavior, request payloads, and status codes, see [API_DOCS.md](API_DOCS.md).
