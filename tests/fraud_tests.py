import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.transactions import evaluate_transaction

def test_transaccion_aprobada():
    # Escenario: Transaccion normal con riesgo = 0
    txn = {
        "amount": 1000000, 
        "location": "CO", 
        "frequency": 1, 
        "hour": 14, 
        "is_new_account": False
    }
    result = evaluate_transaction(txn)
    
    assert result["risk"] == 0
    assert result["status"] == "APPROVED"
    assert result["message"] == "Aprobado por Chayanne ;D"

def test_transaccion_en_revision():
    # Escenario: Transaccion de revision con riesgo = 50
    txn = {
        "amount": 15000000, 
        "location": "US", 
        "frequency": 1, 
        "hour": 12, 
        "is_new_account": False
    }
    result = evaluate_transaction(txn)
    
    assert result["risk"] == 50
    assert result["status"] == "REVIEW"
    assert result["message"] == "Wait, tu transaccion sera revisada a profundidad (*￣3￣)╭"

def test_transaccion_bloqueada_por_monto_y_cuenta_nueva():
    # Escenario: Transaccion de revision con riesgo sospechosa = 70
    txn = {
        "amount": 150000000, 
        "location": "CO", 
        "frequency": 1, 
        "hour": 10, 
        "is_new_account": True
    }
    result = evaluate_transaction(txn)
    
    assert result["risk"] == 70
    assert result["status"] == "BLOCKED"
    assert result["message"] == "Bloqueadoooo :p"

def test_transaccion_bloqueada_por_comportamiento_anomalo():
    # Escenario: Transaccion altamente sospechosa con riesgo 85
    txn = {
        "amount": 2000000, 
        "location": "MX", 
        "frequency": 6, 
        "hour": 3, 
        "is_new_account": False
    }
    result = evaluate_transaction(txn)
    
    assert result["risk"] == 85
    assert result["status"] == "BLOCKED"
    assert result["message"] == "Bloqueadoooo :p"