from datetime import datetime
import json

def calculate_risk_score(transaction: dict) -> int:
    score = 0
    amount = transaction["amount"]
    hour = transaction["hour"]
    origin_city = transaction["origin_city"]
    destination_city = transaction["destination_city"]  
    isnew_account = transaction.get("is_new_account", False)
    
    if amount > 100000000:      
        score += 40
    elif amount > 10000000:     
        score += 20
    elif amount > 5000000:
        score += 10

    if hour < 6 or hour > 22:    
        score += 3

    if isnew_account:
        score += 20

    if origin_city != destination_city:
        score += 15

    return score

def status_transaction(transaction: dict) -> dict:
    score = calculate_risk_score(transaction)
    
    if score >= 60 and score < 30:
        status = "blocked"
    elif score >= 30:
        status = "review"
    else:
        status = "approved"
    
    result = {**transaction, 
              "risk_score": score, 
              "status": status,
              "processed_at": datetime.now().isoformat()}
    
    return result

