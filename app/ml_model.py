import pickle
import math
from pathlib import Path

MODEL_PATH = Path("ml/model/random_forest.pkl")


def _build_feature_vector(transaction: dict, behavioral_factors: dict) -> list[float]:
    """
    Features:
    [0] amount_log       — log(amount) to handle COP magnitude range
    [1] is_foreign       — 1 if location != CO
    [2] frequency        — transactions per hour
    [3] hour_sin         — sine of hour (encodes circularity)
    [4] hour_cos         — cosine of hour (encodes circularity)
    [5] is_new_account   — 1 if new account
    [6] hour_dev         — behavioral deviation for hour (0/0.5/1)
    [7] amount_dev       — behavioral deviation for amount (0/0.5/1)
    [8] location_dev     — behavioral deviation for location (0/1)
    [9] frequency_dev    — behavioral deviation for frequency (0/0.5/1)
    [10] is_profiled     — 1 if user has enough history
    """
    amount = float(transaction.get("amount", 1))
    location = str(transaction.get("location", "CO"))
    frequency = int(transaction.get("frequency", 1))
    hour = int(transaction.get("hour", 12))
    is_new = int(transaction.get("is_new_account", False))

    amount_log = math.log(amount + 1)
    is_foreign = 1 if location != "CO" else 0

    TWO_PI = 2 * math.pi
    hour_angle = hour * TWO_PI / 24
    hour_sin = math.sin(hour_angle)
    hour_cos = math.cos(hour_angle)

    hour_dev = behavioral_factors.get("hour_factor", 1.0)
    amount_dev = behavioral_factors.get("amount_factor", 1.0)
    location_dev = behavioral_factors.get("location_factor", 1.0)
    freq_dev = behavioral_factors.get("frequency_factor", 1.0)
    is_profiled = 1 if behavioral_factors.get("is_profiled", False) else 0

    return [
        amount_log,
        is_foreign,
        float(frequency),
        hour_sin,
        hour_cos,
        float(is_new),
        hour_dev,
        amount_dev,
        location_dev,
        freq_dev,
        float(is_profiled),
    ]


def predict_fraud_probability(transaction: dict, behavioral_factors: dict) -> float:
    features = _build_feature_vector(transaction, behavioral_factors)

    if not MODEL_PATH.exists():
        score = 0.0
        amount_log = features[0]
        is_foreign = features[1]
        frequency = features[2]
        hour_dev = features[6]
        amount_dev = features[7]
        freq_dev = features[9]

        if amount_log > math.log(100_000_000):
            score += 0.5 * amount_dev
        elif amount_log > math.log(10_000_000):
            score += 0.2 * amount_dev

        score += 0.3 * is_foreign * features[8]
        if frequency > 5:
            score += 0.4 * freq_dev
        score += 0.15 * hour_dev

        return min(score, 1.0)

    with open(MODEL_PATH, "rb") as f:
        model = pickle.load(f)

    prob = model.predict_proba([features])[0][1] 
    return float(prob)


def get_feature_names() -> list[str]:
    return [
        "amount_log", "is_foreign", "frequency",
        "hour_sin", "hour_cos", "is_new_account",
        "hour_deviation", "amount_deviation",
        "location_deviation", "frequency_deviation",
        "is_profiled",
    ]
