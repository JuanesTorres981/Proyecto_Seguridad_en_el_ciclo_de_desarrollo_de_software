from datetime import datetime

def evaluate_transaction(transaction: dict) -> dict:
    risk = 0
    amount = transaction.get("amount", 0)
    location = transaction.get("location", "CO")
    frequency = transaction.get("frequency", 1)
    hour = transaction.get("hour", 12)
    is_new_account = transaction.get("is_new_account", False)

    # 1. Riesgo en el monto
    if amount > 100000000:
        risk += 50
    elif amount > 10000000:
        risk += 20
    elif amount > 5000000:
        risk += 10

    # 2. Riesgo en el lugar de transacción
    if location != "CO":
        risk += 30

    # 3. Riesgo en los frecuencia
    if frequency > 5:
        risk += 40
    elif frequency > 3:
        risk += 15

    # 4. Riesgo en el horario que se realiza
    if hour < 6 or hour > 22:    
        risk += 15
    
    # 5. Riesgo si la cuenta es nueva
    if is_new_account:
        risk += 20

    # Determinar el estado basado en el puntaje
    if risk >= 70:
        status = "BLOCKED"
        message = "Bloqueadoooo :p"
    elif risk >= 50:
        status = "REVIEW"
        message = "Wait, tu transaccion sera revisada a profundidad (*￣3￣)╭"
    else:
        status = "APPROVED"
        message = "Aprobado por Chayanne ;D"

    return {
        "status": status,
        "message": message,
        "risk": risk,
        "processed_at": datetime.now().isoformat()
    }