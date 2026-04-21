import sys
import os

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
app_path = os.path.join(base_dir, "app")

sys.path.append(app_path)

from app.transactions import evaluate_transaction

def test_transaccion_aprobada():
    # Escenario: Transaccion normal con riesgo = 0
    txn = {
        "amount": 1000000, 
        "location": "CO", 
        "frequency": 1, 
        "hour": "14:00", 
        "creation_date": "10/25"
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
        "hour": "12:30", 
        "creation_date": "10/25"
    }
    result = evaluate_transaction(txn)
    
    assert result["risk"] == 50
    assert result["status"] == "REVIEW"
    assert result["message"] == "Wait, tu transaccion sera revisada a profundidad (*￣3￣)╭"


def test_transaccion_bloqueada_por_monto_y_cuenta_nueva():
    # Escenario: Transaccion bloqueada altamente sospechosa = 80
    txn = {
        "amount": 150000000, 
        "location": "CO", 
        "frequency": 1, 
        "hour": "10:15", 
        "creation_date": "04/26" 
    }
    result = evaluate_transaction(txn)
    
    assert result["risk"] == 80  
    assert result["status"] == "BLOCKED"
    assert result["message"] == "Bloqueadoooo :p"


def test_transaccion_bloqueada_por_comportamiento_anomalo():
    # Escenario: Transaccion altamente sospechosa con riesgo = 85
    txn = {
        "amount": 2000000, 
        "location": "MX", 
        "frequency": 6, 
        "hour": "03:45", 
        "creation_date": "10/25"
    }
    result = evaluate_transaction(txn)
    
    assert result["risk"] == 85
    assert result["status"] == "BLOCKED"
    assert result["message"] == "Bloqueadoooo :p"


def test_seguridad_capa_1_datos_maliciosos():
    # Escenario: Intento de inyectar datos basura
    txn = {
        "amount": "un millon", 
        "location": "colombia", 
        "frequency": -2, 
        "hour": "99:99", 
        "creation_date": "futuro"
    }
    result = evaluate_transaction(txn)
    
    assert result["status"] == "ERROR"
    assert result["risk"] == 100
    assert "Datos inválidos detectados" in result["message"]