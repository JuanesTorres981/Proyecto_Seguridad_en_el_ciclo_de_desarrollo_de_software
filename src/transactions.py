def evaluate_transaction(amount, location, frequency):
    risk = 0
    if amount > 1000000:
        risk += 50
    if location != "CO":
        risk += 30
    if frequency > 3:
        risk += 40

    if risk > 70:
        return "bloqueadoooo :p.", risk
    return "aprobado por Chayanne ;D.", risk