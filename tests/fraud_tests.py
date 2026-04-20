"""
Tests for Bubbles fraud detection system.
Covers both app/transactions.py and src/transaction_processor.py

Run from repo root:
    pytest tests/ -v
"""
import sys
import os

# Fix import paths so pytest finds the modules from repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from transactions import evaluate_transaction
from transaction_processor import calculate_risk_score, status_transaction


# ── Tests for app/transactions.py ─────────────────────────────────────────────

class TestEvaluateTransaction:

    def test_normal_transaction_approved(self):
        result = evaluate_transaction(50000, "CO", 1)
        assert result["status"] == "APPROVED"
        assert result["risk"] == 0

    def test_high_amount_blocked(self):
        result = evaluate_transaction(2_000_000, "CO", 1)
        assert result["status"] == "BLOCKED"
        assert result["risk"] >= 50

    def test_foreign_location_and_high_frequency_blocked(self):
        result = evaluate_transaction(100_000, "US", 5)
        assert result["status"] == "BLOCKED"
        assert result["risk"] >= 70

    def test_boundary_amount_approved(self):
        # Exactly 1_000_000 does NOT trigger the > 1_000_000 rule
        result = evaluate_transaction(1_000_000, "CO", 3)
        assert result["status"] == "APPROVED"

    def test_foreign_location_alone_not_enough_to_block(self):
        # Only 30 risk points from foreign location → not blocked (threshold 70)
        result = evaluate_transaction(50_000, "US", 1)
        assert result["status"] == "APPROVED"
        assert result["risk"] == 30

    def test_high_frequency_alone_not_enough_to_block(self):
        # Only 40 risk points from frequency → not blocked
        result = evaluate_transaction(50_000, "CO", 5)
        assert result["status"] == "APPROVED"
        assert result["risk"] == 40

    def test_amount_plus_foreign_location_blocked(self):
        result = evaluate_transaction(2_000_000, "US", 1)
        assert result["status"] == "BLOCKED"
        assert result["risk"] == 80


# ── Tests for src/transaction_processor.py ────────────────────────────────────

class TestCalculateRiskScore:

    def _base(self, **overrides):
        data = {
            "amount": 100_000,
            "hour": 14,
            "origin_city": "Bogota",
            "destination_city": "Bogota",
            "is_new_account": False,
        }
        data.update(overrides)
        return data

    def test_normal_transaction_low_score(self):
        score, flags = calculate_risk_score(self._base())
        assert score < 30
        assert flags == []

    def test_very_high_amount_flag(self):
        score, flags = calculate_risk_score(self._base(amount=200_000_000))
        assert "VERY_HIGH_AMOUNT" in flags
        assert score >= 40

    def test_off_hours_flag(self):
        score, flags = calculate_risk_score(self._base(hour=3))
        assert "OFF_HOURS" in flags

    def test_new_account_flag(self):
        score, flags = calculate_risk_score(self._base(is_new_account=True))
        assert "NEW_ACCOUNT" in flags

    def test_cross_city_flag(self):
        score, flags = calculate_risk_score(self._base(destination_city="Cali"))
        assert "CROSS_CITY" in flags

    def test_score_capped_at_100(self):
        # Trigger all rules
        txn = self._base(
            amount=200_000_000, hour=3,
            is_new_account=True, destination_city="Cali"
        )
        score, _ = calculate_risk_score(txn)
        assert score <= 100

    def test_case_insensitive_city_comparison(self):
        score, flags = calculate_risk_score(self._base(
            origin_city="bogota", destination_city="BOGOTA"
        ))
        assert "CROSS_CITY" not in flags


class TestStatusTransaction:

    def _base(self, **overrides):
        data = {
            "id": "TEST-001",
            "amount": 100_000,
            "hour": 14,
            "origin_city": "Bogota",
            "destination_city": "Bogota",
            "is_new_account": False,
        }
        data.update(overrides)
        return data

    def test_approved_status(self):
        result = status_transaction(self._base())
        assert result["status"] == "APPROVED"

    def test_review_status(self):
        # Cross-city (15) + new account (20) = 35 → REVIEW
        result = status_transaction(self._base(
            is_new_account=True, destination_city="Cali"
        ))
        assert result["status"] == "REVIEW"

    def test_blocked_status(self):
        # Very high amount (40) + off hours (20) + new account (20) = 80 → BLOCKED
        result = status_transaction(self._base(
            amount=200_000_000, hour=3, is_new_account=True
        ))
        assert result["status"] == "BLOCKED"

    def test_result_contains_required_fields(self):
        result = status_transaction(self._base())
        for field in ("risk_score", "risk_flags", "status", "processed_at"):
            assert field in result