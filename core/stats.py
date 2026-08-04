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
from core.db import list_device_outcomes_for_stats, list_studies_for_stats, list_users_for_stats
from core.notify import is_internal_email

_NOT_COMPLETED_STATUSES = {"RUNNING", "PENDING", ""}
_ACTIVE_WINDOW_DAYS = 30

# Stored overall_result values -> the labels shown to admins.
_STATUS_LABELS = {
    "ALL_PASS": "PASS",
    "NONE_PASS": "FAIL",
    "MIXED": "MIXED",
}


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


LATITUDE_BANDS = (
    ("tropical", 0.0, 23.5),
    ("subtropical", 23.5, 45.0),
    ("high", 45.0, 90.1),
)


def _latitude_band(lat) -> str | None:
    try:
        abs_lat = abs(float(lat))
    except (TypeError, ValueError):
        return None
    for name, low, high in LATITUDE_BANDS:
        if low <= abs_lat < high:
            return name
    return None


def compute_device_feasibility() -> dict:
    """Empirical feasibility per device, from the actual outcomes of
    studies that have been run - NOT a theoretical irradiance model.

    For each device and latitude band it reports how many studies tested
    it, how many passed, and the observed boundary: the highest required
    operating hours that still passed, and the lowest that failed. Where
    nobody has run a study, the cell is simply empty rather than
    estimated - this is an evidence map, and its gaps are real gaps.

    Deduplicated the same way as the rest of the dashboard: one entry per
    (user, airport, device), keeping that combination's most recent study.
    """
    rows = list_device_outcomes_for_stats()

    latest = {}
    for row in rows:
        base = row.get("base_airport_label") or row.get("airport_label") or "Unnamed"
        key = (
            row["user_id"],
            " ".join(str(base).lower().split()),
            row.get("device_code") or row.get("device_name") or "?",
        )
        current = latest.get(key)
        if current is None or (row.get("created_at") or datetime.min) >= (
            current.get("created_at") or datetime.min
        ):
            latest[key] = row

    devices = defaultdict(
        lambda: {
            "tested": 0,
            "passed": 0,
            "points": [],
            "organizations": Counter(),
            "bands": defaultdict(
                lambda: {"tested": 0, "passed": 0, "max_pass_hours": None, "min_fail_hours": None}
            ),
        }
    )

    for row in latest.values():
        code = row.get("device_code") or row.get("device_name") or "?"
        passed = str(row.get("device_status") or "").upper() == "PASS"
        entry = devices[code]
        entry["tested"] += 1
        entry["passed"] += int(passed)
        org = (row.get("organization") or "").strip()
        if org:
            entry["organizations"][org] += 1
        entry["points"].append(
            {
                "lat": row.get("lat"),
                "lon": row.get("lon"),
                "label": row.get("airport_label") or "Unknown airport",
                "country": row.get("country") or "-",
                "status": "PASS" if passed else "FAIL",
                "required_hours": row.get("required_hours"),
                "count": 1,
            }
        )

        band = _latitude_band(row.get("lat"))
        hours = row.get("required_hours")
        if band is None or hours is None:
            continue
        band_entry = entry["bands"][band]
        band_entry["tested"] += 1
        if passed:
            band_entry["passed"] += 1
            if band_entry["max_pass_hours"] is None or hours > band_entry["max_pass_hours"]:
                band_entry["max_pass_hours"] = hours
        else:
            if band_entry["min_fail_hours"] is None or hours < band_entry["min_fail_hours"]:
                band_entry["min_fail_hours"] = hours

    return {
        code: {
            "tested": data["tested"],
            "passed": data["passed"],
            "points": data["points"],
            "organizations": dict(data["organizations"]),
            "bands": {band: dict(values) for band, values in data["bands"].items()},
        }
        for code, data in sorted(devices.items(), key=lambda kv: -kv[1]["tested"])
    }


def organization_device_matrix(feasibility: dict, max_orgs: int = 8) -> tuple:
    """Which organisations are evaluating which devices - i.e. who is
    interested in what. Returns (rows, device_codes) where each row is
    {"organization": name, <device_code>: count, "Total": n}, ranked by
    total studies and capped at max_orgs so the grid stays readable.
    """
    totals = Counter()
    per_org = defaultdict(Counter)
    for code, data in feasibility.items():
        for org, count in (data.get("organizations") or {}).items():
            per_org[org][code] += count
            totals[org] += count

    device_codes = [code for code, _ in sorted(
        feasibility.items(), key=lambda kv: -kv[1]["tested"]
    )]
    rows = []
    for org, total in totals.most_common(max_orgs):
        row = {"organization": org, "Total": total}
        for code in device_codes:
            row[code] = per_org[org].get(code, 0)
        rows.append(row)
    return rows, device_codes


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
                "full_name": row.get("full_name"),
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
                "full_name": first["full_name"] or first["email"],
                "organization": latest["organization"] or first["organization"],
                "first_created_at": first["created_at"],
                "is_internal": is_internal_email(first["email"]),
                "latest_status": str(latest_data.get("overall_result") or "").upper(),
                "latest_selected_devices": latest_data.get("selected_devices") or [],
                "lat": latest_data.get("lat"),
                "lon": latest_data.get("lon"),
                "airport_label": latest_data.get("airport_label") or latest_data.get("base_airport_label"),
                "country": latest_data.get("country") or "-",
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

    map_points = defaultdict(
        lambda: {"count": 0, "label": None, "lat": None, "lon": None, "statuses": []}
    )
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
        entry["statuses"].append(_STATUS_LABELS.get(f["latest_status"], "UNKNOWN"))
        if not entry["label"]:
            entry["label"] = f.get("airport_label") or "Unknown airport"

    for entry in map_points.values():
        # A single airport can hold several studies (different users, or
        # the same user's separate studies). Collapse their outcomes into
        # one dot colour: all-passed -> pass, none-passed -> fail, and
        # anything else (including a single MIXED study) -> mixed, so a
        # partial result is never rounded up to a clean pass or down to a
        # flat fail.
        statuses = set(entry.pop("statuses"))
        if statuses == {"PASS"}:
            entry["status"] = "PASS"
        elif "PASS" not in statuses and "MIXED" not in statuses:
            entry["status"] = "FAIL"
        else:
            entry["status"] = "MIXED"

    map_points_list = sorted(map_points.values(), key=lambda p: -p["count"])

    def _ranked_with_outcomes(key_fn, label_fn, limit=5):
        """Top entities by FS count, each broken down by outcome, so a
        high total is never mistaken for a good result (or vice versa)."""
        buckets = defaultdict(lambda: {"total": 0, "PASS": 0, "MIXED": 0, "FAIL": 0, "UNKNOWN": 0})
        labels = {}
        for f in distinct_fs:
            key = key_fn(f)
            if key is None:
                continue
            labels[key] = label_fn(f)
            entry = buckets[key]
            entry["total"] += 1
            entry[_STATUS_LABELS.get(f["latest_status"], "UNKNOWN")] += 1
        ranked = sorted(buckets.items(), key=lambda kv: -kv[1]["total"])[:limit]
        return [
            {
                "label": labels[key],
                "total": v["total"],
                "passed": v["PASS"],
                "mixed": v["MIXED"],
                "failed": v["FAIL"] + v["UNKNOWN"],
            }
            for key, v in ranked
        ]

    top_organizations = _ranked_with_outcomes(
        lambda f: (f.get("organization") or "").strip() or None,
        lambda f: (f.get("organization") or "").strip(),
    )
    top_users = _ranked_with_outcomes(
        lambda f: f["user_id"],
        lambda f: f["full_name"] or f["email"],
    )

    fs_listing = [
        {
            "airport": f.get("airport_label") or "Unknown",
            "country": f.get("country") or "-",
            "full_name": f.get("full_name"),
            "organization": f.get("organization") or "-",
            "date": f["first_created_at"],
            "days_since": (now - f["first_created_at"]).days if f["first_created_at"] else None,
            "status": _STATUS_LABELS.get(f["latest_status"], f["latest_status"] or "UNKNOWN"),
        }
        for f in sorted(distinct_fs, key=lambda f: f["first_created_at"] or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    ]

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
        "top_users": top_users,
        "fs_listing": fs_listing,
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
