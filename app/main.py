import uuid
from datetime import datetime

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.models import (
    TransactionRequest,
    TransactionResponse,
    UserProfileResponse,
    MetricsResponse,
)
from app import database as db
from app.user_profile import compute_behavioral_factors, build_profile_summary
from app.transactions import evaluate_rules, determine_status
from app.ml_model import predict_fraud_probability

app = FastAPI(
    title="Bubbles — Fraud Prevention API",
    description="Behavioral + ML-enhanced payment fraud detection system.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    db.init_db()

@app.exception_handler(Exception)
async def generic_handler(request: Request, exc: Exception):
    # Never leak internal errors to the client
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error. Check server logs."},
    )

@app.get("/health")
def health_check():
    """Used by the DevSecOps pipeline to verify the service is alive."""
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}

@app.post("/api/transactions", response_model=TransactionResponse, status_code=201)
def submit_transaction(txn: TransactionRequest):
    """
    Evaluate a transaction and return a risk assessment.

    Pipeline:
    1. Load user's behavioral profile from DB
    2. Compute behavioral deviation factors
    3. Run rule-based scoring (scaled by factors)
    4. Run Random Forest model
    5. Combine scores → final risk → status
    6. Persist transaction + update user profile
    """
    user_id = txn.user_id
    txn_dict = txn.model_dump()

    profile = db.get_user_profile(user_id)

    behavioral_factors = compute_behavioral_factors(txn_dict, profile)

    rule_result = evaluate_rules(txn_dict, behavioral_factors)
    rule_score = rule_result["rule_score"]
    flags = rule_result["flags"]
    behavioral_adj = rule_result["behavioral_adjustment"]

    fraud_prob = predict_fraud_probability(txn_dict, behavioral_factors)
    ml_score_raw = fraud_prob * 100

    combined = int(rule_score * 0.6 + ml_score_raw * 0.4)
    combined = max(0, min(combined, 100))  

    if fraud_prob > 0.75:
        flags.append(f"ML model high confidence ({fraud_prob:.0%} fraud probability)")

    status, message = determine_status(combined)

    txn_id = str(uuid.uuid4())
    processed_at = datetime.utcnow()
    db.upsert_user_profile(user_id, txn_dict)

    record = {
        "user_id": user_id,
        "amount": txn.amount,
        "location": txn.location,
        "hour": txn.hour,
        "frequency": txn.frequency,
        "is_new_account": txn.is_new_account,
        "risk_score": combined,
        "rule_score": rule_score,
        "ml_score": round(ml_score_raw, 2),
        "behavioral_adj": behavioral_adj,
        "status": status,
        "flags": flags,
        "processed_at": processed_at.isoformat(),
    }
    db.save_transaction(txn_id, record)

    return TransactionResponse(
        transaction_id=txn_id,
        user_id=user_id,
        amount=txn.amount,
        location=txn.location,
        hour=txn.hour,
        status=status,
        risk_score=combined,
        rule_score=rule_score,
        ml_score=round(ml_score_raw, 2),
        behavioral_adjustment=behavioral_adj,
        flags=flags,
        message=message,
        processed_at=processed_at,
    )

@app.get("/api/transactions/{user_id}")
def get_user_history(user_id: str, limit: int = 50):
    """Returns recent transactions for a user (for frontend dashboard)."""
    if not all(c.isalnum() or c in ("_", "-") for c in user_id):
        raise HTTPException(status_code=400, detail="Invalid user_id format")
    if limit < 1 or limit > 200:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 200")
    return db.get_user_transactions(user_id.lower(), limit)

@app.get("/api/users/{user_id}/profile", response_model=UserProfileResponse)
def get_user_profile(user_id: str):
    """Returns the behavioral profile for a user."""
    if not all(c.isalnum() or c in ("_", "-") for c in user_id):
        raise HTTPException(status_code=400, detail="Invalid user_id format")

    profile = db.get_user_profile(user_id.lower())
    summary = build_profile_summary(profile)

    return UserProfileResponse(
        user_id=user_id.lower(),
        **summary,
    )

@app.get("/api/metrics", response_model=MetricsResponse)
def get_metrics():
    """Aggregated stats for the frontend dashboard."""
    m = db.get_metrics()
    return MetricsResponse(**m)