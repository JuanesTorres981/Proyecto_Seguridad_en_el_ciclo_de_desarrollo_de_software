from datetime import datetime
from validation import validate_transaction_data

def evaluate_transaction(transaction: dict) -> dict:
    clean_data, errors = validate_transaction_data(transaction)
    
    if errors:
        return {
            "status": "ERROR",
            "message": f"Datos inválidos detectados: {errors}",
            "risk": 100,  
            "processed_at": datetime.now().isoformat()
        }
    
    risk = 0
    amount = clean_data["amount"]
    location = clean_data["location"]
    frequency = clean_data["frequency"]
    hour = clean_data["hour"]
    account_months = clean_data["creation_date"] 

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
    
    # 5. Riesgo en la antiguedad de la cuenta
    if account_months == 0:
        risk += 30
    elif account_months <= 3:
        risk += 15  
    elif account_months >= 12:
        risk -= 10  

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