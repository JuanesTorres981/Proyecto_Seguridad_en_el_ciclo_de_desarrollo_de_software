def evaluate_transaction(amount, location, frequency):
    risk = 0

    if amount > 1_000_000:
        risk += 50
    if location != "CO":
        risk += 30
    if frequency > 3:
        risk += 40

    if risk >= 70:
        return {
            "status": "BLOCKED",
            "message": "bloqueadoooo :p.",
            "risk": risk
        }

    return {
        "status": "APPROVED",
        "message": "aprobado por Chayanne ;D.",
        "risk": risk
    }