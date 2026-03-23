# core/db.py

import sqlite3
import json
from datetime import datetime
from pathlib import Path

DB_PATH = Path("data/app.db")


def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    # USERS
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('admin', 'user')),
        is_active INTEGER NOT NULL DEFAULT 1,
        full_name TEXT,
        organization TEXT,
        created_at TEXT NOT NULL,
        last_login_at TEXT
    )
    """)

    # STUDIES
    cur.execute("""
    CREATE TABLE IF NOT EXISTS studies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        created_at TEXT NOT NULL,

        airport_label TEXT,
        lat REAL,
        lon REAL,

        required_hours REAL,
        operating_profile_mode TEXT,

        selected_devices_json TEXT,
        per_device_config_json TEXT,

        overall_result TEXT,
        worst_blackout_days INTEGER,
        worst_blackout_pct REAL,

        result_summary_json TEXT,

        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    """)

    conn.commit()
    conn.close()


# =========================
# USERS
# =========================

def create_user(email, password_hash, role="user", full_name=None, organization=None):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO users (email, password_hash, role, full_name, organization, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        email,
        password_hash,
        role,
        full_name,
        organization,
        datetime.utcnow().isoformat()
    ))

    conn.commit()
    conn.close()


def get_user_by_email(email):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM users WHERE email = ?", (email,))
    user = cur.fetchone()

    conn.close()
    return user


def update_last_login(user_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE users SET last_login_at = ?
        WHERE id = ?
    """, (datetime.utcnow().isoformat(), user_id))

    conn.commit()
    conn.close()


def list_all_users():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM users ORDER BY created_at DESC")
    rows = cur.fetchall()

    conn.close()
    return rows


# =========================
# STUDIES
# =========================

def save_study(
    user_id,
    airport_label,
    lat,
    lon,
    required_hours,
    operating_profile_mode,
    selected_devices,
    per_device_config,
    overall_result,
    worst_blackout_days,
    worst_blackout_pct,
    result_summary
):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO studies (
            user_id,
            created_at,
            airport_label,
            lat,
            lon,
            required_hours,
            operating_profile_mode,
            selected_devices_json,
            per_device_config_json,
            overall_result,
            worst_blackout_days,
            worst_blackout_pct,
            result_summary_json
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        datetime.utcnow().isoformat(),
        airport_label,
        lat,
        lon,
        required_hours,
        operating_profile_mode,
        json.dumps(selected_devices),
        json.dumps(per_device_config),
        overall_result,
        worst_blackout_days,
        worst_blackout_pct,
        json.dumps(result_summary)
    ))

    conn.commit()
    conn.close()


def list_user_studies(user_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT * FROM studies
        WHERE user_id = ?
        ORDER BY created_at DESC
    """, (user_id,))

    rows = cur.fetchall()
    conn.close()
    return rows


def list_all_studies():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT s.*, u.email
        FROM studies s
        JOIN users u ON s.user_id = u.id
        ORDER BY s.created_at DESC
    """)

    rows = cur.fetchall()
    conn.close()
    return rows
