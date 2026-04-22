import json
import os
from contextlib import contextmanager
from datetime import datetime

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from core.devices import DEVICES, SOLAR_ENGINES
from core.devices_avlite import AVLITE_FIXTURES
from core.time_utils import format_timestamp


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
        return format_timestamp(value, include_seconds=True)
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


def _device_catalog_row_to_display(row):
    if not row:
        return row
    item = dict(row)
    item["created_at"] = _dt_to_text(row.get("created_at"))
    item["updated_at"] = _dt_to_text(row.get("updated_at"))
    return item


def _panel_configuration_for_device(device):
    if device.get("system_type") == "avlite_fixture":
        fixture = AVLITE_FIXTURES.get(device.get("fixture_key"), {})
        panel_count = fixture.get("panel_count")
        if panel_count == 2:
            return "double_v_shape"
        if panel_count == 4:
            return "quad_90deg"
    return "single_panel"


def _default_catalog_items():
    items = []

    for key, engine in SOLAR_ENGINES.items():
        tilt_options = engine.get("tilt_options") or []
        items.append(
            {
                "runtime_id": None,
                "code": engine.get("key") or key,
                "entity_type": "solar_engine",
                "manufacturer": "SALA",
                "name": engine.get("name") or key,
                "system_type": "solar_engine",
                "default_power_w": None,
                "battery_type": engine.get("battery_type"),
                "battery_wh": engine.get("batt"),
                "cutoff_pct": engine.get("cutoff_pct"),
                "standby_power_w": engine.get("standby_power_w"),
                "supports_intensity_adjustment": False,
                "panel_configuration": "single_panel" if (engine.get("pv") or 0) else None,
                "panel_wp": engine.get("pv"),
                "panel_tilt_options": tilt_options,
                "panel_tilt_deg": tilt_options[0] if tilt_options else None,
                "default_engine_code": None,
                "compatible_engine_codes": [],
                "has_external_battery_option": engine.get("batt_ext") is not None,
                "is_active": True,
                "metadata": {
                    "short_name": engine.get("short_name"),
                    "battery_wh_external": engine.get("batt_ext"),
                    "fixed_tilt_mechanics": engine.get("fixed"),
                },
            }
        )

    for device_id, device in DEVICES.items():
        entity_type = "built_in_device"
        if device.get("system_type") == "external_engine":
            entity_type = "powered_device"

        battery_type = device.get("battery_type")
        cutoff_pct = device.get("cutoff_pct")
        panel_configuration = device.get("panel_configuration")
        panel_wp = device.get("pv")
        panel_tilt_deg = device.get("tilt")
        metadata = {
            "device_id": device_id,
            "lamp_variants": device.get("lamp_variants"),
            "default_lamp_variant": device.get("default_lamp_variant"),
            "tilt_options": device.get("tilt_options"),
            "fixed_tilt_mechanics": device.get("fixed"),
        }

        if device.get("system_type") == "avlite_fixture":
            fixture = AVLITE_FIXTURES.get(device.get("fixture_key"), {})
            battery_type = fixture.get("battery_type")
            cutoff_pct = fixture.get("cutoff_pct")
            panel_configuration = _panel_configuration_for_device(device)
            panel_tilt_deg = fixture.get("panels", [{}])[0].get("tilt")
            metadata.update(
                {
                    "fixture_key": device.get("fixture_key"),
                    "panel_geometry": fixture.get("panel_geometry"),
                    "panels": fixture.get("panels"),
                    "battery_voltage_v": fixture.get("battery_voltage_v"),
                    "battery_ah": fixture.get("battery_ah"),
                    "usable_battery_pct": fixture.get("usable_battery_pct"),
                    "source_note": fixture.get("source_note"),
                }
            )

        items.append(
            {
                "runtime_id": device_id,
                "code": device.get("code") or str(device_id),
                "entity_type": entity_type,
                "manufacturer": device.get("manufacturer"),
                "name": device.get("name") or device.get("code") or str(device_id),
                "system_type": device.get("system_type"),
                "default_power_w": device.get("default_power"),
                "battery_type": battery_type,
                "battery_wh": device.get("batt"),
                "cutoff_pct": cutoff_pct,
                "standby_power_w": device.get("standby_power_w"),
                "supports_intensity_adjustment": bool(device.get("supports_intensity_adjustment")),
                "panel_configuration": panel_configuration,
                "panel_wp": panel_wp,
                "panel_tilt_options": device.get("tilt_options") or [],
                "panel_tilt_deg": panel_tilt_deg,
                "default_engine_code": device.get("default_engine"),
                "compatible_engine_codes": device.get("compatible_engines") or [],
                "has_external_battery_option": False,
                "is_active": True,
                "metadata": metadata,
            }
        )

    return items


def _sync_default_device_catalog(cur):
    for item in _default_catalog_items():
        cur.execute(
            """
            INSERT INTO device_catalog (
                code,
                runtime_id,
                entity_type,
                manufacturer,
                name,
                system_type,
                default_power_w,
                battery_type,
                battery_wh,
                cutoff_pct,
                standby_power_w,
                supports_intensity_adjustment,
                panel_configuration,
                panel_wp,
                panel_tilt_options,
                panel_tilt_deg,
                default_engine_code,
                compatible_engine_codes,
                has_external_battery_option,
                metadata,
                is_active,
                updated_at
            )
            VALUES (
                %(code)s,
                %(runtime_id)s,
                %(entity_type)s,
                %(manufacturer)s,
                %(name)s,
                %(system_type)s,
                %(default_power_w)s,
                %(battery_type)s,
                %(battery_wh)s,
                %(cutoff_pct)s,
                %(standby_power_w)s,
                %(supports_intensity_adjustment)s,
                %(panel_configuration)s,
                %(panel_wp)s,
                %(panel_tilt_options)s,
                %(panel_tilt_deg)s,
                %(default_engine_code)s,
                %(compatible_engine_codes)s,
                %(has_external_battery_option)s,
                %(metadata)s,
                %(is_active)s,
                NOW()
            )
            ON CONFLICT (code) DO UPDATE SET
                entity_type = EXCLUDED.entity_type,
                runtime_id = EXCLUDED.runtime_id,
                manufacturer = EXCLUDED.manufacturer,
                name = EXCLUDED.name,
                system_type = EXCLUDED.system_type,
                default_power_w = EXCLUDED.default_power_w,
                battery_type = EXCLUDED.battery_type,
                battery_wh = EXCLUDED.battery_wh,
                cutoff_pct = EXCLUDED.cutoff_pct,
                standby_power_w = EXCLUDED.standby_power_w,
                supports_intensity_adjustment = EXCLUDED.supports_intensity_adjustment,
                panel_configuration = EXCLUDED.panel_configuration,
                panel_wp = EXCLUDED.panel_wp,
                panel_tilt_options = EXCLUDED.panel_tilt_options,
                panel_tilt_deg = EXCLUDED.panel_tilt_deg,
                default_engine_code = EXCLUDED.default_engine_code,
                compatible_engine_codes = EXCLUDED.compatible_engine_codes,
                has_external_battery_option = EXCLUDED.has_external_battery_option,
                metadata = EXCLUDED.metadata,
                is_active = EXCLUDED.is_active,
                updated_at = NOW()
            """,
            {
                **item,
                "panel_tilt_options": Jsonb(item.get("panel_tilt_options") or []),
                "compatible_engine_codes": Jsonb(item.get("compatible_engine_codes") or []),
                "metadata": Jsonb(item.get("metadata") or {}),
            },
        )


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

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS device_catalog (
                id SERIAL PRIMARY KEY,
                code TEXT NOT NULL UNIQUE,
                runtime_id INTEGER UNIQUE,
                entity_type TEXT NOT NULL,
                manufacturer TEXT NOT NULL,
                name TEXT NOT NULL,
                system_type TEXT NOT NULL,
                default_power_w DOUBLE PRECISION,
                battery_type TEXT,
                battery_wh DOUBLE PRECISION,
                cutoff_pct DOUBLE PRECISION,
                standby_power_w DOUBLE PRECISION,
                supports_intensity_adjustment BOOLEAN NOT NULL DEFAULT FALSE,
                panel_configuration TEXT,
                panel_wp DOUBLE PRECISION,
                panel_tilt_options JSONB NOT NULL DEFAULT '[]'::jsonb,
                panel_tilt_deg DOUBLE PRECISION,
                default_engine_code TEXT,
                compatible_engine_codes JSONB NOT NULL DEFAULT '[]'::jsonb,
                has_external_battery_option BOOLEAN NOT NULL DEFAULT FALSE,
                metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        cur.execute("ALTER TABLE device_catalog ADD COLUMN IF NOT EXISTS runtime_id INTEGER UNIQUE")

        cur.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_studies_user_id ON studies(user_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_access_requests_status ON access_requests(status)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_device_catalog_entity_type ON device_catalog(entity_type)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_device_catalog_manufacturer ON device_catalog(manufacturer)")
        _sync_default_device_catalog(cur)


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


def list_device_catalog(entity_type=None):
    with db_cursor() as (_, cur):
        if entity_type:
            cur.execute(
                """
                SELECT *
                FROM device_catalog
                WHERE entity_type = %s
                ORDER BY manufacturer, name, code
                """,
                (entity_type,),
            )
        else:
            cur.execute(
                """
                SELECT *
                FROM device_catalog
                ORDER BY entity_type, manufacturer, name, code
                """
            )
        return [_device_catalog_row_to_display(row) for row in cur.fetchall()]


def get_device_catalog_item(item_id):
    with db_cursor() as (_, cur):
        cur.execute("SELECT * FROM device_catalog WHERE id = %s", (item_id,))
        row = cur.fetchone()
        return _device_catalog_row_to_display(row) if row else None


def device_catalog_code_exists(code, exclude_id=None):
    with db_cursor() as (_, cur):
        if exclude_id is None:
            cur.execute("SELECT id FROM device_catalog WHERE code = %s", (code,))
        else:
            cur.execute(
                "SELECT id FROM device_catalog WHERE code = %s AND id <> %s",
                (code, exclude_id),
            )
        return cur.fetchone() is not None


def _catalog_write_payload(payload):
    return {
        "code": payload.get("code"),
        "runtime_id": payload.get("runtime_id"),
        "entity_type": payload.get("entity_type"),
        "manufacturer": payload.get("manufacturer"),
        "name": payload.get("name"),
        "system_type": payload.get("system_type"),
        "default_power_w": payload.get("default_power_w"),
        "battery_type": payload.get("battery_type"),
        "battery_wh": payload.get("battery_wh"),
        "cutoff_pct": payload.get("cutoff_pct"),
        "standby_power_w": payload.get("standby_power_w"),
        "supports_intensity_adjustment": bool(payload.get("supports_intensity_adjustment")),
        "panel_configuration": payload.get("panel_configuration"),
        "panel_wp": payload.get("panel_wp"),
        "panel_tilt_options": Jsonb(payload.get("panel_tilt_options") or []),
        "panel_tilt_deg": payload.get("panel_tilt_deg"),
        "default_engine_code": payload.get("default_engine_code"),
        "compatible_engine_codes": Jsonb(payload.get("compatible_engine_codes") or []),
        "has_external_battery_option": bool(payload.get("has_external_battery_option")),
        "metadata": Jsonb(payload.get("metadata") or {}),
        "is_active": bool(payload.get("is_active", True)),
    }


def _next_runtime_device_id(cur):
    cur.execute("SELECT COALESCE(MAX(runtime_id), 999) AS max_runtime_id FROM device_catalog")
    row = cur.fetchone()
    return int((row or {}).get("max_runtime_id") or 999) + 1


def create_device_catalog_item(payload):
    with db_cursor() as (_, cur):
        write_payload = _catalog_write_payload(payload)
        if write_payload["entity_type"] != "solar_engine" and not write_payload["runtime_id"]:
            write_payload["runtime_id"] = _next_runtime_device_id(cur)
        cur.execute(
            """
            INSERT INTO device_catalog (
                code,
                runtime_id,
                entity_type,
                manufacturer,
                name,
                system_type,
                default_power_w,
                battery_type,
                battery_wh,
                cutoff_pct,
                standby_power_w,
                supports_intensity_adjustment,
                panel_configuration,
                panel_wp,
                panel_tilt_options,
                panel_tilt_deg,
                default_engine_code,
                compatible_engine_codes,
                has_external_battery_option,
                metadata,
                is_active,
                updated_at
            ) VALUES (
                %(code)s,
                %(runtime_id)s,
                %(entity_type)s,
                %(manufacturer)s,
                %(name)s,
                %(system_type)s,
                %(default_power_w)s,
                %(battery_type)s,
                %(battery_wh)s,
                %(cutoff_pct)s,
                %(standby_power_w)s,
                %(supports_intensity_adjustment)s,
                %(panel_configuration)s,
                %(panel_wp)s,
                %(panel_tilt_options)s,
                %(panel_tilt_deg)s,
                %(default_engine_code)s,
                %(compatible_engine_codes)s,
                %(has_external_battery_option)s,
                %(metadata)s,
                %(is_active)s,
                NOW()
            )
            RETURNING id
            """,
            write_payload,
        )
        row = cur.fetchone()
        return row["id"] if row else None


def update_device_catalog_item(item_id, payload):
    with db_cursor() as (_, cur):
        cur.execute("SELECT runtime_id, entity_type FROM device_catalog WHERE id = %s", (item_id,))
        existing = cur.fetchone() or {}
        write_payload = _catalog_write_payload(payload)
        if write_payload["entity_type"] != "solar_engine":
            write_payload["runtime_id"] = write_payload["runtime_id"] or existing.get("runtime_id") or _next_runtime_device_id(cur)
        else:
            write_payload["runtime_id"] = None
        cur.execute(
            """
            UPDATE device_catalog
            SET
                code = %(code)s,
                runtime_id = %(runtime_id)s,
                entity_type = %(entity_type)s,
                manufacturer = %(manufacturer)s,
                name = %(name)s,
                system_type = %(system_type)s,
                default_power_w = %(default_power_w)s,
                battery_type = %(battery_type)s,
                battery_wh = %(battery_wh)s,
                cutoff_pct = %(cutoff_pct)s,
                standby_power_w = %(standby_power_w)s,
                supports_intensity_adjustment = %(supports_intensity_adjustment)s,
                panel_configuration = %(panel_configuration)s,
                panel_wp = %(panel_wp)s,
                panel_tilt_options = %(panel_tilt_options)s,
                panel_tilt_deg = %(panel_tilt_deg)s,
                default_engine_code = %(default_engine_code)s,
                compatible_engine_codes = %(compatible_engine_codes)s,
                has_external_battery_option = %(has_external_battery_option)s,
                metadata = %(metadata)s,
                is_active = %(is_active)s,
                updated_at = NOW()
            WHERE id = %(item_id)s
            """,
            {**write_payload, "item_id": item_id},
        )
