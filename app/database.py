import sqlite3
import json
from pathlib import Path
from datetime import datetime

DB_PATH = Path("data/bubbles.db")
MAX_RECENT_HOURS = 100  
MAX_RECENT_AMOUNTS = 100


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    # Enable WAL for better concurrent read performance
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    """Create tables if they don't exist. Called once at startup."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS user_profiles (
        user_id         TEXT PRIMARY KEY,
        txn_count       INTEGER DEFAULT 0,
        -- Welford online algorithm state for amount
        amount_mean     REAL    DEFAULT 0.0,
        amount_m2       REAL    DEFAULT 0.0,
        -- Welford online algorithm state for frequency
        freq_mean       REAL    DEFAULT 0.0,
        freq_m2         REAL    DEFAULT 0.0,
        -- Circular buffers stored as JSON arrays
        recent_hours    TEXT    DEFAULT '[]',
        recent_amounts  TEXT    DEFAULT '[]',
        known_locations TEXT    DEFAULT '[]',
        last_updated    TEXT
    );

    CREATE TABLE IF NOT EXISTS transactions (
        id                   TEXT PRIMARY KEY,
        user_id              TEXT NOT NULL,
        amount               REAL NOT NULL,
        location             TEXT NOT NULL,
        hour                 INTEGER NOT NULL,
        frequency            INTEGER NOT NULL,
        is_new_account       INTEGER NOT NULL,
        risk_score           INTEGER NOT NULL,
        rule_score           INTEGER NOT NULL,
        ml_score             REAL NOT NULL,
        behavioral_adj       REAL NOT NULL,
        status               TEXT NOT NULL,
        flags                TEXT DEFAULT '[]',
        processed_at         TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES user_profiles(user_id)
    );

    CREATE INDEX IF NOT EXISTS idx_txn_user ON transactions(user_id);
    CREATE INDEX IF NOT EXISTS idx_txn_status ON transactions(status);
    """)

    conn.commit()
    conn.close()


# ─── User Profile CRUD ────────────────────────────────────────────────────────

def get_user_profile(user_id: str) -> dict | None:
    """Returns raw profile row as dict, or None if user is new."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM user_profiles WHERE user_id = ?", (user_id,)
    ).fetchone()
    conn.close()
    if row is None:
        return None
    profile = dict(row)
    profile["recent_hours"] = json.loads(profile["recent_hours"])
    profile["recent_amounts"] = json.loads(profile["recent_amounts"])
    profile["known_locations"] = json.loads(profile["known_locations"])
    return profile


def upsert_user_profile(user_id: str, txn: dict) -> None:
    """
    Update (or create) a user's behavioral profile using the new transaction.
    Uses Welford's online algorithm for numerically stable mean/variance.
    """
    conn = get_connection()
    existing = conn.execute(
        "SELECT * FROM user_profiles WHERE user_id = ?", (user_id,)
    ).fetchone()

    amount = float(txn["amount"])
    freq = float(txn["frequency"])
    hour = int(txn["hour"])
    location = txn["location"]

    if existing is None:
        # New user — initialize profile
        recent_hours = [hour]
        recent_amounts = [amount]
        known_locations = [location]
        conn.execute("""
            INSERT INTO user_profiles
            (user_id, txn_count, amount_mean, amount_m2, freq_mean, freq_m2,
             recent_hours, recent_amounts, known_locations, last_updated)
            VALUES (?, 1, ?, 0, ?, 0, ?, ?, ?, ?)
        """, (
            user_id, amount, freq,
            json.dumps(recent_hours),
            json.dumps(recent_amounts),
            json.dumps(known_locations),
            datetime.utcnow().isoformat()
        ))
    else:
        row = dict(existing)
        n = row["txn_count"]

        # Welford update for amount
        n_new = n + 1
        delta_a = amount - row["amount_mean"]
        new_amount_mean = row["amount_mean"] + delta_a / n_new
        new_amount_m2 = row["amount_m2"] + delta_a * (amount - new_amount_mean)

        # Welford update for frequency
        delta_f = freq - row["freq_mean"]
        new_freq_mean = row["freq_mean"] + delta_f / n_new
        new_freq_m2 = row["freq_m2"] + delta_f * (freq - new_freq_mean)

        # Circular buffer for hours (keep last MAX_RECENT_HOURS)
        recent_hours = json.loads(row["recent_hours"])
        recent_hours.append(hour)
        if len(recent_hours) > MAX_RECENT_HOURS:
            recent_hours = recent_hours[-MAX_RECENT_HOURS:]

        # Buffer for amounts
        recent_amounts = json.loads(row["recent_amounts"])
        recent_amounts.append(amount)
        if len(recent_amounts) > MAX_RECENT_AMOUNTS:
            recent_amounts = recent_amounts[-MAX_RECENT_AMOUNTS:]

        # Known locations (unique set)
        known_locations = json.loads(row["known_locations"])
        if location not in known_locations:
            known_locations.append(location)

        conn.execute("""
            UPDATE user_profiles
            SET txn_count=?, amount_mean=?, amount_m2=?,
                freq_mean=?, freq_m2=?,
                recent_hours=?, recent_amounts=?, known_locations=?,
                last_updated=?
            WHERE user_id=?
        """, (
            n_new, new_amount_mean, new_amount_m2,
            new_freq_mean, new_freq_m2,
            json.dumps(recent_hours),
            json.dumps(recent_amounts),
            json.dumps(known_locations),
            datetime.utcnow().isoformat(),
            user_id
        ))

    conn.commit()
    conn.close()


# ─── Transaction Log ──────────────────────────────────────────────────────────

def save_transaction(txn_id: str, data: dict) -> None:
    """Append a fully evaluated transaction to the audit log."""
    conn = get_connection()
    conn.execute("""
        INSERT INTO transactions
        (id, user_id, amount, location, hour, frequency, is_new_account,
         risk_score, rule_score, ml_score, behavioral_adj, status, flags, processed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        txn_id,
        data["user_id"],
        data["amount"],
        data["location"],
        data["hour"],
        data["frequency"],
        int(data["is_new_account"]),
        data["risk_score"],
        data["rule_score"],
        data["ml_score"],
        data["behavioral_adj"],
        data["status"],
        json.dumps(data.get("flags", [])),
        data["processed_at"],
    ))
    conn.commit()
    conn.close()


def get_user_transactions(user_id: str, limit: int = 50) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM transactions WHERE user_id=? ORDER BY processed_at DESC LIMIT ?",
        (user_id, limit)
    ).fetchall()
    conn.close()
    result = []
    for row in rows:
        r = dict(row)
        r["flags"] = json.loads(r["flags"])
        result.append(r)
    return result


def get_metrics() -> dict:
    conn = get_connection()
    row = conn.execute("""
        SELECT
            COUNT(*)                                        AS total,
            SUM(CASE WHEN status='APPROVED' THEN 1 ELSE 0 END) AS approved,
            SUM(CASE WHEN status='REVIEW'   THEN 1 ELSE 0 END) AS review,
            SUM(CASE WHEN status='BLOCKED'  THEN 1 ELSE 0 END) AS blocked,
            AVG(risk_score)                                 AS avg_risk
        FROM transactions
    """).fetchone()
    conn.close()
    d = dict(row)
    total = d["total"] or 1
    return {
        "total_transactions": d["total"] or 0,
        "approved": d["approved"] or 0,
        "review": d["review"] or 0,
        "blocked": d["blocked"] or 0,
        "approval_rate": round((d["approved"] or 0) / total * 100, 1),
        "block_rate": round((d["blocked"] or 0) / total * 100, 1),
        "avg_risk_score": round(d["avg_risk"] or 0, 1),
    }
