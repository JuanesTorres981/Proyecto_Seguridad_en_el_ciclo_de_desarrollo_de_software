from datetime import datetime

def rule_high_amount(amount: float, factor: float) -> tuple[int, str | None]:
    if amount > 100_000_000:
        pts = int(50 * factor)
        return pts, f"Very high amount (>{amount/1e6:.0f}M COP)" if pts > 0 else None
    elif amount > 10_000_000:
        pts = int(20 * factor)
        return pts, f"High amount (>{amount/1e6:.0f}M COP)" if pts > 0 else None
    elif amount > 5_000_000:
        pts = int(10 * factor)
        return pts, f"Elevated amount (>{amount/1e6:.0f}M COP)" if pts > 0 else None
    return 0, None

def rule_unusual_location(location: str, factor: float) -> tuple[int, str | None]:
    if location != "CO":
        pts = int(30 * factor)
        return pts, f"Foreign location ({location})" if pts > 0 else None
    return 0, None

def rule_high_frequency(frequency: int, factor: float) -> tuple[int, str | None]:
    if frequency > 5:
        pts = int(40 * factor)
        return pts, f"Very high frequency ({frequency} txns/hr)" if pts > 0 else None
    elif frequency > 3:
        pts = int(15 * factor)
        return pts, f"Elevated frequency ({frequency} txns/hr)" if pts > 0 else None
    return 0, None

def rule_odd_hour(hour: int, factor: float) -> tuple[int, str | None]:
    if hour < 6 or hour > 22:
        pts = int(15 * factor)
        return pts, f"Transaction at {hour:02d}:00 (unusual hours)" if pts > 0 else None
    return 0, None

def rule_new_account(is_new: bool) -> tuple[int, str | None]:
    if is_new:
        return 20, "New account"
    return 0, None

def evaluate_rules(transaction: dict, behavioral_factors: dict) -> dict:
    amount = float(transaction.get("amount", 0))
    location = str(transaction.get("location", "CO"))
    frequency = int(transaction.get("frequency", 1))
    hour = int(transaction.get("hour", 12))
    is_new = bool(transaction.get("is_new_account", False))

    hf = behavioral_factors.get("hour_factor", 1.0)
    af = behavioral_factors.get("amount_factor", 1.0)
    lf = behavioral_factors.get("location_factor", 1.0)
    ff = behavioral_factors.get("frequency_factor", 1.0)

    rules = [
        rule_high_amount(amount, af),
        rule_unusual_location(location, lf),
        rule_high_frequency(frequency, ff),
        rule_odd_hour(hour, hf),
        rule_new_account(is_new),
    ]

    raw_scores = [
        rule_high_amount(amount, 1.0)[0],
        rule_unusual_location(location, 1.0)[0],
        rule_high_frequency(frequency, 1.0)[0],
        rule_odd_hour(hour, 1.0)[0],
        rule_new_account(is_new)[0],
    ]

    total_score = sum(pts for pts, _ in rules)
    raw_total = sum(raw_scores)
    flags = [msg for _, msg in rules if msg is not None]

    behavioral_adjustment = float(raw_total - total_score)

    return {
        "rule_score": total_score,
        "flags": flags,
        "behavioral_adjustment": behavioral_adjustment,
    }

def determine_status(final_score: int) -> tuple[str, str]:
    if final_score >= 70:
        return "BLOCKED", "Transaction blocked due to high fraud risk."
    elif final_score >= 45:
        return "REVIEW", "Transaction flagged for manual review."
    else:
        return "APPROVED", "Transaction approved."
