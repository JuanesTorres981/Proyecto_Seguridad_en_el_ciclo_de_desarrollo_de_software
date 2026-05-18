"""
fraud_tests.py — Unit tests for the fraud detection system.

Tests cover:
- Rule engine (static scoring)
- Behavioral profiling (user-specific adjustments)
- Score combination logic
- Edge cases and security boundaries
"""

import sys
import os
import math

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.transactions import evaluate_rules, determine_status
from app.user_profile import (
    compute_behavioral_factors,
    _circular_deviation,
    _amount_deviation,
    _location_deviation,
)


# ─── Helper to build a mock user profile ─────────────────────────────────────

def make_profile(
    txn_count: int = 20,
    recent_hours: list = None,
    recent_amounts: list = None,
    known_locations: list = None,
    amount_mean: float = 1_000_000,
    amount_m2: float = 5e11,    # ~sqrt(m2/(n-1)) ≈ 162k std
    freq_mean: float = 2.0,
    freq_m2: float = 4.0,
) -> dict:
    return {
        "txn_count": txn_count,
        "recent_hours": recent_hours or list(range(8, 18)) * 2,  # 8am–6pm
        "recent_amounts": recent_amounts or [1_000_000] * 20,
        "known_locations": known_locations or ["CO"],
        "amount_mean": amount_mean,
        "amount_m2": amount_m2,
        "freq_mean": freq_mean,
        "freq_m2": freq_m2,
        "last_updated": "2025-01-01T00:00:00",
    }


# ─── Rule engine tests ────────────────────────────────────────────────────────

class TestRuleEngine:

    def test_normal_transaction_zero_risk(self):
        txn = {"amount": 500_000, "location": "CO",
               "frequency": 1, "hour": 14, "is_new_account": False}
        factors = {k: 1.0 for k in ["hour_factor", "amount_factor",
                                     "location_factor", "frequency_factor"]}
        factors["is_profiled"] = False
        result = evaluate_rules(txn, factors)
        assert result["rule_score"] == 0
        assert result["flags"] == []

    def test_very_high_amount_scores_50(self):
        txn = {"amount": 200_000_000, "location": "CO",
               "frequency": 1, "hour": 14, "is_new_account": False}
        factors = {k: 1.0 for k in ["hour_factor", "amount_factor",
                                     "location_factor", "frequency_factor"]}
        factors["is_profiled"] = False
        result = evaluate_rules(txn, factors)
        assert result["rule_score"] >= 50
        assert any("high amount" in f.lower() for f in result["flags"])

    def test_foreign_location_adds_30(self):
        txn = {"amount": 100_000, "location": "RU",
               "frequency": 1, "hour": 14, "is_new_account": False}
        factors = {k: 1.0 for k in ["hour_factor", "amount_factor",
                                     "location_factor", "frequency_factor"]}
        factors["is_profiled"] = False
        result = evaluate_rules(txn, factors)
        assert result["rule_score"] == 30
        assert any("RU" in f for f in result["flags"])

    def test_new_account_always_adds_20(self):
        txn = {"amount": 100_000, "location": "CO",
               "frequency": 1, "hour": 12, "is_new_account": True}
        factors = {k: 1.0 for k in ["hour_factor", "amount_factor",
                                     "location_factor", "frequency_factor"]}
        factors["is_profiled"] = False
        result = evaluate_rules(txn, factors)
        assert result["rule_score"] == 20  # New account rule isn't factored
        assert "New account" in result["flags"]

    def test_high_frequency_scores_40(self):
        txn = {"amount": 100_000, "location": "CO",
               "frequency": 8, "hour": 14, "is_new_account": False}
        factors = {k: 1.0 for k in ["hour_factor", "amount_factor",
                                     "location_factor", "frequency_factor"]}
        factors["is_profiled"] = False
        result = evaluate_rules(txn, factors)
        assert result["rule_score"] >= 40


# ─── Behavioral profiling tests ───────────────────────────────────────────────

class TestBehavioralProfiling:

    def test_no_profile_returns_all_factors_1(self):
        txn = {"amount": 500_000, "location": "CO",
               "frequency": 1, "hour": 3, "is_new_account": False}
        factors = compute_behavioral_factors(txn, None)
        assert factors["hour_factor"] == 1.0
        assert factors["amount_factor"] == 1.0
        assert factors["location_factor"] == 1.0
        assert factors["is_profiled"] is False

    def test_night_owl_normal_at_3am(self):
        """
        User who always transacts at 1-4am should have low hour deviation at 3am.
        This is the core use case described in the project brief.
        """
        night_hours = [1, 2, 3, 4, 2, 3, 1, 4, 3, 2, 1, 3, 2, 4, 3, 2, 1, 3, 2, 3]
        deviation = _circular_deviation(3, night_hours)
        # Should be 0 (completely normal for this user)
        assert deviation == 0.0

    def test_business_hours_user_abnormal_at_3am(self):
        """
        User who always transacts 9am–5pm should find 3am very unusual.
        """
        business_hours = [9, 10, 11, 12, 13, 14, 15, 16, 17, 10,
                          11, 14, 9, 15, 12, 10, 11, 14, 16, 9]
        deviation = _circular_deviation(3, business_hours)
        # Should be 1.0 (very unusual for this user)
        assert deviation == 1.0

    def test_known_location_has_zero_deviation(self):
        assert _location_deviation("CO", ["CO", "US"]) == 0.0

    def test_unknown_location_has_full_deviation(self):
        assert _location_deviation("RU", ["CO", "US"]) == 1.0

    def test_behavioral_factor_reduces_rule_score(self):
        """
        The night-owl user making a 3am transaction should get LESS risk
        than a business-hours user making the same transaction.
        """
        txn = {"amount": 500_000, "location": "CO",
               "frequency": 1, "hour": 3, "is_new_account": False}
        full_factors = {k: 1.0 for k in ["hour_factor", "amount_factor",
                                           "location_factor", "frequency_factor"]}
        full_factors["is_profiled"] = False
        result_global = evaluate_rules(txn, full_factors)

        profiled_factors = dict(full_factors)
        profiled_factors["hour_factor"] = 0.0   # Normal for this user
        result_profiled = evaluate_rules(txn, profiled_factors)

        assert result_profiled["rule_score"] < result_global["rule_score"]
        assert result_profiled["behavioral_adjustment"] > 0

    def test_insufficient_history_uses_full_factors(self):
        """Users with < 5 transactions get full global rules."""
        profile = make_profile(txn_count=3)
        txn = {"amount": 500_000, "location": "CO",
               "frequency": 1, "hour": 3, "is_new_account": False}
        factors = compute_behavioral_factors(txn, profile)
        assert factors["is_profiled"] is False
        assert factors["hour_factor"] == 1.0


# ─── Status determination tests ───────────────────────────────────────────────

class TestStatusDetermination:

    def test_low_risk_approved(self):
        status, _ = determine_status(30)
        assert status == "APPROVED"

    def test_medium_risk_review(self):
        status, _ = determine_status(55)
        assert status == "REVIEW"

    def test_high_risk_blocked(self):
        status, _ = determine_status(75)
        assert status == "BLOCKED"

    def test_boundary_exactly_70_is_blocked(self):
        status, _ = determine_status(70)
        assert status == "BLOCKED"

    def test_boundary_exactly_45_is_review(self):
        status, _ = determine_status(45)
        assert status == "REVIEW"


# ─── Integration scenario tests ───────────────────────────────────────────────

class TestIntegrationScenarios:

    def test_regular_user_3am_is_not_blocked(self):
        """
        Night-owl user doing their normal 3am transaction should not be blocked
        even though the global hour rule would normally add risk.
        """
        night_profile = make_profile(
            txn_count=20,
            recent_hours=[1, 2, 3, 4, 2, 3, 1, 4, 3, 2,
                          1, 3, 2, 4, 3, 2, 1, 3, 2, 3],
            known_locations=["CO"],
            amount_mean=500_000,
            amount_m2=1e10,
        )
        txn = {"amount": 500_000, "location": "CO",
               "frequency": 1, "hour": 3, "is_new_account": False}
        factors = compute_behavioral_factors(txn, night_profile)
        result = evaluate_rules(txn, factors)
        # The hour rule should be reduced to 0 for this user
        assert factors["hour_factor"] == 0.0
        status, _ = determine_status(result["rule_score"])
        assert status == "APPROVED"

    def test_new_foreign_large_transfer_is_blocked(self):
        """Classic fraud pattern: new account, foreign, large amount."""
        txn = {"amount": 150_000_000, "location": "RU",
               "frequency": 1, "hour": 3, "is_new_account": True}
        factors = {k: 1.0 for k in ["hour_factor", "amount_factor",
                                     "location_factor", "frequency_factor"]}
        factors["is_profiled"] = False
        result = evaluate_rules(txn, factors)
        # 50 (amount) + 30 (location) + 15 (hour) + 20 (new) = 115
        assert result["rule_score"] >= 70
        status, _ = determine_status(result["rule_score"])
        assert status == "BLOCKED"
