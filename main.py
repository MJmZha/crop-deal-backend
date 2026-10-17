import logging
import uuid
from datetime import datetime
from typing import Literal

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import AliasChoices, BaseModel, ConfigDict, Field

from firebase_config import db

logger = logging.getLogger(__name__)


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
            "project": "al-crop-risk-system",
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

