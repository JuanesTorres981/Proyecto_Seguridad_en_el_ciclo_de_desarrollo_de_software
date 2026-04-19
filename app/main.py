from transactions import evaluate_transaction
import json
from datetime import datetime


def process_transaction(transaction):
    amount = transaction["amount"]
    location = transaction["location"]
    frequency = transaction["frequency"]

    result = evaluate_transaction(amount, location, frequency)

    # Construir registro completo
    record = {
        "transaction_id": transaction["id"],
        "user": transaction["user"],
        "amount": amount,
        "location": location,
        "frequency": frequency,
        "timestamp": str(datetime.now()),
        "status": result["status"],
        "risk": result["risk"]
    }

    return record


if __name__ == "__main__":

    transactions = [
        {"id": 1, "user": "Ana", "amount": 50000, "location": "CO", "frequency": 1},
        {"id": 2, "user": "Luis", "amount": 2000000, "location": "CO", "frequency": 1},
        {"id": 3, "user": "Sofía", "amount": 100000, "location": "US", "frequency": 5}
    ]

    results = []

    for t in transactions:
        record = process_transaction(t)
        results.append(record)

        print(record)
        print("-" * 40)

    # Guardar logs en JSON
    with open("transactions_log.json", "w") as f:
        json.dump(results, f, indent=4)