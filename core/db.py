import json
import os
from contextlib import contextmanager
from datetime import UTC, datetime

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb


def _require_database_url() -> str:
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        raise RuntimeError(
            "DATABASE_URL is required. Configure Render Postgres and set the DATABASE_URL environment variable."
        )
    return database_url


def get_connection():
    return psycopg.connect(_require_database_url(), row_factory=dict_row)


@contextmanager
def db_cursor():
    conn = None
    cur = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        yield conn, cur
        conn.commit()
    except Exception:
        if conn is not None:
            conn.rollback()
        raise
    finally:
        if cur is not None:
            cur.close()
        if conn is not None:
            conn.close()


def _dt_to_text(value):
    if isinstance(value, datetime):
        if value.tzinfo is not None:
            value = value.astimezone(UTC)
        return value.strftime("%Y-%m-%d %H:%M:%S UTC")
    return value


def _study_payload(
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
    result_summary,
):
    return {
        "airport_label": airport_label,
        "lat": lat,
        "lon": lon,
        "required_hours": required_hours,
        "operating_profile_mode": operating_profile_mode,
        "selected_devices": selected_devices,
        "per_device_config": per_device_config,
        "overall_result": overall_result,
        "worst_blackout_days": worst_blackout_days,
        "worst_blackout_pct": worst_blackout_pct,
        "result_summary": result_summary,
    }


def _study_row_to_legacy(row):
    if not row:
        return row

    payload = row.get("study_data") or {}
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except Exception:
            payload = {}

    legacy = dict(row)
    legacy.update(
        {
            "study_name": row.get("study_name") or payload.get("airport_label"),
            "airport_label": payload.get("airport_label"),
            "lat": payload.get("lat"),
            "lon": payload.get("lon"),
            "required_hours": payload.get("required_hours"),
            "operating_profile_mode": payload.get("operating_profile_mode"),
            "selected_devices_json": json.dumps(payload.get("selected_devices") or []),
            "per_device_config_json": json.dumps(payload.get("per_device_config") or {}),
            "overall_result": payload.get("overall_result"),
            "worst_blackout_days": payload.get("worst_blackout_days"),
            "worst_blackout_pct": payload.get("worst_blackout_pct"),
            "result_summary_json": json.dumps(payload.get("result_summary") or {}),
            "created_at": _dt_to_text(row.get("created_at")),
            "updated_at": _dt_to_text(row.get("updated_at")),
        }
    )
    return legacy


def init_db():
    with db_cursor() as (_, cur):
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                full_name TEXT,
                organization TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                last_login_at TIMESTAMPTZ
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS studies (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                study_name TEXT,
                study_data JSONB NOT NULL,
                pdf_name TEXT,
                pdf_bytes BYTEA,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS access_requests (
                id SERIAL PRIMARY KEY,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                full_name TEXT NOT NULL,
                email TEXT NOT NULL,
                organization TEXT,
                message TEXT,
                status TEXT NOT NULL DEFAULT 'new'
            )
            """
        )

        cur.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_studies_user_id ON studies(user_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_access_requests_status ON access_requests(status)")


def create_user(email, password_hash, role="user", full_name=None, organization=None):
    with db_cursor() as (_, cur):
        cur.execute(
            """
            INSERT INTO users (email, password_hash, role, full_name, organization)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (email) DO NOTHING
            RETURNING id
            """,
            (email, password_hash, role, full_name, organization),
        )
        row = cur.fetchone()
        if row:
            return row["id"]

        cur.execute("SELECT id FROM users WHERE email = %s", (email,))
        existing = cur.fetchone()
        return existing["id"] if existing else None


def upsert_user(
    email,
    password_hash,
    role="user",
    full_name=None,
    organization=None,
    is_active=True,
):
    with db_cursor() as (_, cur):
        cur.execute(
            """
            INSERT INTO users (email, password_hash, role, is_active, full_name, organization)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (email) DO UPDATE SET
                password_hash = EXCLUDED.password_hash,
                role = EXCLUDED.role,
                is_active = EXCLUDED.is_active,
                full_name = EXCLUDED.full_name,
                organization = EXCLUDED.organization
            RETURNING id
            """,
            (email, password_hash, role, is_active, full_name, organization),
        )
        row = cur.fetchone()
        return row["id"] if row else None


def get_user_by_email(email):
    with db_cursor() as (_, cur):
        cur.execute("SELECT * FROM users WHERE email = %s", (email,))
        row = cur.fetchone()
        if not row:
            return None
        row["created_at"] = _dt_to_text(row.get("created_at"))
        row["last_login_at"] = _dt_to_text(row.get("last_login_at"))
        return row


def user_exists(email):
    with db_cursor() as (_, cur):
        cur.execute("SELECT id FROM users WHERE email = %s", (email,))
        return cur.fetchone() is not None


def update_last_login(user_id):
    with db_cursor() as (_, cur):
        cur.execute(
            "UPDATE users SET last_login_at = NOW() WHERE id = %s",
            (user_id,),
        )


def list_all_users():
    with db_cursor() as (_, cur):
        cur.execute("SELECT * FROM users ORDER BY created_at DESC")
        rows = cur.fetchall()
        for row in rows:
            row["created_at"] = _dt_to_text(row.get("created_at"))
            row["last_login_at"] = _dt_to_text(row.get("last_login_at"))
        return rows


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
    result_summary,
    pdf_name=None,
    pdf_bytes=None,
):
    payload = _study_payload(
        airport_label=airport_label,
        lat=lat,
        lon=lon,
        required_hours=required_hours,
        operating_profile_mode=operating_profile_mode,
        selected_devices=selected_devices,
        per_device_config=per_device_config,
        overall_result=overall_result,
        worst_blackout_days=worst_blackout_days,
        worst_blackout_pct=worst_blackout_pct,
        result_summary=result_summary,
    )

    with db_cursor() as (_, cur):
        cur.execute(
            """
            INSERT INTO studies (
                user_id,
                study_name,
                study_data,
                pdf_name,
                pdf_bytes,
                updated_at
            )
            VALUES (%s, %s, %s, %s, %s, NOW())
            RETURNING id
            """,
            (
                user_id,
                airport_label or "Unnamed study",
                Jsonb(payload),
                pdf_name,
                pdf_bytes,
            ),
        )
        row = cur.fetchone()
        return row["id"] if row else None


def get_study(study_id, user_id=None):
    with db_cursor() as (_, cur):
        if user_id is None:
            cur.execute("SELECT * FROM studies WHERE id = %s", (study_id,))
        else:
            cur.execute(
                "SELECT * FROM studies WHERE id = %s AND user_id = %s",
                (study_id, user_id),
            )
        row = cur.fetchone()
        return _study_row_to_legacy(row) if row else None


def list_user_studies(user_id):
    with db_cursor() as (_, cur):
        cur.execute(
            """
            SELECT *
            FROM studies
            WHERE user_id = %s
            ORDER BY created_at DESC
            """,
            (user_id,),
        )
        return [_study_row_to_legacy(row) for row in cur.fetchall()]


def get_studies(user_id=None, email=None):
    if user_id is not None:
        return list_user_studies(user_id)
    if email:
        user = get_user_by_email(email)
        if not user:
            return []
        return list_user_studies(user["id"])
    return []


def list_all_studies():
    with db_cursor() as (_, cur):
        cur.execute(
            """
            SELECT s.*, u.email
            FROM studies s
            JOIN users u ON s.user_id = u.id
            ORDER BY s.created_at DESC
            """
        )
        return [_study_row_to_legacy(row) for row in cur.fetchall()]


def delete_study(study_id, user_id):
    with db_cursor() as (_, cur):
        cur.execute(
            "DELETE FROM studies WHERE id = %s AND user_id = %s RETURNING id",
            (study_id, user_id),
        )
        return cur.fetchone() is not None


def create_access_request(full_name, email, organization=None, message=None):
    with db_cursor() as (_, cur):
        cur.execute(
            """
            INSERT INTO access_requests (full_name, email, organization, message, status)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
            """,
            (full_name, email, organization, message, "new"),
        )
        row = cur.fetchone()
        return row["id"] if row else None


def list_access_requests():
    with db_cursor() as (_, cur):
        cur.execute(
            """
            SELECT *
            FROM access_requests
            ORDER BY created_at DESC
            """
        )
        rows = cur.fetchall()
        for row in rows:
            row["created_at"] = _dt_to_text(row.get("created_at"))
        return rows


def get_access_request(request_id):
    with db_cursor() as (_, cur):
        cur.execute("SELECT * FROM access_requests WHERE id = %s", (request_id,))
        row = cur.fetchone()
        if row:
            row["created_at"] = _dt_to_text(row.get("created_at"))
        return row


def update_access_request_status(request_id, status):
    with db_cursor() as (_, cur):
        cur.execute(
            """
            UPDATE access_requests
            SET status = %s
            WHERE id = %s
            """,
            (status, request_id),
        )


def update_user_active(user_id, is_active):
    with db_cursor() as (_, cur):
        cur.execute(
            """
            UPDATE users
            SET is_active = %s
            WHERE id = %s
            """,
            (bool(is_active), user_id),
        )


def update_user_password(user_id, password_hash):
    with db_cursor() as (_, cur):
        cur.execute(
            """
            UPDATE users
            SET password_hash = %s
            WHERE id = %s
            """,
            (password_hash, user_id),
        )
