from app.transactions import evaluate_transaction

def test_transaccion_normal():
    result = evaluate_transaction(50000, "CO", 1)

    assert result["status"] == "APPROVED"
    assert result["risk"] == 0

def test_monto_alto():
    result = evaluate_transaction(2000000, "CO", 1)

    assert result["status"] == "BLOCKED"
    assert result["risk"] >= 50

def test_comportamiento_sospechoso():
    result = evaluate_transaction(100000, "US", 5)

    assert result["status"] == "BLOCKED"
    assert result["risk"] >= 70

def test_valores_limite():
    result = evaluate_transaction(1000000, "CO", 3)

    # justo en el límite, debería ser aprobado si usas >=70 para bloquear
    assert result["status"] == "APPROVED"