"""
simulate.py — Simulador de usuarios y transacciones para Bubbles.

USO:
    python simulate.py                  → menú interactivo completo
    python simulate.py --seed-all       → crea todos los perfiles base y sale
    python simulate.py --user juan      → muestra perfil de un usuario

USUARIOS PREDEFINIDOS:
    oficinista_ana   → transfiere en horario laboral, montos medianos, solo CO
    nochero_carlos   → activo entre 1am-4am, montos variados, solo CO
    viajero_sofia    → múltiples países, montos altos, horarios mixtos
"""

import json
import sys
import time
import argparse
import random
import math
import urllib.request
import urllib.error
from datetime import datetime

BASE_URL = "http://localhost:8000"

# ─── Colores para consola ─────────────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
RESET  = "\033[0m"

STATUS_COLOR = {
    "APPROVED": GREEN,
    "REVIEW":   YELLOW,
    "BLOCKED":  RED,
}

# ─── HTTP helpers (sin dependencias externas) ─────────────────────────────────

def post(endpoint: str, body: dict) -> dict:
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        f"{BASE_URL}{endpoint}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


def get(endpoint: str) -> dict:
    with urllib.request.urlopen(f"{BASE_URL}{endpoint}", timeout=10) as resp:
        return json.loads(resp.read())


def check_api() -> bool:
    try:
        get("/health")
        return True
    except Exception:
        return False


# ─── Perfiles de usuarios predefinidos ────────────────────────────────────────

PREDEFINED_USERS = {
    "oficinista_ana": {
        "description": "Ana — Empleada bancaria, horario de oficina, pagos domésticos",
        "normal_behavior": {
            "hours":      list(range(8, 18)),       # 8am–6pm
            "amounts":    (200_000, 2_000_000),     # rango COP
            "locations":  ["CO"],
            "frequency":  (1, 2),
        },
        "seed_count": 15,
    },
    "nochero_carlos": {
        "description": "Carlos — Freelancer, trabaja de noche, activo 1am–4am",
        "normal_behavior": {
            "hours":      [1, 2, 3, 4],
            "amounts":    (500_000, 5_000_000),
            "locations":  ["CO"],
            "frequency":  (1, 3),
        },
        "seed_count": 15,
    },
    "viajero_sofia": {
        "description": "Sofía — Consultora internacional, viaja frecuentemente",
        "normal_behavior": {
            "hours":      list(range(6, 23)),
            "amounts":    (2_000_000, 20_000_000),
            "locations":  ["CO", "US", "MX", "ES"],
            "frequency":  (1, 4),
        },
        "seed_count": 15,
    },
}

# ─── Escenarios de prueba ──────────────────────────────────────────────────────

def make_test_scenarios(user_id: str, profile_key: str) -> list[dict]:
    """Genera escenarios de prueba personalizados según el perfil del usuario."""

    normal = PREDEFINED_USERS[profile_key]["normal_behavior"]
    normal_hour   = random.choice(normal["hours"])
    normal_loc    = random.choice(normal["locations"])
    normal_amount = random.randint(*normal["amounts"])

    scenarios = [
        {
            "name": "✅ Transacción completamente normal",
            "desc": "Dentro del patrón habitual del usuario",
            "txn": {
                "user_id": user_id,
                "amount": normal_amount,
                "location": normal_loc,
                "hour": normal_hour,
                "frequency": random.randint(*normal["frequency"]),
                "is_new_account": False,
            },
            "expected": "APPROVED",
        },
        {
            "name": "🌍 Ubicación inusual",
            "desc": "Misma hora y monto normal, pero desde país desconocido",
            "txn": {
                "user_id": user_id,
                "amount": normal_amount,
                "location": "RU",
                "hour": normal_hour,
                "frequency": 1,
                "is_new_account": False,
            },
            "expected": "REVIEW or BLOCKED",
        },
        {
            "name": "💰 Monto muy elevado",
            "desc": "Monto 50x mayor al promedio del usuario",
            "txn": {
                "user_id": user_id,
                "amount": min(normal["amounts"][1] * 50, 500_000_000),
                "location": normal_loc,
                "hour": normal_hour,
                "frequency": 1,
                "is_new_account": False,
            },
            "expected": "REVIEW or BLOCKED",
        },
        {
            "name": "🚨 Patrón de fraude clásico",
            "desc": "Monto enorme + país extraño + frecuencia alta + hora inusual",
            "txn": {
                "user_id": user_id,
                "amount": 200_000_000,
                "location": "RU",
                "hour": 4 if profile_key != "nochero_carlos" else 14,
                "frequency": 8,
                "is_new_account": False,
            },
            "expected": "BLOCKED",
        },
    ]

    # Escenario especial para el nochero: 3am debería ser APROBADO
    if profile_key == "nochero_carlos":
        scenarios.insert(1, {
            "name": "🌙 3am — Normal para Carlos (hora habitual)",
            "desc": "Para Carlos las 3am son completamente normales — el sistema debería reconocerlo",
            "txn": {
                "user_id": user_id,
                "amount": 800_000,
                "location": "CO",
                "hour": 3,
                "frequency": 1,
                "is_new_account": False,
            },
            "expected": "APPROVED (behavioral profile activo)",
        })

    return scenarios


# ─── Funciones de simulación ──────────────────────────────────────────────────

def seed_user(user_id: str, profile_key: str, verbose: bool = True) -> None:
    """Envía N transacciones normales para construir el perfil conductual del usuario."""
    config = PREDEFINED_USERS[profile_key]
    normal = config["normal_behavior"]
    n = config["seed_count"]

    if verbose:
        print(f"\n{CYAN}{BOLD}Construyendo perfil de {user_id}...{RESET}")
        print(f"{DIM}{config['description']}{RESET}")
        print(f"{DIM}Enviando {n} transacciones base...{RESET}\n")

    rng = random.Random(42)
    for i in range(n):
        hour   = rng.choice(normal["hours"])
        amount = rng.randint(*normal["amounts"])
        loc    = rng.choice(normal["locations"])
        freq   = rng.randint(*normal["frequency"])

        txn = {
            "user_id":        user_id,
            "amount":         float(amount),
            "location":       loc,
            "hour":           hour,
            "frequency":      freq,
            "is_new_account": False,
        }
        try:
            result = post("/api/transactions", txn)
            if verbose:
                bar = "█" * (i + 1) + "░" * (n - i - 1)
                print(f"\r  [{bar}] {i+1}/{n}", end="", flush=True)
        except Exception as e:
            print(f"\n{RED}Error en transacción {i+1}: {e}{RESET}")

    if verbose:
        print(f"\n{GREEN}  ✓ Perfil construido ({n} transacciones){RESET}")


def print_transaction_result(result: dict, scenario: dict = None) -> None:
    """Imprime el resultado de una transacción de forma legible."""
    status = result.get("status", "?")
    color  = STATUS_COLOR.get(status, RESET)

    if scenario:
        print(f"\n  {BOLD}{scenario['name']}{RESET}")
        print(f"  {DIM}{scenario['desc']}{RESET}")
        if "expected" in scenario:
            print(f"  {DIM}Esperado: {scenario['expected']}{RESET}")

    print(f"\n  Estado:      {color}{BOLD}{status}{RESET}")
    print(f"  Risk Score:  {result.get('risk_score', '?')} / 100")
    print(f"  Rule Score:  {result.get('rule_score', '?')}")
    print(f"  ML Score:    {result.get('ml_score', '?'):.1f}")

    adj = result.get("behavioral_adjustment", 0)
    if adj > 0:
        print(f"  {GREEN}Ajuste conductual: -{adj:.0f} puntos (perfil personalizado activo){RESET}")
    else:
        print(f"  {DIM}Ajuste conductual: 0 (sin historia suficiente){RESET}")

    flags = result.get("flags", [])
    if flags:
        print(f"  Alertas:")
        for f in flags:
            print(f"    {YELLOW}⚠ {f}{RESET}")
    else:
        print(f"  {GREEN}Sin alertas{RESET}")

    print(f"  {DIM}ID: {result.get('transaction_id', '?')[:8]}...{RESET}")


def run_test_scenarios(user_id: str, profile_key: str) -> None:
    """Ejecuta todos los escenarios de prueba para un usuario."""
    scenarios = make_test_scenarios(user_id, profile_key)
    config = PREDEFINED_USERS[profile_key]

    print(f"\n{BOLD}{'─'*60}{RESET}")
    print(f"{CYAN}{BOLD}Pruebas para {user_id}{RESET}")
    print(f"{DIM}{config['description']}{RESET}")
    print(f"{BOLD}{'─'*60}{RESET}")

    for scenario in scenarios:
        try:
            result = post("/api/transactions", scenario["txn"])
            print_transaction_result(result, scenario)
        except Exception as e:
            print(f"\n  {RED}Error: {e}{RESET}")

        print(f"  {DIM}{'·'*50}{RESET}")
        time.sleep(0.3)


def show_user_profile(user_id: str) -> None:
    """Muestra el perfil conductual actual de un usuario."""
    try:
        profile = get(f"/api/users/{user_id}/profile")
        history = get(f"/api/transactions/{user_id}?limit=5")
    except Exception as e:
        print(f"{RED}No se pudo obtener perfil de {user_id}: {e}{RESET}")
        return

    print(f"\n{CYAN}{BOLD}Perfil: {user_id}{RESET}")
    print(f"  Transacciones:   {profile['transaction_count']}")
    print(f"  Monto promedio:  ${profile['avg_amount']:,.0f} COP")
    print(f"  Hora promedio:   {profile['avg_hour']:.1f}h")
    print(f"  Frecuencia avg:  {profile['avg_frequency']:.1f} txns/hr")
    print(f"  Países conocidos: {', '.join(profile['known_locations'])}")
    profiled = profile.get("is_profiled", False)
    status_txt = f"{GREEN}ACTIVO{RESET}" if profiled else f"{YELLOW}INSUFICIENTE (<5 txns){RESET}"
    print(f"  Perfil conductual: {status_txt}")

    if history:
        print(f"\n  Últimas transacciones:")
        for txn in history[:3]:
            st = txn["status"]
            col = STATUS_COLOR.get(st, RESET)
            print(f"    {col}{st}{RESET}  ${txn['amount']:>12,.0f}  {txn['location']}  h={txn['hour']:02d}  score={txn['risk_score']}")


def show_global_metrics() -> None:
    """Muestra métricas globales del sistema."""
    try:
        m = get("/api/metrics")
    except Exception as e:
        print(f"{RED}No se pudo obtener métricas: {e}{RESET}")
        return

    total = m["total_transactions"] or 1
    print(f"\n{CYAN}{BOLD}Métricas del sistema{RESET}")
    print(f"  Total transacciones: {m['total_transactions']}")
    print(f"  {GREEN}Aprobadas: {m['approved']} ({m['approval_rate']}%){RESET}")
    print(f"  {YELLOW}En revisión: {m['review']}{RESET}")
    print(f"  {RED}Bloqueadas: {m['blocked']} ({m['block_rate']}%){RESET}")
    print(f"  Risk score promedio: {m['avg_risk_score']}")


# ─── Creación de usuario personalizado ───────────────────────────────────────

def create_custom_user() -> None:
    """Guía interactiva para crear un usuario personalizado."""
    print(f"\n{CYAN}{BOLD}Crear usuario personalizado{RESET}")
    print(f"{DIM}Define el comportamiento 'normal' de tu usuario{RESET}\n")

    user_id = input("  ID del usuario (ej: maria_bogota): ").strip()
    if not user_id or not all(c.isalnum() or c in "_-" for c in user_id):
        print(f"{RED}ID inválido. Solo letras, números, _ o -{RESET}")
        return

    print(f"\n  Horas habituales (ej: 9 10 11 12 13 14 15 16 17 para horario oficina)")
    print(f"  {DIM}O rangos comunes: 'noche' (0-5), 'mañana' (6-12), 'tarde' (12-20), 'noche-tarde' (20-23){RESET}")
    hour_input = input("  Horas: ").strip().lower()

    hour_presets = {
        "noche":       list(range(0, 6)),
        "mañana":      list(range(6, 13)),
        "tarde":       list(range(12, 21)),
        "noche-tarde": list(range(20, 24)),
        "all":         list(range(0, 24)),
    }
    if hour_input in hour_presets:
        hours = hour_presets[hour_input]
    else:
        try:
            hours = [int(h) for h in hour_input.split() if 0 <= int(h) <= 23]
        except ValueError:
            hours = list(range(8, 18))
        if not hours:
            hours = list(range(8, 18))

    print(f"\n  Rango de montos en COP (ej: 100000 5000000)")
    amount_input = input("  Monto mínimo y máximo: ").strip()
    try:
        parts = amount_input.split()
        min_a, max_a = int(parts[0]), int(parts[1])
    except Exception:
        min_a, max_a = 200_000, 2_000_000

    print(f"\n  Países habituales separados por espacio (ej: CO US MX)")
    loc_input = input("  Países: ").strip().upper()
    locations = loc_input.split() if loc_input else ["CO"]
    locations = [l[:5] for l in locations if l.isalpha()][:5]
    if not locations:
        locations = ["CO"]

    n_seed = input(f"\n  ¿Cuántas transacciones base para construir el perfil? (recomendado: 15): ").strip()
    try:
        n_seed = max(5, min(50, int(n_seed)))
    except ValueError:
        n_seed = 15

    # Construir config temporal
    custom_config = {
        "description": f"Usuario personalizado: {user_id}",
        "normal_behavior": {
            "hours":     hours,
            "amounts":   (min_a, max_a),
            "locations": locations,
            "frequency": (1, 3),
        },
        "seed_count": n_seed,
    }

    print(f"\n{DIM}Resumen del perfil a crear:{RESET}")
    print(f"  Usuario:   {user_id}")
    print(f"  Horas:     {min(hours)}h – {max(hours)}h")
    print(f"  Montos:    ${min_a:,.0f} – ${max_a:,.0f} COP")
    print(f"  Países:    {', '.join(locations)}")
    print(f"  Base:      {n_seed} transacciones\n")

    confirm = input("¿Crear este usuario? (s/n): ").strip().lower()
    if confirm != "s":
        print(f"{YELLOW}Cancelado.{RESET}")
        return

    # Sembrar transacciones base
    rng = random.Random()
    normal = custom_config["normal_behavior"]
    n = custom_config["seed_count"]

    print(f"\n{CYAN}Construyendo perfil de {user_id}...{RESET}")
    for i in range(n):
        txn = {
            "user_id":        user_id,
            "amount":         float(rng.randint(*normal["amounts"])),
            "location":       rng.choice(normal["locations"]),
            "hour":           rng.choice(normal["hours"]),
            "frequency":      rng.randint(*normal["frequency"]),
            "is_new_account": False,
        }
        try:
            post("/api/transactions", txn)
            bar = "█" * (i + 1) + "░" * (n - i - 1)
            print(f"\r  [{bar}] {i+1}/{n}", end="", flush=True)
        except Exception as e:
            print(f"\n{RED}Error: {e}{RESET}")

    print(f"\n{GREEN}✓ Perfil creado. Ahora puedes enviarle transacciones de prueba.{RESET}")

    # Ofrecer transacción de prueba inmediata
    print(f"\n¿Enviar una transacción de prueba ahora? (s/n): ", end="")
    if input().strip().lower() == "s":
        test_custom_transaction(user_id, custom_config)


def test_custom_transaction(user_id: str, config: dict = None) -> None:
    """Envía una transacción manual a cualquier usuario."""
    print(f"\n{CYAN}{BOLD}Transacción manual para {user_id}{RESET}")

    try:
        amount    = float(input("  Monto (COP): ").replace(",", "").strip())
        location  = input("  País (ej: CO, US, RU): ").strip().upper()[:5]
        hour      = int(input("  Hora (0-23): ").strip())
        frequency = int(input("  Frecuencia (txns/hr, normalmente 1): ").strip() or "1")
        is_new    = input("  ¿Cuenta nueva? (s/n): ").strip().lower() == "s"
    except (ValueError, EOFError):
        print(f"{RED}Entrada inválida.{RESET}")
        return

    txn = {
        "user_id":        user_id,
        "amount":         amount,
        "location":       location,
        "hour":           hour,
        "frequency":      frequency,
        "is_new_account": is_new,
    }

    try:
        result = post("/api/transactions", txn)
        print_transaction_result(result)
    except Exception as e:
        print(f"{RED}Error: {e}{RESET}")


# ─── Menú principal ───────────────────────────────────────────────────────────

def main_menu() -> None:
    print(f"\n{CYAN}{BOLD}{'═'*60}")
    print(f"   BUBBLES — Simulador de Detección de Fraude")
    print(f"{'═'*60}{RESET}")

    options = [
        ("1", "Crear y probar los 3 usuarios predefinidos (demo completa)"),
        ("2", "Probar un usuario predefinido específico"),
        ("3", "Ver perfil de un usuario"),
        ("4", "Crear usuario personalizado"),
        ("5", "Enviar transacción manual a cualquier usuario"),
        ("6", "Ver métricas globales del sistema"),
        ("7", "Resetear base de datos (borrar todo)"),
        ("0", "Salir"),
    ]

    for key, desc in options:
        print(f"  {CYAN}{key}{RESET}  {desc}")

    print()
    choice = input("Opción: ").strip()

    if choice == "1":
        # Demo completa
        print(f"\n{BOLD}Demo completa — 3 usuarios predefinidos{RESET}")
        print(f"{DIM}Esto puede tomar ~30 segundos...{RESET}")
        for user_id, config in PREDEFINED_USERS.items():
            seed_user(user_id, user_id, verbose=True)
            run_test_scenarios(user_id, user_id)
        show_global_metrics()

    elif choice == "2":
        print(f"\nUsuarios disponibles:")
        for i, (uid, cfg) in enumerate(PREDEFINED_USERS.items(), 1):
            print(f"  {i}. {uid} — {cfg['description']}")
        sel = input("Número: ").strip()
        keys = list(PREDEFINED_USERS.keys())
        try:
            key = keys[int(sel) - 1]
            seed_user(key, key)
            run_test_scenarios(key, key)
        except (ValueError, IndexError):
            print(f"{RED}Opción inválida.{RESET}")

    elif choice == "3":
        uid = input("ID del usuario: ").strip()
        show_user_profile(uid)

    elif choice == "4":
        create_custom_user()

    elif choice == "5":
        uid = input("ID del usuario: ").strip()
        test_custom_transaction(uid)

    elif choice == "6":
        show_global_metrics()

    elif choice == "7":
        confirm = input(f"{RED}¿Seguro que quieres borrar todos los datos? (escribe BORRAR): {RESET}").strip()
        if confirm == "BORRAR":
            import os
            db_path = "data/bubbles.db"
            if os.path.exists(db_path):
                os.remove(db_path)
                print(f"{GREEN}Base de datos eliminada. Reinicia la API para recrearla.{RESET}")
            else:
                print(f"{YELLOW}No hay base de datos que borrar.{RESET}")

    elif choice == "0":
        print(f"\n{DIM}Bye!{RESET}\n")
        return

    else:
        print(f"{YELLOW}Opción no reconocida.{RESET}")

    # Volver al menú
    input(f"\n{DIM}[Enter para continuar]{RESET}")
    main_menu()


# ─── Entry point ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bubbles fraud simulator")
    parser.add_argument("--seed-all", action="store_true",
                        help="Crea todos los perfiles predefinidos y sale")
    parser.add_argument("--user", type=str, help="Muestra el perfil de un usuario")
    args = parser.parse_args()

    # Verificar que la API esté corriendo
    if not check_api():
        print(f"\n{RED}{BOLD}ERROR: La API no está corriendo.{RESET}")
        print(f"Primero ejecuta en otra terminal:")
        print(f"  {CYAN}uvicorn app.main:app --reload{RESET}\n")
        sys.exit(1)

    print(f"{GREEN}✓ API conectada{RESET}")

    if args.seed_all:
        for user_id, config in PREDEFINED_USERS.items():
            seed_user(user_id, user_id)
        print(f"\n{GREEN}Todos los perfiles creados.{RESET}")

    elif args.user:
        show_user_profile(args.user)

    else:
        main_menu()