from transactions import evaluate_transaction
import json
from datetime import datetime

def process_transaction(transaction):
    result = evaluate_transaction(transaction)

    record = {
        "transaction_id": transaction["id"],
        "user": transaction["user"],
        "amount": transaction.get("amount"),
        "location": transaction.get("location"),
        "frequency": transaction.get("frequency"),
        "timestamp": str(datetime.now()),
        "status": result["status"],
        "risk": result["risk"],
        "message": result["message"]
    }
    return record

if __name__ == "__main__":
    transactions = [
        {"id": 1, "user": "Anadearmas", "amount": 2500000, "location": "CO", "frequency": 1, "hour": 14, "is_new_account": False},
        {"id": 2, "user": "Luismi", "amount": 150000000, "location": "CO", "frequency": 1, "hour": 15, "is_new_account": False},
        {"id": 3, "user": "Sofiadelbarrio", "amount": 15000000, "location": "US", "frequency": 2, "hour": 10, "is_new_account": True},
        {"id": 4, "user": "Estebanco", "amount": 50000, "location": "RU", "frequency": 7, "hour": 3, "is_new_account": False}
    ]

    results = []
    for t in transactions:
        record = process_transaction(t)
        results.append(record)
        print(record)
        print("-" * 40)

    # Guardar logs en JSON auditable
    with open("transactions_log.json", "w") as f:
        json.dump(results, f, indent=4)