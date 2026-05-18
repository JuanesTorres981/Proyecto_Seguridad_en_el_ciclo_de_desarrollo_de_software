"""
train.py — Entrena el modelo Random Forest para detección de fraude.

"""

import csv
import math
import pickle
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

MODEL_DIR = Path("ml/model")
MODEL_PATH = MODEL_DIR / "random_forest.pkl"
REAL_DATA_PATH = Path("ml/data/creditcard.csv")


# Carga de datos reales (Kaggle Credit Card Fraud)

def load_real_data() -> tuple:
    """
    Carga creditcard.csv y adapta sus columnas a nuestro feature vector.

    El dataset tiene:
      Time   - segundos desde la primera transaccion del dataset
      V1-V28 - features PCA (anonimizadas por privacidad del banco)
      Amount - monto en EUR
      Class  - 0 (legitima) o 1 (fraude)

    Adaptacion a nuestro feature vector de 11 dimensiones:
      [0]  amount_log       <- log(Amount + 1)
      [1]  is_foreign       <- proxy: V3 < -1.5 correlaciona con ubicacion inusual
      [2]  frequency        <- proxy: V4 normalizado (velocidad de transacciones)
      [3]  hour_sin         <- sin(hora * 2pi/24), hora derivada de Time
      [4]  hour_cos         <- cos(hora * 2pi/24)
      [5]  is_new_account   <- proxy: V14 < -5.0 (riesgo de cuenta nueva)
      [6]  hour_deviation   <- proxy conductual: |V12| normalizado
      [7]  amount_deviation <- proxy conductual: |V17| normalizado
      [8]  location_dev     <- proxy: |V10| normalizado
      [9]  frequency_dev    <- proxy: |V11| normalizado
      [10] is_profiled      <- 1.0 (dataset tiene contexto historico implicito)

    Nota: V1-V28 son PCA por privacidad, usamos los componentes con mayor
    correlacion conocida con fraude como proxies para nuestras dimensiones.
    """
    print(f"Cargando datos reales desde {REAL_DATA_PATH}...")

    X, y = [], []
    TWO_PI = 2 * math.pi

    with open(REAL_DATA_PATH, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                time_val = float(row["Time"])
                amount   = float(row["Amount"])
                label    = int(float(row["Class"]))

                v3  = float(row["V3"])
                v4  = float(row["V4"])
                v10 = float(row["V10"])
                v11 = float(row["V11"])
                v12 = float(row["V12"])
                v14 = float(row["V14"])
                v17 = float(row["V17"])

                # Derivar hora del dia (dataset cubre 2 dias = 172800 seg)
                hour = (time_val % 86400) / 3600
                angle = hour * TWO_PI / 24

                amount_log   = math.log(amount + 1)
                is_foreign   = 1.0 if v3 < -1.5 else 0.0
                freq_proxy   = min(max((v4 + 5) / 3.0, 0.0), 5.0)
                hour_dev     = min(abs(v12) / 3.0, 1.0)
                amount_dev   = min(abs(v17) / 3.0, 1.0)
                location_dev = min(abs(v10) / 3.0, 1.0)
                freq_dev     = min(abs(v11) / 3.0, 1.0)
                is_new_acc   = 1.0 if v14 < -5.0 else 0.0

                X.append([
                    amount_log,
                    is_foreign,
                    freq_proxy,
                    math.sin(angle),
                    math.cos(angle),
                    is_new_acc,
                    hour_dev,
                    amount_dev,
                    location_dev,
                    freq_dev,
                    1.0,
                ])
                y.append(label)

            except (ValueError, KeyError):
                continue

    print(f"Cargadas {len(X)} transacciones ({sum(y)} fraudes, {len(y)-sum(y)} legitimas)")
    print(f"Tasa de fraude real: {sum(y)/len(y)*100:.3f}%")
    return X, y


# Datos sinteticos (fallback si no hay datos reales)

def generate_synthetic_dataset(n_normal=5000, n_fraud=1000, seed=42) -> tuple:
    print("AVISO: No se encontro ml/data/creditcard.csv — usando datos sinteticos.")
    print("Para datos reales: https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud\n")

    rng = random.Random(seed)
    TWO_PI = 2 * math.pi
    X, y = [], []

    def sample(is_fraud):
        if not is_fraud:
            amount = rng.uniform(50_000, 5_000_000)
            is_foreign = 0; freq = rng.uniform(1, 3); hour = rng.uniform(7, 21)
            is_new = 0.0; hour_dev = rng.uniform(0, 0.3); amount_dev = rng.uniform(0, 0.3)
            loc_dev = 0.0; freq_dev = rng.uniform(0, 0.3)
        else:
            t = rng.random()
            if t < 0.35:
                amount = rng.uniform(50_000_000, 500_000_000)
                is_foreign = rng.choice([0, 0, 1]); freq = rng.uniform(1, 3)
                hour = rng.uniform(0, 23); is_new = rng.choice([0.0, 1.0])
            elif t < 0.6:
                amount = rng.uniform(500_000, 20_000_000)
                is_foreign = 1; freq = rng.uniform(1, 4)
                hour = rng.choice(list(range(0, 6)) + list(range(22, 24)))
                is_new = rng.choice([0.0, 0.0, 1.0])
            elif t < 0.8:
                amount = rng.uniform(1_000, 500_000)
                is_foreign = rng.choice([0, 1]); freq = rng.uniform(6, 20)
                hour = rng.uniform(0, 23); is_new = rng.choice([0.0, 1.0])
            else:
                amount = rng.uniform(10_000_000, 100_000_000)
                is_foreign = rng.choice([0, 0, 1]); freq = rng.uniform(1, 3)
                hour = rng.choice(list(range(0, 6)) + list(range(21, 24))); is_new = 1.0

            hour_dev = rng.uniform(0.5, 1.0); amount_dev = rng.uniform(0.5, 1.0)
            loc_dev = rng.uniform(0.5, 1.0); freq_dev = rng.uniform(0.3, 1.0)

        angle = hour * TWO_PI / 24
        is_profiled = 1.0 if rng.random() > 0.2 else 0.0
        return [
            math.log(amount + 1), float(is_foreign), float(freq),
            math.sin(angle), math.cos(angle), float(is_new),
            hour_dev, amount_dev, loc_dev, freq_dev, is_profiled,
        ]

    for _ in range(n_normal):
        X.append(sample(False)); y.append(0)
    for _ in range(n_fraud):
        X.append(sample(True)); y.append(1)
    return X, y


# Entrenamiento

def train():
    try:
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.model_selection import train_test_split
        from sklearn.metrics import (classification_report, roc_auc_score,
                                     confusion_matrix, average_precision_score)
        import numpy as np
    except ImportError:
        print("ERROR: scikit-learn no instalado. Ejecuta: pip install scikit-learn")
        sys.exit(1)

    print("=" * 60)
    print("  Bubbles - Entrenamiento Random Forest")
    print("=" * 60 + "\n")

    if REAL_DATA_PATH.exists():
        X, y = load_real_data()
        data_source = "REAL (Kaggle Credit Card Fraud — 284k transacciones)"
    else:
        X, y = generate_synthetic_dataset()
        data_source = "SINTETICO (fallback)"

    print(f"\nFuente: {data_source}")

    X_arr = np.array(X)
    y_arr = np.array(y)

    X_train, X_test, y_train, y_test = train_test_split(
        X_arr, y_arr, test_size=0.2, random_state=42, stratify=y_arr
    )
    print(f"Train: {len(X_train)} | Test: {len(X_test)}")
    print(f"Fraudes en train: {y_train.sum()} ({y_train.mean()*100:.3f}%)\n")

    print("Entrenando Random Forest (class_weight=balanced para datos desbalanceados)...")
    model = RandomForestClassifier(
        n_estimators=300,
        max_depth=15,
        min_samples_leaf=3,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1]

    auc_roc = roc_auc_score(y_test, y_prob)
    auc_pr  = average_precision_score(y_test, y_prob)
    cm = confusion_matrix(y_test, y_pred)

    print("\n=== Metricas de Rendimiento ===")
    print(classification_report(y_test, y_pred,
                                 target_names=["Legitima", "Fraude"], digits=4))
    print(f"AUC-ROC: {auc_roc:.4f}   (con datos reales esperado 0.97-0.99)")
    print(f"AUC-PR:  {auc_pr:.4f}   (metrica clave con datos desbalanceados)")
    print(f"\nMatriz de confusion:")
    print(f"  Legitimas  -> Correctas:   {cm[0][0]:6d} | Falsas alarmas: {cm[0][1]:4d}")
    print(f"  Fraudes    -> Detectados:  {cm[1][1]:6d} | No detectados:  {cm[1][0]:4d}")
    fn = cm[1][0]
    print(f"\n  Fraudes no detectados: {fn}/{cm[1].sum()} ({fn/cm[1].sum()*100:.1f}%)")

    feature_names = [
        "amount_log", "is_foreign", "frequency",
        "hour_sin", "hour_cos", "is_new_account",
        "hour_deviation", "amount_deviation",
        "location_deviation", "frequency_deviation",
        "is_profiled",
    ]
    importances = sorted(
        zip(feature_names, model.feature_importances_),
        key=lambda x: x[1], reverse=True,
    )
    print("\n=== Importancia de Features (para documentacion SSDLC) ===")
    for name, imp in importances:
        bar = "█" * int(imp * 50)
        print(f"  {name:<22} {imp:.4f}  {bar}")

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(model, f)

    print(f"\nModelo guardado en {MODEL_PATH}")
    print(f"Fuente de entrenamiento: {data_source}")
    print("\nSiguiente paso: uvicorn app.main:app --reload")


if __name__ == "__main__":
    train()
