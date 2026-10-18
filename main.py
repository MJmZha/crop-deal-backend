import logging
import os
import uuid
from datetime import datetime, timedelta
from typing import Any, Literal

import bcrypt
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from pydantic import AliasChoices, BaseModel, ConfigDict, EmailStr, Field

from firebase_config import db

logger = logging.getLogger(__name__)


SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


class CropDetailsRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    crop_name: str = Field(
        ...,
        min_length=1,
        validation_alias=AliasChoices("cropName", "crop_name"),
    )
    quantity_kg: float = Field(
        ...,
        gt=0,
        validation_alias=AliasChoices("quantityKg", "quantity_kg"),
    )
    expected_price_per_kg: float = Field(
        ...,
        gt=0,
        validation_alias=AliasChoices(
            "expectedPricePerKg",
            "expected_price_per_kg",
            "offered_price_per_kg",
        ),
    )
    farmer: str | None = Field(
        default=None,
        validation_alias=AliasChoices("farmer", "farmerName"),
    )
    location: str | None = Field(
        default=None,
        min_length=1,
        validation_alias=AliasChoices("location", "farmLocation"),
    )

    def to_firestore_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "cropName": self.crop_name,
            "quantityKg": self.quantity_kg,
            "expectedPricePerKg": self.expected_price_per_kg,
        }
        if self.farmer is not None:
            payload["farmer"] = self.farmer
        if self.location is not None:
            payload["location"] = self.location
        return payload


class RiskAssessmentRequest(BaseModel):
    crop_name: str = Field(..., min_length=1)
    quantity_kg: float = Field(..., gt=0)
    offered_price_per_kg: float = Field(..., gt=0)
    market_price_per_kg: float = Field(..., gt=0)
    buyer_verified: bool
    payment_method: Literal["advance", "cash_on_delivery", "after_delivery"]


class UserRegister(BaseModel):
    name: str
    email: EmailStr
    password: str = Field(..., min_length=6)
    role: Literal["farmer", "buyer", "admin"]
    location: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    user_id: str
    name: str
    email: EmailStr
    role: Literal["farmer", "buyer", "admin"]
    location: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


def hash_password(password: str) -> str:
    password_bytes = password.encode("utf-8")
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password_bytes, salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    password_bytes = plain.encode("utf-8")
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]
    return bcrypt.checkpw(password_bytes, hashed.encode("utf-8"))


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    if expires_delta is None:
        expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("sub") is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return payload
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    payload = decode_token(token)
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Firebase is not connected.",
        )

    user_doc = db.collection("users").document(user_id).get()
    if not user_doc.exists:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_data = user_doc.to_dict() or {}
    return {
        "user_id": user_id,
        "name": user_data.get("name"),
        "email": user_data.get("email"),
        "role": user_data.get("role"),
        "location": user_data.get("location"),
    }


def require_role(role: str):
    def role_dependency(user: dict = Depends(get_current_user)) -> dict:
        if user.get("role") != role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This action requires the '{role}' role.",
            )
        return user

    return role_dependency


app = FastAPI(
    title="Crop Deal Risk Decision Support API",
    version="0.1.0",
    description="AI-based crop deal risk and loss prevention backend for farmers.",
)


@app.get("/")
def root() -> dict[str, str]:
    """Return a welcome message for the API."""
    return {
        "message": "Welcome to the Crop Deal Risk and Loss Prevention Decision Support System API.",
        "status": "success",
    }


@app.get("/health")
def health() -> dict[str, str]:
    """Return the health status of the API server."""
    return {
        "status": "healthy",
        "message": "Server is running successfully.",
    }


@app.post("/api/auth/register")
def register_user(payload: UserRegister) -> UserOut:
    """Register a new user and save their profile to Firestore."""
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Firebase is not connected.",
        )

    existing_user = (
        db.collection("users")
        .where(field_path="email", op_string="==", value=payload.email)
        .limit(1)
        .stream()
    )
    if any(existing_user):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists.",
        )

    user_id = str(uuid.uuid4())
    password_hash = hash_password(payload.password)
    user_data = {
        "user_id": user_id,
        "name": payload.name,
        "email": str(payload.email),
        "password_hash": password_hash,
        "role": payload.role,
        "location": payload.location,
        "created_at": datetime.utcnow().isoformat(),
    }

    db.collection("users").document(user_id).set(user_data)

    return UserOut(
        user_id=user_id,
        name=payload.name,
        email=payload.email,
        role=payload.role,
        location=payload.location,
    )


@app.post("/api/auth/login")
def login_user(form_data: OAuth2PasswordRequestForm = Depends()) -> TokenResponse:
    """Authenticate a user and return a JWT access token."""
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Firebase is not connected.",
        )

    users = (
        db.collection("users")
        .where(field_path="email", op_string="==", value=form_data.username)
        .limit(1)
        .stream()
    )
    user_doc = next(users, None)
    if user_doc is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_data = user_doc.to_dict()
    if not verify_password(form_data.password, user_data.get("password_hash", "")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token({"sub": user_data["user_id"], "role": user_data["role"]})
    user_out = UserOut(
        user_id=user_data["user_id"],
        name=user_data["name"],
        email=user_data["email"],
        role=user_data["role"],
        location=user_data["location"],
    )
    return TokenResponse(access_token=token, user=user_out)


@app.get("/api/auth/me")
def get_logged_in_user(user: dict = Depends(get_current_user)) -> UserOut:
    """Fetch the currently authenticated user profile."""
    return UserOut(
        user_id=user["user_id"],
        name=user["name"],
        email=user["email"],
        role=user["role"],
        location=user["location"],
    )


@app.post("/crop-details")
def submit_crop_details(payload: CropDetailsRequest) -> dict[str, object]:
    """Accept crop deal details and save them to Firestore."""
    firestore_payload = payload.to_firestore_dict()

    if db is None:
        return JSONResponse(
            status_code=503,
            content={
                "success": False,
                "message": "Firebase is not connected. Set GOOGLE_APPLICATION_CREDENTIALS and Firebase project settings.",
            },
        )

    try:
        doc_ref = db.collection("cropListings").document()
        doc_ref.set(firestore_payload)

        return {
            "success": True,
            "message": "Crop details saved successfully.",
            "documentId": doc_ref.id,
            "data": firestore_payload,
        }
    except Exception:
        logger.exception("Failed to save crop details to Firestore.")
        return JSONResponse(
            status_code=503,
            content={
                "success": False,
                "message": "Unable to save crop details right now. Please try again later.",
            },
        )


@app.post("/risk-assessment")
def assess_risk(payload: RiskAssessmentRequest) -> dict[str, object]:
    """Prototype rule-based crop deal risk assessment for farmers."""
    reasons: list[str] = []
    precautions: list[str] = []
    risk_score = 0

    offered_price = payload.offered_price_per_kg
    market_price = payload.market_price_per_kg
    price_difference_percent = ((market_price - offered_price) / market_price) * 100

    if offered_price < market_price * 0.8:
        risk_score += 35
        reasons.append(
            "Offered price is substantially below the current market price, which may signal a weak deal or possible manipulation."
        )
    elif offered_price < market_price:
        risk_score += 20
        reasons.append(
            "Offered price is below the current market price, reducing expected profit and increasing deal risk."
        )
    else:
        reasons.append(
            "Offered price is at or above the market price, which is favorable and lowers risk."
        )

    if not payload.buyer_verified:
        risk_score += 30
        reasons.append("Buyer is not verified, which increases the risk of non-payment or fraud.")
    else:
        reasons.append("Buyer verification lowers the risk of default or scam behavior.")

    if payload.payment_method == "cash_on_delivery":
        risk_score += 25
        reasons.append("Cash-on-delivery payment is riskier because payment may not be secured before delivery.")
    elif payload.payment_method == "after_delivery":
        risk_score += 18
        reasons.append("After-delivery payment increases risk because payment may be delayed or disputed.")
    else:
        reasons.append("Advance payment is relatively safer because some payment is received upfront.")

    risk_score = max(0, min(100, risk_score))

    if risk_score >= 70:
        risk_level = "High"
        precautions = [
            "Verify the buyer identity and trade history before confirming the deal.",
            "Use a written agreement with quantity, quality, and delivery terms clearly stated.",
            "Ask for a partial advance payment or secure confirmation before dispatch.",
            "Avoid large-volume sales to unverified buyers in a single transaction.",
        ]
    elif risk_score >= 35:
        risk_level = "Medium"
        precautions = [
            "Double-check buyer credibility and market comparisons before proceeding.",
            "Use staged payments or a clear delivery schedule with confirmation steps.",
            "Keep documentation of the price agreement, quantity, and location.",
        ]
    else:
        risk_level = "Low"
        precautions = [
            "Maintain a written record of the deal and agreed terms.",
            "Proceed with standard delivery and payment checks, but no major extra risk is currently indicated.",
            "Continue monitoring market prices and buyer communication before final dispatch.",
        ]

    return {
        "prototype_rule_based_assessment": True,
        "note": "This is a prototype rule-based assessment for decision support only; it is not a trained AI model and not scientifically validated.",
        "risk_score": risk_score,
        "risk_level": risk_level,
        "crop_name": payload.crop_name,
        "quantity_kg": payload.quantity_kg,
        "offered_price_per_kg": payload.offered_price_per_kg,
        "market_price_per_kg": payload.market_price_per_kg,
        "buyer_verified": payload.buyer_verified,
        "payment_method": payload.payment_method,
        "price_difference_percent": round(price_difference_percent, 2),
        "reasons": reasons,
        "suggested_precautions": precautions,
    }


@app.exception_handler(404)
async def not_found_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content={
            "success": False,
            "message": "The requested endpoint was not found.",
            "path": str(request.url.path),
        },
    )


@app.exception_handler(500)
async def internal_server_error_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "An internal server error occurred. Please try again later.",
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "message": "Request validation failed.",
            "details": exc.errors(),
        },
    )
    
    # ============================================
# FIREBASE INTEGRATION ENDPOINTS
# ============================================

@app.get("/firebase-test")
def firebase_test():
    """Test Firebase connection."""
    if db is None:
        return {
            "status": "error",
            "message": "Firebase not connected. Check firebase-credentials.json",
        }
    
    try:
        test_ref = db.collection("test").document("connection")
        test_ref.set({
            "status": "connected",
            "timestamp": datetime.utcnow().isoformat(),
            "project": "crop-deal-risk-system",
        })
        
        doc = test_ref.get()
        
        return {
            "status": "success",
            "message": "Firebase is working!",
            "data": doc.to_dict(),
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/crop-details/save")
def save_crop_to_firestore(payload: CropDetailsRequest):
    """Save crop details to Firestore."""
    if db is None:
        return {"status": "error", "message": "Firebase not connected"}
    
    try:
        crop_id = str(uuid.uuid4())
        data = {
            **payload.model_dump(),
            "crop_id": crop_id,
            "created_at": datetime.utcnow().isoformat(),
        }
        
        db.collection("cropListings").document(crop_id).set(data)
        
        return {
            "status": "success",
            "message": "Crop saved to Firestore!",
            "crop_id": crop_id,
            "data": data,
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/crop-details/list")
def list_crops_from_firestore():
    """Get all crop listings from Firestore."""
    if db is None:
        return {"status": "error", "message": "Firebase not connected"}
    
    try:
        crops = []
        docs = db.collection("cropListings").stream()
        
        for doc in docs:
            crop = doc.to_dict()
            crop["id"] = doc.id
            crops.append(crop)
        
        return {"status": "success", "count": len(crops), "crops": crops}
    except Exception as e:
        return {"status": "error", "message": str(e)}


class FullAssessmentRequest(BaseModel):
    crop_name: str = Field(..., min_length=1)
    quantity_kg: float = Field(..., gt=0)
    offered_price_per_kg: float = Field(..., gt=0)
    market_price_per_kg: float = Field(..., gt=0)
    buyer_verified: bool
    payment_method: Literal["advance", "cash_on_delivery", "after_delivery"]
    distance_km: float = Field(default=0.0, ge=0)


class WhatIfRequest(BaseModel):
    assessment_id: str
    changes: dict[str, Any] = Field(default_factory=dict)


def compute_assessment_result(payload: FullAssessmentRequest) -> dict[str, object]:
    reasons: list[str] = []
    risk_score = 0

    offered_price = payload.offered_price_per_kg
    market_price = payload.market_price_per_kg

    if offered_price < market_price * 0.8:
        risk_score += 35
        reasons.append(
            "Offered price is substantially below the current market price, which may signal a weak deal or possible manipulation."
        )
    elif offered_price < market_price:
        risk_score += 20
        reasons.append(
            "Offered price is below the current market price, reducing expected profit and increasing deal risk."
        )
    else:
        reasons.append(
            "Offered price is at or above the market price, which is favorable and lowers risk."
        )

    if not payload.buyer_verified:
        risk_score += 30
        reasons.append("Buyer is not verified, which increases the risk of non-payment or fraud.")
    else:
        reasons.append("Buyer verification lowers the risk of default or scam behavior.")

    if payload.payment_method == "cash_on_delivery":
        risk_score += 25
        reasons.append("Cash-on-delivery payment is riskier because payment may not be secured before delivery.")
    elif payload.payment_method == "after_delivery":
        risk_score += 18
        reasons.append("After-delivery payment increases risk because payment may be delayed or disputed.")
    else:
        reasons.append("Advance payment is relatively safer because some payment is received upfront.")

    if payload.distance_km > 50:
        risk_score += 10
        reasons.append("Distance exceeds 50 km, increasing the risk of delivery and coordination issues.")
    else:
        reasons.append("Distance is within the preferred range, reducing logistical risk.")

    risk_score = max(0, min(100, risk_score))

    if risk_score >= 70:
        risk_level = "High"
        recommendation = "REJECT"
    elif risk_score >= 35:
        risk_level = "Medium"
        recommendation = "NEGOTIATE"
    else:
        risk_level = "Low"
        recommendation = "ACCEPT"

    financial_exposure = (
        payload.quantity_kg
        * payload.offered_price_per_kg
        * (risk_score / 100)
        * 0.3
    )

    return {
        "risk_score": risk_score,
        "risk_level": risk_level,
        "recommendation": recommendation,
        "financial_exposure": round(financial_exposure, 2),
        "reasons": reasons,
        "farmer_must_decide": True,
        "disclaimer": "Prototype rule-based assessment only",
    }


@app.post("/assess/full")
def assess_full(
    payload: FullAssessmentRequest,
    user: dict = Depends(get_current_user),
) -> dict[str, object]:
    """Calculate a full prototype risk assessment and save it to Firestore."""
    summary = compute_assessment_result(payload)

    if db is None:
        return JSONResponse(
            status_code=503,
            content={
                "success": False,
                "message": "Firebase is not connected. Set GOOGLE_APPLICATION_CREDENTIALS and Firebase configuration.",
            },
        )

    assessment_id = str(uuid.uuid4())
    data = {
        "assessment_id": assessment_id,
        "user_id": user.get("user_id"),
        "user_role": user.get("role"),
        "crop_name": payload.crop_name,
        "quantity_kg": payload.quantity_kg,
        "offered_price_per_kg": payload.offered_price_per_kg,
        "market_price_per_kg": payload.market_price_per_kg,
        "buyer_verified": payload.buyer_verified,
        "payment_method": payload.payment_method,
        "distance_km": payload.distance_km,
        "risk_score": summary["risk_score"],
        "risk_level": summary["risk_level"],
        "recommendation": summary["recommendation"],
        "financial_exposure": summary["financial_exposure"],
        "farmer_must_decide": True,
        "prototype": True,
        "created_at": datetime.utcnow().isoformat(),
    }

    print(f"[DEBUG] Saving assessment: {assessment_id}")
    print(f"[DEBUG] Data: {data}")
    print(f"[DEBUG] DB: {db}")

    try:
        db.collection("assessments").document(assessment_id).set(data)
        return {
            "assessment_id": assessment_id,
            "risk_score": summary["risk_score"],
            "risk_level": summary["risk_level"],
            "recommendation": summary["recommendation"],
            "financial_exposure": summary["financial_exposure"],
            "reasons": summary["reasons"],
            "farmer_must_decide": True,
            "disclaimer": "Prototype rule-based assessment only",
        }
    except Exception as exc:
        logger.exception("Failed to save assessment to Firestore.")
        print(f"[ERROR] Firestore save failed for assessment {assessment_id}: {exc}")
        return JSONResponse(
            status_code=503,
            content={
                "success": False,
                "message": "Unable to save assessment right now. Please try again later.",
            },
        )


@app.post("/simulate/whatif")
def simulate_what_if(
    payload: WhatIfRequest,
    current_user: dict = Depends(get_current_user),
) -> dict[str, object]:
    """Run a simulated scenario against an existing assessment and save the result."""
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Firebase is not connected.",
        )

    assessment_doc = db.collection("assessments").document(payload.assessment_id).get()
    if not assessment_doc.exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment not found.",
        )

    assessment = assessment_doc.to_dict() or {}
    if assessment.get("user_id") != current_user.get("user_id"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only simulate your own assessment.",
        )

    original_inputs = {
        "crop_name": assessment.get("crop_name"),
        "quantity_kg": assessment.get("quantity_kg"),
        "offered_price_per_kg": assessment.get("offered_price_per_kg"),
        "market_price_per_kg": assessment.get("market_price_per_kg"),
        "buyer_verified": assessment.get("buyer_verified"),
        "payment_method": assessment.get("payment_method"),
        "distance_km": assessment.get("distance_km", 0.0),
    }

    try:
        original_payload = FullAssessmentRequest(**original_inputs)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Original assessment data is incomplete: {exc}",
        ) from exc

    updated_inputs = {**original_inputs, **payload.changes}
    try:
        updated_payload = FullAssessmentRequest(**updated_inputs)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid simulation changes: {exc}",
        ) from exc

    original_result = compute_assessment_result(original_payload)
    updated_result = compute_assessment_result(updated_payload)

    risk_score_change = updated_result["risk_score"] - original_result["risk_score"]
    recommendation_changed = original_result["recommendation"] != updated_result["recommendation"]

    scenario_id = str(uuid.uuid4())
    scenario_data = {
        "scenario_id": scenario_id,
        "assessment_id": payload.assessment_id,
        "user_id": current_user.get("user_id"),
        "is_simulated": True,
        "label": "⚠️ SIMULATED SCENARIO — not a real deal",
        "original": {
            **original_inputs,
            "risk_score": original_result["risk_score"],
            "risk_level": original_result["risk_level"],
            "recommendation": original_result["recommendation"],
        },
        "updated": {
            **updated_inputs,
            "risk_score": updated_result["risk_score"],
            "risk_level": updated_result["risk_level"],
            "recommendation": updated_result["recommendation"],
        },
        "risk_score_change": risk_score_change,
        "recommendation_changed": recommendation_changed,
        "created_at": datetime.utcnow().isoformat(),
    }

    db.collection("scenarios").document(scenario_id).set(scenario_data)

    return {
        "scenario_id": scenario_id,
        "label": "⚠️ SIMULATED SCENARIO — not a real deal",
        "original": scenario_data["original"],
        "updated": scenario_data["updated"],
        "risk_score_change": risk_score_change,
        "recommendation_changed": recommendation_changed,
        "is_simulated": True,
    }

