# core/stats.py
#
# Aggregates for the admin "Statistics" dashboard. Built on top of
# core.db.list_studies_for_stats() / list_users_for_stats(), which already
# exclude the heavy fields (pdf_bytes, result_summary) - see the OOM
# incident documented on list_all_studies(). All grouping/aggregation
# happens here in Python: this is an occasional admin view over a dataset
# small enough that this is simpler and more maintainable than deeply
# nested JSONB SQL for multi-key grouping, argmax-per-group, and device
# array unnesting.
#
# Definition of "an FS" used throughout (confirmed with the SALA team):
# one entry per (user, airport), counted once at first completion.
# Recalculations of the same airport by the same user do NOT add to the
# FS totals, weekly chart, device tally, map, or pass/fail ratio - those
# all read from this deduplicated set, using the LATEST completed version
# for anything that reflects current status (pass/fail, devices tested).
# The two exceptions are generation time and recalculation rate, which
# are inherently about individual runs/versions, not the deduped airport
# concept, so they read every completed row.

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

from core.catalog import get_cached_runtime_catalog
from core.db import list_studies_for_stats, list_users_for_stats
from core.notify import is_internal_email

_NOT_COMPLETED_STATUSES = {"RUNNING", "PENDING", ""}
_ACTIVE_WINDOW_DAYS = 30


def _as_utc(dt):
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _is_completed(study_data: dict) -> bool:
    status = str((study_data or {}).get("overall_result") or "").upper()
    return status not in _NOT_COMPLETED_STATUSES


def _airport_group_key(user_id, study_data: dict):
    base = (study_data or {}).get("base_airport_label") or (study_data or {}).get("airport_label") or "Unnamed"
    return (user_id, " ".join(str(base).lower().split()))


def _device_family_name(sim_key, devices: dict) -> str:
    raw = str(sim_key or "")
    device_id_raw = raw.split("||", 1)[0]
    try:
        device_id = int(device_id_raw)
    except Exception:
        return raw or "Unknown device"
    spec = devices.get(device_id)
    if spec:
        return spec.get("name") or spec.get("code") or f"Device #{device_id}"
    return f"Device #{device_id} (removed)"


def _week_bucket_starts(weeks: int, now: datetime):
    current_week_start = (now - timedelta(days=now.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    return [current_week_start - timedelta(weeks=i) for i in range(weeks - 1, -1, -1)]


def compute_admin_stats(weeks: int = 8) -> dict:
    raw_rows = list_studies_for_stats()
    raw_users = list_users_for_stats()
    devices, _ = get_cached_runtime_catalog()

    completed_rows = []
    for row in raw_rows:
        study_data = row.get("study_data") or {}
        if not _is_completed(study_data):
            continue
        completed_rows.append(
            {
                "user_id": row["user_id"],
                "email": row.get("email"),
                "organization": row.get("organization"),
                "created_at": _as_utc(row.get("created_at")),
                "study_data": study_data,
            }
        )

    groups = defaultdict(list)
    for r in completed_rows:
        groups[_airport_group_key(r["user_id"], r["study_data"])].append(r)

    distinct_fs = []
    for (user_id, _airport_norm), items in groups.items():
        items_sorted = sorted(items, key=lambda r: r["created_at"] or datetime.min.replace(tzinfo=timezone.utc))
        first, latest = items_sorted[0], items_sorted[-1]
        latest_data = latest["study_data"]
        distinct_fs.append(
            {
                "user_id": user_id,
                "email": first["email"],
                "organization": latest["organization"] or first["organization"],
                "first_created_at": first["created_at"],
                "is_internal": is_internal_email(first["email"]),
                "latest_status": str(latest_data.get("overall_result") or "").upper(),
                "latest_selected_devices": latest_data.get("selected_devices") or [],
                "lat": latest_data.get("lat"),
                "lon": latest_data.get("lon"),
                "airport_label": latest_data.get("airport_label") or latest_data.get("base_airport_label"),
                "version_count": len(items_sorted),
            }
        )

    total_fs = len(distinct_fs)
    internal_fs = sum(1 for f in distinct_fs if f["is_internal"])
    external_fs = total_fs - internal_fs

    now = datetime.now(timezone.utc)
    weekly_counts = []
    for week_start in _week_bucket_starts(weeks, now):
        week_end = week_start + timedelta(weeks=1)
        internal_count = external_count = 0
        for f in distinct_fs:
            dt = f["first_created_at"]
            if dt and week_start <= dt < week_end:
                if f["is_internal"]:
                    internal_count += 1
                else:
                    external_count += 1
        weekly_counts.append(
            {
                "week_start": week_start.date().isoformat(),
                "internal": internal_count,
                "external": external_count,
                "total": internal_count + external_count,
            }
        )

    status_counts = Counter()
    for f in distinct_fs:
        status = f["latest_status"]
        if status == "ALL_PASS":
            status_counts["PASS"] += 1
        elif status == "NONE_PASS":
            status_counts["FAIL"] += 1
        elif status == "MIXED":
            status_counts["MIXED"] += 1
        else:
            status_counts["UNKNOWN"] += 1

    device_counter = Counter()
    for f in distinct_fs:
        family_names = {_device_family_name(k, devices) for k in f["latest_selected_devices"]}
        device_counter.update(family_names)
    top_devices = device_counter.most_common(3)

    map_points = defaultdict(lambda: {"count": 0, "label": None, "lat": None, "lon": None})
    for f in distinct_fs:
        lat, lon = f.get("lat"), f.get("lon")
        if lat is None or lon is None:
            continue
        try:
            key = (round(float(lat), 3), round(float(lon), 3))
        except Exception:
            continue
        entry = map_points[key]
        entry["count"] += 1
        entry["lat"] = float(lat)
        entry["lon"] = float(lon)
        if not entry["label"]:
            entry["label"] = f.get("airport_label") or "Unknown airport"
    map_points_list = sorted(map_points.values(), key=lambda p: -p["count"])

    org_counter = Counter()
    for f in distinct_fs:
        org = (f.get("organization") or "").strip()
        if org:
            org_counter[org] += 1
    top_organizations = org_counter.most_common(5)

    recalculated_count = sum(1 for f in distinct_fs if f["version_count"] > 1)
    recalculation_rate_pct = (recalculated_count / total_fs * 100.0) if total_fs else 0.0

    elapsed_seconds = []
    for r in completed_rows:
        totals = (r["study_data"].get("simulation_timing") or {}).get("totals") or {}
        elapsed = totals.get("elapsed_seconds")
        if elapsed:
            try:
                elapsed_seconds.append(float(elapsed))
            except Exception:
                pass
    elapsed_seconds.sort()
    sample_size = len(elapsed_seconds)
    avg_generation_seconds = sum(elapsed_seconds) / sample_size if sample_size else None
    median_generation_seconds = elapsed_seconds[sample_size // 2] if sample_size else None

    total_users = len(raw_users)
    active_users = dormant_users = 0
    for u in raw_users:
        last_login = _as_utc(u.get("last_login_at"))
        if last_login and (now - last_login) <= timedelta(days=_ACTIVE_WINDOW_DAYS):
            active_users += 1
        else:
            dormant_users += 1

    return {
        "total_fs": total_fs,
        "internal_fs": internal_fs,
        "external_fs": external_fs,
        "weekly_counts": weekly_counts,
        "weeks": weeks,
        "status_counts": dict(status_counts),
        "top_devices": top_devices,
        "map_points": map_points_list,
        "top_organizations": top_organizations,
        "recalculation_rate_pct": recalculation_rate_pct,
        "recalculated_count": recalculated_count,
        "avg_generation_seconds": avg_generation_seconds,
        "median_generation_seconds": median_generation_seconds,
        "generation_time_sample_size": sample_size,
        "total_users": total_users,
        "active_users": active_users,
        "dormant_users": dormant_users,
        "active_window_days": _ACTIVE_WINDOW_DAYS,
        "total_completed_runs": len(completed_rows),
    }
