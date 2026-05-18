import math
import json

def _circular_stats(hours: list[int]) -> tuple[float, float]:
    if not hours:
        return 12.0, 24.0  

    TWO_PI = 2 * math.pi
    angles = [h * TWO_PI / 24 for h in hours]

    mean_sin = sum(math.sin(a) for a in angles) / len(angles)
    mean_cos = sum(math.cos(a) for a in angles) / len(angles)

    R = math.sqrt(mean_sin ** 2 + mean_cos ** 2)  
    mean_angle = math.atan2(mean_sin, mean_cos)
    mean_hour = (mean_angle * 24 / TWO_PI) % 24

    circ_std_rad = math.sqrt(-2 * math.log(R + 1e-9))
    circ_std_hours = circ_std_rad * 24 / TWO_PI

    return mean_hour, circ_std_hours


def _circular_deviation(hour: int, hours_history: list[int]) -> float:
    n = len(hours_history)
    if n < 5:
        return 1.0 

    mean_h, std_h = _circular_stats(hours_history)
    if std_h < 0.1:
        std_h = 0.1  

    diff = abs(hour - mean_h)
    diff = min(diff, 24 - diff)  
    z = diff / std_h

    if z < 1.0:
        return 0.0   
    elif z < 2.0:
        return 0.5   
    else:
        return 1.0   

def _amount_deviation(amount: float, profile: dict) -> float:
    n = profile.get("txn_count", 0)
    if n < 5:
        return 1.0

    mean = profile.get("amount_mean", 0)
    m2 = profile.get("amount_m2", 0)

    if n < 2:
        variance = float("inf")
    else:
        variance = m2 / (n - 1)

    std = math.sqrt(variance) if variance > 0 else 1.0

    if std < 1.0:
        std = 1.0

    z = abs(amount - mean) / std

    if z < 1.0:
        return 0.0
    elif z < 2.5:
        return 0.5
    else:
        return 1.0

def _location_deviation(location: str, known_locations: list[str]) -> float:
    """0 if user has transacted from here before, 1 if brand new location."""
    if not known_locations:
        return 1.0
    return 0.0 if location in known_locations else 1.0

def _frequency_deviation(frequency: int, profile: dict) -> float:
    n = profile.get("txn_count", 0)
    if n < 5:
        return 1.0

    mean = profile.get("freq_mean", 1.0)
    m2 = profile.get("freq_m2", 0)

    if n < 2:
        return 1.0

    variance = m2 / (n - 1)
    std = math.sqrt(variance) if variance > 0 else 1.0
    if std < 0.1:
        std = 0.1

    z = abs(frequency - mean) / std

    if z < 1.0:
        return 0.0
    elif z < 2.0:
        return 0.5
    else:
        return 1.0
    
def compute_behavioral_factors(transaction: dict, profile: dict | None) -> dict:
    if profile is None or profile.get("txn_count", 0) < 5:
        return {
            "hour_factor": 1.0,
            "amount_factor": 1.0,
            "location_factor": 1.0,
            "frequency_factor": 1.0,
            "is_profiled": False,
        }

    recent_hours = profile.get("recent_hours", [])
    known_locations = profile.get("known_locations", [])

    return {
        "hour_factor": _circular_deviation(
            transaction["hour"], recent_hours
        ),
        "amount_factor": _amount_deviation(transaction["amount"], profile),
        "location_factor": _location_deviation(
            transaction["location"], known_locations
        ),
        "frequency_factor": _frequency_deviation(transaction["frequency"], profile),
        "is_profiled": True,
    }

def build_profile_summary(profile: dict | None) -> dict:
    if profile is None:
        return {
            "transaction_count": 0,
            "avg_amount": 0.0,
            "std_amount": 0.0,
            "avg_hour": 0.0,
            "known_locations": [],
            "avg_frequency": 0.0,
            "is_profiled": False,
            "last_updated": None,
        }

    n = profile.get("txn_count", 0)
    m2_a = profile.get("amount_m2", 0)
    variance = m2_a / (n - 1) if n >= 2 else 0
    std_amount = math.sqrt(variance) if variance > 0 else 0

    recent_hours = profile.get("recent_hours", [])
    avg_hour, _ = _circular_stats(recent_hours) if recent_hours else (0, 0)

    return {
        "transaction_count": n,
        "avg_amount": round(profile.get("amount_mean", 0), 2),
        "std_amount": round(std_amount, 2),
        "avg_hour": round(avg_hour, 1),
        "known_locations": profile.get("known_locations", []),
        "avg_frequency": round(profile.get("freq_mean", 0), 2),
        "is_profiled": n >= 5,
        "last_updated": profile.get("last_updated"),
    }
