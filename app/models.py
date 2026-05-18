from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime


class TransactionRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=100)
    amount: float = Field(..., gt=0, le=1_000_000_000,
                          description="Amount in COP. Must be positive and realistic.")
    location: str = Field(..., min_length=2, max_length=5,
                           description="ISO country code, e.g. CO, US, MX")
    frequency: int = Field(..., ge=1, le=200,
                            description="Number of transactions in the last hour")
    hour: int = Field(..., ge=0, le=23, description="Hour of the day (0-23)")
    is_new_account: bool = Field(default=False)

    @field_validator("user_id")
    @classmethod
    def sanitize_user_id(cls, v: str) -> str:
        clean = v.strip()
        if not all(c.isalnum() or c in ("_", "-") for c in clean):
            raise ValueError("user_id must only contain letters, numbers, _ or -")
        return clean.lower()

    @field_validator("location")
    @classmethod
    def normalize_location(cls, v: str) -> str:
        return v.upper().strip()

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: float) -> float:
        if v != round(v, 2):
            raise ValueError("Amount cannot have more than 2 decimal places")
        return v


class TransactionResponse(BaseModel):
    transaction_id: str
    user_id: str
    amount: float
    location: str
    hour: int
    status: str                  
    risk_score: int              
    rule_score: int            
    ml_score: float              
    behavioral_adjustment: float 
    flags: list[str]             
    message: str
    processed_at: datetime


class UserProfileResponse(BaseModel):
    user_id: str
    transaction_count: int
    avg_amount: float
    std_amount: float
    avg_hour: float
    known_locations: list[str]
    avg_frequency: float
    is_profiled: bool            
    last_updated: Optional[datetime]


class MetricsResponse(BaseModel):
    total_transactions: int
    approved: int
    review: int
    blocked: int
    approval_rate: float
    block_rate: float
    avg_risk_score: float
